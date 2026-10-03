"""RED agent bounded package (SPEC.md section 5).

Agent operating contracts live here: the model gateway seam every agent use
case depends on, the typed request/response values it exchanges, and the
deterministic fake adapter that lets agents run offline (SPEC.md sections 6 and
13 condition 5). This package holds no pipeline stage; it is the shared model
access seam for the Director and the specialist agents.
"""
