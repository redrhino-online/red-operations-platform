"""Section 11 acceptance suite (SPEC.md section 11).

The suite's scenario coverage contract lives in ``covered-scenarios.txt`` and is
verified by ``scripts/check_acceptance_coverage.sh`` (DoD condition 2). Scenarios
whose seams or deploy environment do not exist yet are declared ``uncovered``
there so the gate fails honestly until they are built.
"""
