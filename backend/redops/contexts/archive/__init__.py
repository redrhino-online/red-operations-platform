"""Stage Artifact archive bounded context (pure domain).

Owns the markdown drop space for every stage's artifacts (docs/specs/
stage-artifact-archive.md section 1). A StageArtifact is the archived content
of one stage asset version: collection (dropping an artifact) and approval
(recording a gate) remain separate acts, so the archive collects everything
without authorizing production. The aggregate is append-only: a change is a
new version, never a rewrite.
"""
