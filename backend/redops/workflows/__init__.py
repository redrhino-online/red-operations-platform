"""RED durable workflow runs (SPEC.md section 7, ADR 0005).

Stage work and agent work run as versioned workflows with durable run state.
SPEC.md section 7 requires a workflow definition to carry its version, steps,
gate requirements and retry/timeout policy, and requires run state to be
persisted before side effects so a worker can resume from committed steps.
ADR 0005 adds the pilot constraint: a node restart must resume an in-flight
``wait_for_human`` approval, and resumption must be idempotent.

This package holds no pipeline stage and no vendor code. It is the RED-side
contract the fork's workflow/resumer substrate is adapted to behind ports
(DoD condition 7: the vendored OpenExecutive is unmodified).
"""
