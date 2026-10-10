// Stage artifact drop form, native cockpit page fragment (stage artifact
// archive spec section 3). Additive file (ADR 0014). It collects one markdown
// artifact for a stage — kind (the stage template's canonical kinds plus a
// custom entry, extra kinds allowed), asset id (follows the kind until edited
// by hand, like the gate form's rows), optional version (blank = the next free
// one), the artifact markdown, the collecting owner and an optional note — and
// posts it to `POST /red/clients/{tenant}/artifacts`. The backend remains the
// sole enforcer of the archive's fields: a refusal is rendered verbatim inline
// and nothing is recorded locally.

import { useEffect, useRef, useState } from "react";

import {
  dropArtifact,
  type StageArtifactDrop,
} from "@/lib/redOperationsApi";

// The select sentinel for a kind outside the stage template's canonical list;
// the archive collects everything, so the free-text entry stays available.
const CUSTOM_KIND = "__custom__";

const inputClass =
  "rounded-lg border border-line bg-surface px-2 py-1 text-xs text-fg focus:outline-none focus:border-line-strong";
const quietButtonClass =
  "rounded-lg border border-line bg-surface-overlay px-2 py-1 text-xs font-medium text-fg hover:border-line-strong focus:outline-none focus:border-line-strong";

function labelClass(control: React.ReactNode, text: string) {
  return (
    <label className="text-xs text-fg-muted flex items-center gap-2">
      {control}
      {text}
    </label>
  );
}

export interface ArtifactDropFormProps {
  tenantId: string;
  workspaceId: string;
  stageNumber: number;
  // The stage template's canonical kinds, offered as the select options; a
  // custom entry allows every extra kind the archive collects.
  requiredKinds: string[];
  authorities: string[];
  onDropped: () => void;
  onClose: () => void;
}

export function ArtifactDropForm({
  tenantId,
  workspaceId,
  stageNumber,
  requiredKinds,
  authorities,
  onDropped,
  onClose,
}: ArtifactDropFormProps) {
  const [kindSelect, setKindSelect] = useState(
    requiredKinds[0] ?? CUSTOM_KIND,
  );
  const [customKind, setCustomKind] = useState("");
  const [assetId, setAssetId] = useState(requiredKinds[0] ?? "");
  const [version, setVersion] = useState("");
  const [markdown, setMarkdown] = useState("");
  const [owner, setOwner] = useState(authorities[0] ?? "");
  const [note, setNote] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // The defaults snapshot at open time: a later props refresh must not reset
  // in-progress edits.
  const defaultsRef = useRef({ requiredKinds, authorities });
  defaultsRef.current = { requiredKinds, authorities };

  // A stage change re-opens the form on fresh defaults, like the gate form.
  useEffect(() => {
    const kinds = defaultsRef.current.requiredKinds;
    setKindSelect(kinds[0] ?? CUSTOM_KIND);
    setCustomKind("");
    setAssetId(kinds[0] ?? "");
    setVersion("");
    setMarkdown("");
    setOwner(defaultsRef.current.authorities[0] ?? "");
    setNote("");
    setSubmitError(null);
  }, [stageNumber]);

  const effectiveKind = kindSelect === CUSTOM_KIND ? customKind : kindSelect;

  // The asset id follows the kind until it is edited by hand: a change keeps
  // it only when the user has already moved it off the previous kind.
  const followAssetId = (previousKind: string, nextKind: string) => {
    if (assetId === "" || assetId === previousKind) setAssetId(nextKind);
  };

  const handleKindSelect = (next: string) => {
    const previous = effectiveKind;
    setKindSelect(next);
    followAssetId(previous, next === CUSTOM_KIND ? "" : next);
  };

  const handleCustomKind = (next: string) => {
    const previous = effectiveKind;
    setCustomKind(next);
    followAssetId(previous, next);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) return;
    // Blank means "unset": the backend defaults the asset id to the kind, the
    // version to the next free one and the drop date to today.
    const body: StageArtifactDrop = {
      workspace_id: workspaceId,
      stage_number: stageNumber,
      kind: effectiveKind,
      markdown,
      owner,
    };
    if (assetId !== "") body.asset_id = assetId;
    if (version !== "") {
      const parsed = Number(version);
      if (Number.isFinite(parsed)) body.version = Math.trunc(parsed);
    }
    if (note !== "") body.note = note;
    setSubmitting(true);
    setSubmitError(null);
    dropArtifact(tenantId, body)
      .then(() => {
        setSubmitting(false);
        onDropped();
      })
      .catch((err) => {
        setSubmitting(false);
        setSubmitError(
          err instanceof Error
            ? err.message
            : "Failed to drop the artifact",
        );
      });
  };

  return (
    <form data-testid="artifact-drop-form" onSubmit={handleSubmit}>
      {submitError ? (
        <p
          role="alert"
          data-testid="artifact-error"
          className="mb-3 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400"
        >
          {submitError}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        {labelClass(
          <select
            value={kindSelect}
            onChange={(event) => handleKindSelect(event.target.value)}
            className={inputClass}
          >
            {requiredKinds.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
            <option value={CUSTOM_KIND}>custom…</option>
          </select>,
          "Kind",
        )}
        {kindSelect === CUSTOM_KIND
          ? labelClass(
              <input
                type="text"
                value={customKind}
                onChange={(event) => handleCustomKind(event.target.value)}
                className={inputClass}
              />,
              "Custom kind",
            )
          : null}
        {labelClass(
          <input
            type="text"
            value={assetId}
            onChange={(event) => setAssetId(event.target.value)}
            className={inputClass}
          />,
          "Asset id",
        )}
        {labelClass(
          <input
            type="number"
            value={version}
            onChange={(event) => setVersion(event.target.value)}
            className={inputClass}
          />,
          "Version",
        )}
        {labelClass(
          <select
            value={owner}
            onChange={(event) => setOwner(event.target.value)}
            className={inputClass}
          >
            {authorities.map((authority) => (
              <option key={authority} value={authority}>
                {authority}
              </option>
            ))}
          </select>,
          "Owner",
        )}
        {labelClass(
          <input
            type="text"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className={inputClass}
          />,
          "Note",
        )}
      </div>
      <label className="mt-3 block text-xs text-fg-muted">
        <span className="mb-1 block">Markdown</span>
        <textarea
          value={markdown}
          onChange={(event) => setMarkdown(event.target.value)}
          rows={8}
          required
          className={`${inputClass} block w-full font-mono`}
        />
      </label>
      <div className="mt-4 flex items-center gap-3">
        <button
          type="submit"
          data-testid="artifact-submit"
          disabled={submitting}
          className={quietButtonClass}
        >
          Drop artifact
        </button>
        <button type="button" onClick={onClose} className={quietButtonClass}>
          Cancel
        </button>
        {submitting ? (
          <span role="status" className="text-xs text-fg-muted">
            Dropping artifact…
          </span>
        ) : null}
      </div>
    </form>
  );
}
