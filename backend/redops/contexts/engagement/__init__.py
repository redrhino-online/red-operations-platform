"""Engagement bounded context (pure domain).

Owns the client, contract scope, stakeholders and health. ClientWorkspace is the
tenant root every client-owned resource attaches to: its invariant is that every
child resource belongs to exactly one client (SPEC.md section 3), and it records
the workspace authorities and the engagement lifecycle. The stage 0-10 production
pipeline and later cross-context references anchor here.
"""
