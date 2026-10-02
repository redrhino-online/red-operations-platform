SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

REPO ?= .
RALPH ?= ./ralph_cycle.sh
COUNT := $(or $(n),$(N))

# Create case-insensitive command aliases while keeping the run logic in two targets.
RUN_ALIASES := $(shell bash -c 's=run; for ((m=0;m<8;m++)); do out=; for ((i=0;i<3;i++)); do c=$${s:i:1}; if ((m & (1<<i))); then out+=$$(printf "%s" "$$c" | tr "[:lower:]" "[:upper:]"); else out+=$$c; fi; done; printf "%s " "$$out"; done')
LOOP_ALIASES := $(shell bash -c 's=loop; for ((m=0;m<16;m++)); do out=; for ((i=0;i<4;i++)); do c=$${s:i:1}; if ((m & (1<<i))); then out+=$$(printf "%s" "$$c" | tr "[:lower:]" "[:upper:]"); else out+=$$c; fi; done; printf "%s " "$$out"; done')
HELP_ALIASES := $(shell bash -c 's=help; for ((m=0;m<16;m++)); do out=; for ((i=0;i<4;i++)); do c=$${s:i:1}; if ((m & (1<<i))); then out+=$$(printf "%s" "$$c" | tr "[:lower:]" "[:upper:]"); else out+=$$c; fi; done; printf "%s " "$$out"; done')

COMMAND_ALIASES := $(RUN_ALIASES) $(LOOP_ALIASES) $(HELP_ALIASES)

.PHONY: run loop help $(COMMAND_ALIASES)
.DEFAULT_GOAL := help

$(filter-out run,$(RUN_ALIASES)): run
$(filter-out loop,$(LOOP_ALIASES)): loop
$(filter-out help,$(HELP_ALIASES)): help

help:
	@printf '%s\n' \
	  'make run                 Run one Ralph cycle' \
	  'make loop n=5            Run five sequential Ralph cycles' \
	  'make run REPO=../fork    Run against a Git checkout in another folder'

run:
	@"$(RALPH)" "$(REPO)"

loop:
	@[[ "$(COUNT)" =~ ^[1-9][0-9]*$$ ]] || { printf 'Use: make loop n=5, where n is a positive whole number\n' >&2; exit 2; }
	@for ((cycle = 1; cycle <= $(COUNT); cycle++)); do \
	  printf '\nRalph cycle %s of %s\n' "$$cycle" "$(COUNT)"; \
	  "$(RALPH)" "$(REPO)" || exit $$?; \
	done
