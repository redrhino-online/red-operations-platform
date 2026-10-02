"""Commercial Design bounded context (pure domain).

Owns the offer specification and the customer path. OfferVersion pins the
audience, promise, eligibility, price hypothesis and the exact approved method
version it depends on, so production readiness cannot be claimed without an
approved dependency (SPEC.md section 3, Phase 3).
"""
