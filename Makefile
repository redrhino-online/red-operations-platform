SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

REPO ?= .
RALPH ?= ./ralph_cycle.sh
COUNT := $(or $(n),$(N),1)

# Local development database. The docker-compose postgres service exposes this
# URL. Exporting it keeps the persistence adapter and migration tests running
# (instead of skipping) for every cycle and for `make check`. An explicit
# environment value overrides this default; a local .env overrides both
# (ralph_cycle.sh loads .env). See .env.example.
DATABASE_URL ?= postgresql://redops:redops@localhost:5432/redops
export DATABASE_URL

# Definition-of-done health check. The Atlas cluster already serves the app at
# this internal host; change the path if the deployment exposes health
# elsewhere. REDOP_HEALTH_INSECURE=1 skips CA verification for the internal
# atlas-ca, which WSL does not trust.
REDOP_HEALTH_URL ?= https://redop.atlas.lan/
REDOP_HEALTH_INSECURE ?= 1
export REDOP_HEALTH_URL REDOP_HEALTH_INSECURE

# Publish policy: a single `make run` and every non-final `make loop` cycle push
# to origin only. The final cycle of a loop also pushes to atlas. Override with
# PUSH_REMOTES / FINAL_PUSH_REMOTES. Never pushes to `upstream`.
PUSH_REMOTES ?= origin
FINAL_PUSH_REMOTES ?= origin atlas

# A cycle that fails (for example a model or network hiccup, or a stale lock) is
# retried at the same cycle number up to MAX_FAILURES consecutive times before
# the loop halts, so one flaky run does not kill a long loop. RETRY_SLEEP is the
# backoff in seconds between retries.
MAX_FAILURES ?= 5
RETRY_SLEEP ?= 15

# Create case-insensitive command aliases while keeping the run logic in two targets.
RUN_ALIASES := $(shell bash -c 's=run; for ((m=0;m<8;m++)); do out=; for ((i=0;i<3;i++)); do c=$${s:i:1}; if ((m & (1<<i))); then out+=$$(printf "%s" "$$c" | tr "[:lower:]" "[:upper:]"); else out+=$$c; fi; done; printf "%s " "$$out"; done')
LOOP_ALIASES := $(shell bash -c 's=loop; for ((m=0;m<16;m++)); do out=; for ((i=0;i<4;i++)); do c=$${s:i:1}; if ((m & (1<<i))); then out+=$$(printf "%s" "$$c" | tr "[:lower:]" "[:upper:]"); else out+=$$c; fi; done; printf "%s " "$$out"; done')
HELP_ALIASES := $(shell bash -c 's=help; for ((m=0;m<16;m++)); do out=; for ((i=0;i<4;i++)); do c=$${s:i:1}; if ((m & (1<<i))); then out+=$$(printf "%s" "$$c" | tr "[:lower:]" "[:upper:]"); else out+=$$c; fi; done; printf "%s " "$$out"; done')

COMMAND_ALIASES := $(RUN_ALIASES) $(LOOP_ALIASES) $(HELP_ALIASES)

.PHONY: run loop help check done canon-lock canon-pin reset-hosted $(COMMAND_ALIASES)
.DEFAULT_GOAL := help

$(filter-out run,$(RUN_ALIASES)): run
$(filter-out loop,$(LOOP_ALIASES)): loop
$(filter-out help,$(HELP_ALIASES)): help

help:
	@printf '%s\n' \
	  'make run                 Run one Ralph cycle' \
	  'make loop                Run one cycle (n defaults to 1)' \
	  'make loop n=5            Run five sequential Ralph cycles' \
	  'make loop n=-1           Run continuously until done, STOP or a hard error' \
	  'make run REPO=../fork    Run against a Git checkout in another folder' \
	  'make check               Run the full test suite (with Postgres) and pyflakes' \
	  'make done                Run the prototype definition-of-done gate (SPEC section 13)' \
	  'make canon-lock          Lock the current canon content at the start of a run (idempotent)' \
	  'make canon-pin           Force re-pin the canon content hash in canon.lock' \
	  'make reset-hosted        Wipe the hosted instance data (onboarding/people)'

run: canon-lock
	@RALPH_PUSH_REMOTES="$(PUSH_REMOTES)" RALPH_PLAN_PUSH_REMOTES="$(PUSH_REMOTES)" "$(RALPH)" "$(REPO)"

check:
	@printf 'check: pytest (unit + postgres adapters + migrations) and pyflakes\n'
	@uv run pytest -q
	@uv run pyflakes backend tests

done:
	@./scripts/check_definition_of_done.sh

# Lock the canon at the start of a run so a cycle never trips the strict pin,
# and so a mid-run canon change still halts the loop. Writes canon.lock only
# when the content hash differs, so an unchanged canon leaves the tree clean.
canon-lock:
	@h="$$(./scripts/canon_hash.sh)"; p="$$(awk 'NR==1{print $$1}' canon.lock 2>/dev/null || true)"; \
	if [[ "$$h" != "$$p" ]]; then \
	  printf '%s %s\n' "$$h" "$$(date -u +%FT%TZ)" > canon.lock; \
	  printf 'canon locked: %s (was %s)\n' "$$h" "$${p:-none}"; \
	else printf 'canon locked: %s\n' "$$h"; fi

canon-pin:
	@h="$$(./scripts/canon_hash.sh)"; printf '%s %s\n' "$$h" "$$(date -u +%FT%TZ)" > canon.lock; printf 'pinned canon: %s\n' "$$h"

reset-hosted:
	@./scripts/reset_redop_data.sh

loop: canon-lock
	@if [[ "$(COUNT)" != "-1" ]] && [[ ! "$(COUNT)" =~ ^[1-9][0-9]*$$ ]]; then \
	  printf 'Use: make loop n=5 for five cycles, or make loop n=-1 to run continuously\n' >&2; exit 2; fi
	@failures=0; cycle=1; \
	if (( $(COUNT) == -1 )); then limit=9223372036854775807; continuous=1; total="continuous"; else limit=$(COUNT); continuous=0; total=$(COUNT); fi; \
	while (( cycle <= limit )); do \
	  if [[ -e "$(REPO)/.ralph/STOP" ]]; then \
	    printf 'Stop requested: %s exists; halting before cycle %s\n' "$(REPO)/.ralph/STOP" "$$cycle"; \
	    break; \
	  fi; \
	  if (( continuous == 0 )) && (( cycle == limit )); then remotes="$(FINAL_PUSH_REMOTES)"; else remotes="$(PUSH_REMOTES)"; fi; \
	  printf '\nRalph cycle %s of %s (publish: %s)\n' "$$cycle" "$$total" "$$remotes"; \
	  status=0; RALPH_PUSH_REMOTES="$$remotes" RALPH_PLAN_PUSH_REMOTES="$$remotes" "$(RALPH)" "$(REPO)" || status=$$?; \
	  if (( status == 3 )); then \
	    if [[ -e "$(REPO)/.ralph/DONE" ]]; then \
	      printf 'Definition of done reached; halting loop\n'; \
	      if (( continuous == 1 )); then \
	        branch="$$(git -C "$(REPO)" symbolic-ref --quiet --short HEAD || printf main)"; \
	        if git -C "$(REPO)" remote get-url atlas >/dev/null 2>&1; then \
	          git -C "$(REPO)" push atlas "HEAD:refs/heads/$$branch" || printf 'atlas push failed; push manually\n'; \
	        else printf 'atlas remote not configured; skipping atlas push\n'; fi; \
	      fi; \
	    else \
	      printf 'Stop requested: %s exists; halting loop\n' "$(REPO)/.ralph/STOP"; \
	    fi; \
	    break; \
	  fi; \
	  if (( status == 4 )); then \
	    printf 'Canon content changed; halting the loop now (not a retryable failure). Re-pin with make canon-pin, or set RALPH_CANON_STRICT=0, then resume.\n'; \
	    break; \
	  fi; \
	  if (( status != 0 )); then \
	    failures=$$(( failures + 1 )); \
	    printf 'Cycle %s failed (status %s); failure %s of %s\n' "$$cycle" "$$status" "$$failures" "$(MAX_FAILURES)"; \
	    if (( failures >= $(MAX_FAILURES) )); then printf 'Halting after %s consecutive failures\n' "$$failures"; exit $$status; fi; \
	    sleep $(RETRY_SLEEP); \
	    continue; \
	  fi; \
	  failures=0; \
	  cycle=$$(( cycle + 1 )); \
	done
