"""Shared RED platform infrastructure that is not owned by one context.

SPEC.md section 6 places cross-cutting concerns such as identity, outbox and
observability here. Persistence migrations live here too, because a migration
tool is a delivery concern, not a bounded-context domain rule.
"""
