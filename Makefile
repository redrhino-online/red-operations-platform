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

# Definition-of-done health check. The Atlas cluster must serve the RED app at
# this internal host; `[6/6]` requires the response to carry a RED identity
# marker, so a bare 200 from another app cannot pass condition 9. Change the
# path if the deployment exposes the RED health elsewhere.
# REDOP_HEALTH_INSECURE=1 skips CA verification for the internal atlas-ca, which
# WSL does not trust.
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

.PHONY: run loop help check done docs docs-serve canon-lock canon-pin vendor-pin seed reset-hosted $(COMMAND_ALIASES)
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
	  'make done                Run the definition-of-done gate (SPEC sections 13 and 14)' \
	  'make docs                Build the developer docs site into site/ (strict)' \
	  'make docs-serve          Serve the developer docs locally with live reload' \
	  'make canon-lock          Lock the current canon content at the start of a run (idempotent)' \
	  'make canon-pin           Force re-pin the canon content hash in canon.lock' \
	  'make vendor-pin          Owner action: re-baseline the absorbed fork manifest (ADR 0014)' \
	  'make seed                Seed the 3F pilot workspace into DATABASE_URL (idempotent)' \
	  'make reset-hosted        Wipe the hosted instance data (onboarding/people)'

run: canon-lock
	@status=0; RALPH_PUSH_REMOTES="$(PUSH_REMOTES)" RALPH_PLAN_PUSH_REMOTES="$(PUSH_REMOTES)" "$(RALPH)" "$(REPO)" || status=$$?; \
	if (( status == 4 )); then printf '\nCANON DRIFT: canon content changed; re-pin with make canon-pin, or set RALPH_CANON_STRICT=0. Halting cleanly.\n'; exit 0; fi; \
	exit $$status

check:
	@printf 'check: pytest (unit + postgres adapters + migrations) and pyflakes\n'
	@uv run pytest -q
	@uv run pyflakes backend tests

done:
	@./scripts/check_definition_of_done.sh

# Developer docs site (MkDocs Material). Requires mkdocs-material; use
# `make docs-serve` for a live preview. Publishing is automatic via
# .github/workflows/docs.yml on push to main.
docs:
	@uv run --with mkdocs-material mkdocs build --strict

docs-serve:
	@uv run --with mkdocs-material mkdocs serve

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

# Owner action only: re-baseline the absorbed fork's manifest after an
# owner-approved exception recorded in docs/fork_inventory.md or after an
# upstream merge. Unattended build cycles never pin (ADR 0014).
vendor-pin:
	@python3 scripts/vendor_pin.py pin

# Seed the 3F pilot workspace (K1; SPEC.md section 14 condition 4) into the
# database named by DATABASE_URL, through the real domain use cases. Idempotent:
# a rerun changes nothing. The seeded values are demo data, never client
# approvals.
seed:
	@PYTHONPATH=backend uv run python -m redops.seed

# Seed the RED runtime Departments/Council/People stores (K10; SPEC.md section
# 14 condition 7) into the SQLite database named by EPISODIC_DB_PATH, through
# the vendored store's public API. Idempotent: a rerun changes nothing.
seed-stores:
	@PYTHONPATH=backend uv run python -m redops.seed_red_stores

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
	  ck="$$(./scripts/canon_hash.sh)"; cp="$$(awk 'NR==1{print $$1}' canon.lock 2>/dev/null || true)"; \
	  if [[ "$$ck" != "$$cp" ]]; then \
	    printf '\nCANON DRIFT: canon content changed (pinned %s, now %s). Halting cleanly; re-pin with make canon-pin, or set RALPH_CANON_STRICT=0.\n' "$$cp" "$$ck"; \
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
	    printf '\nCANON DRIFT: canon changed mid-cycle. Halting cleanly; re-pin with make canon-pin, or set RALPH_CANON_STRICT=0.\n'; \
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
