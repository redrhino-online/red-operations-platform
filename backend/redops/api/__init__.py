"""RED FastAPI entry points (thin adapters over the domain).

SPEC.md section 6 places entry points at the outermost onion layer: routes call
application use cases, which depend on domain types and ports. ADR 0008 makes
OpenExecutive a pinned dependency reused through composition, so RED owns its
own app and mounts the reused shell rather than editing it.
"""
