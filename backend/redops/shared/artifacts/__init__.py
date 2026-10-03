"""Shared artifact-access layer (SPEC.md sections 3, 6 and 9).

Artifact bytes are cross-cutting: a source record's immutable original and a
production build's generated file are both stored in the private object store
with metadata in PostgreSQL, and both must be resolvable only by the client
that owns them. SPEC.md section 6 places cross-context concerns in ``shared``,
so the tenant-scoped artifact URL seam lives here rather than in one context.
"""
