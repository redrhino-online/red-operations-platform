"""Infrastructure adapters for RED durable workflow runs (SPEC.md section 7).

SPEC.md section 6 keeps persistence in the infrastructure layer: the domain and
application layers know only the ``WorkflowRunStore`` port, never JSONB, table
columns or a driver. This package holds the payload mapper and the process-local
and PostgreSQL stores behind that port, mirroring the Governance adapters.
"""
