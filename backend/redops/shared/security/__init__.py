"""Shared prompt-injection guard (SPEC.md sections 5 and 9).

Client material and model output are data, never authority. SPEC.md section 5
requires the platform to guard prompt injection by treating ingested client
material as data, limiting retrieval to the active client, and validating tool
calls outside model output. SPEC.md section 9 keeps cross-client access out and
requires client material to be treated as confidential. That boundary is
cross-cutting, so the tenant-scoped guard lives in ``shared`` (SPEC.md section
6) rather than inside one bounded context.
"""
