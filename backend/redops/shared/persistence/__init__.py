"""Persistence delivery concerns shared across bounded contexts.

ADR 0003 makes RED's relational store PostgreSQL and requires schema changes
to ship as migrations committed with the code (SPEC.md section 6: migrations
committed with schema changes). The ordered migration scripts live under
``redops/shared/persistence/migrations`` and are applied by Alembic.
"""
