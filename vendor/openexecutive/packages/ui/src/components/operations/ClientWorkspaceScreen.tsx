"use client";

// Client workspace overview container, native cockpit page (K3; SPEC.md section
// 14 conditions 2 and 3). Additive file (ADR 0014). It reads the shared
// workspace/engagement selection from `useRedClient()` (K2) and owns the
// tenant-scoped read from the engagement production view; there is no per-screen
// free-text tenant or engagement input. Selecting an approved-asset pin opens
// the in-page asset detail panel (asset review and approval spec section 3.1),
// fetched lazily on first open from the tenant-scoped approvals, the gate
// decisions, the kind's mapped content source and the stage artifact archive. A
// stage's Record gate action opens the schema-driven gate form (asset review
// and approval spec section 3.3) and its Add artifact action opens the markdown
// drop form (stage artifact archive spec section 3), both with the workspace's
// registered authorities; the backend remains the sole enforcer of
// prerequisites and authority.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import {
  contentSourceForKind,
  getProductionView,
  listApprovals,
  listArtifacts,
  listAssetContent,
  listDecisions,
  type ApprovalRecord,
  type AssetContentEntry,
  type DecisionRecord,
  type EngagementProductionView,
  type StageArtifact,
} from "@/lib/redOperationsApi";
import { AssetDetailPanel } from "./AssetDetailPanel";
import { ArtifactDropForm } from "./ArtifactDropForm";
import { ClientWorkspaceOverview } from "./ClientWorkspaceOverview";
import { StageGateForm } from "./StageGateForm";

interface AssetDetail {
  approvals: ApprovalRecord[];
  decisions: DecisionRecord[];
  content: AssetContentEntry | null;
  artifacts: StageArtifact[];
}

export function ClientWorkspaceScreen() {
  const { tenantId, workspaceId, workspaces } = useRedClient();
  const [view, setView] = useState<EngagementProductionView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AssetDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [gateStage, setGateStage] = useState<number | null>(null);
  const [artifactStage, setArtifactStage] = useState<number | null>(null);
  // Only the latest asset detail request may write, so a slow read for one pin
  // cannot overwrite a newer selection.
  const detailSeqRef = useRef(0);

  // The selected workspace's registered actors, from the listing the shared
  // context already loaded (GET /red/clients); the gate and artifact forms only
  // suggest them and the backend validates every actor.
  const authorities = useMemo(() => {
    const workspace = workspaces.find(
      (candidate) => candidate.workspace_id === workspaceId,
    );
    return workspace ? workspace.authorities.map((entry) => entry.actor) : [];
  }, [workspaces, workspaceId]);

  const load = useCallback(async () => {
    if (!workspaceId) {
      setView(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // No date filter: the review surface reads the current instant (stage
      // artifact archive spec section 2).
      setView(await getProductionView(tenantId, workspaceId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workspace");
    } finally {
      setLoading(false);
    }
  }, [tenantId, workspaceId]);

  useEffect(() => {
    void load();
  }, [load]);

  // A tenant or workspace change invalidates any open panel or form: the
  // detail reads are tenant-scoped, so a stale panel must never survive the
  // selection.
  useEffect(() => {
    detailSeqRef.current += 1;
    setSelectedAssetId(null);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(false);
    setGateStage(null);
    setArtifactStage(null);
  }, [tenantId, workspaceId]);

  const loadDetail = useCallback(
    async (assetId: string) => {
      const seq = ++detailSeqRef.current;
      setDetailLoading(true);
      setDetailError(null);
      try {
        const [approvalPage, decisionPage, artifactPage] = await Promise.all([
          listApprovals(tenantId),
          listDecisions(tenantId),
          workspaceId
            ? listArtifacts(tenantId, {
                workspace_id: workspaceId,
                asset_id: assetId,
              })
            : Promise.resolve(null),
        ]);
        const approvals = approvalPage.approvals.filter(
          (approval) => approval.asset_id === assetId,
        );
        const decisions = decisionPage.decisions.filter((decision) =>
          decision.required_assets.some((asset) => asset.asset_id === assetId),
        );
        const source = contentSourceForKind(assetId);
        const content = source
          ? await listAssetContent(tenantId, source)
          : null;
        if (seq !== detailSeqRef.current) return;
        setDetail({
          approvals,
          decisions,
          content,
          artifacts: artifactPage?.artifacts ?? [],
        });
      } catch (err) {
        if (seq !== detailSeqRef.current) return;
        setDetail(null);
        setDetailError(
          err instanceof Error ? err.message : "Failed to load asset detail",
        );
      } finally {
        if (seq === detailSeqRef.current) setDetailLoading(false);
      }
    },
    [tenantId, workspaceId],
  );

  const selectAsset = useCallback(
    (assetId: string) => {
      if (selectedAssetId === assetId) {
        detailSeqRef.current += 1;
        setSelectedAssetId(null);
        setDetail(null);
        setDetailError(null);
        setDetailLoading(false);
        return;
      }
      setSelectedAssetId(assetId);
      void loadDetail(assetId);
    },
    [selectedAssetId, loadDetail],
  );

  const closeGateForm = useCallback(() => setGateStage(null), []);
  const closeArtifactForm = useCallback(() => setArtifactStage(null), []);

  const handleGateRecorded = useCallback(() => {
    setGateStage(null);
    void load();
  }, [load]);

  const handleArtifactDropped = useCallback(() => {
    setArtifactStage(null);
    void load();
  }, [load]);

  // The stage the drop form collects for: its template kinds are the offered
  // options, and extra kinds stay allowed through the custom entry.
  const artifactStageKinds = useMemo(() => {
    if (artifactStage === null) return [];
    return (
      view?.stages.find((stage) => stage.stage_number === artifactStage)
        ?.required_asset_kinds ?? []
    );
  }, [view, artifactStage]);

  return (
    <main className="flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong"
          >
            Refresh
          </button>
        </div>
        {!workspaceId ? (
          <p className="text-sm text-fg-muted">
            Select a workspace to see its production view.
          </p>
        ) : (
          <>
            <ClientWorkspaceOverview
              view={view}
              loading={loading}
              error={error}
              onSelectAsset={selectAsset}
              onRecordGate={setGateStage}
              onAddArtifact={setArtifactStage}
            />
            {selectedAssetId ? (
              <section
                aria-labelledby="asset-detail-heading"
                data-testid="asset-detail-section"
                className="mt-4 rounded-xl border border-line bg-surface-elevated p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <h2
                    id="asset-detail-heading"
                    className="text-sm font-medium text-fg"
                  >
                    Asset detail: {selectedAssetId}
                  </h2>
                  <button
                    type="button"
                    onClick={() => selectAsset(selectedAssetId)}
                    className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong"
                  >
                    Close
                  </button>
                </div>
                <AssetDetailPanel
                  assetId={selectedAssetId}
                  approvals={detail?.approvals ?? []}
                  decisions={detail?.decisions ?? []}
                  content={detail?.content ?? null}
                  artifacts={detail?.artifacts ?? []}
                  loading={detailLoading}
                  error={detailError}
                />
              </section>
            ) : null}
            {gateStage !== null ? (
              <section
                aria-labelledby="record-gate-heading"
                data-testid="record-gate-section"
                className="mt-4 rounded-xl border border-line bg-surface-elevated p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <h2
                    id="record-gate-heading"
                    className="text-sm font-medium text-fg"
                  >
                    Record gate: stage {gateStage}
                  </h2>
                  <button
                    type="button"
                    onClick={closeGateForm}
                    className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong"
                  >
                    Close
                  </button>
                </div>
                <StageGateForm
                  tenantId={tenantId}
                  stageNumber={gateStage}
                  workspaceId={workspaceId}
                  authorities={authorities}
                  onRecorded={handleGateRecorded}
                  onClose={closeGateForm}
                />
              </section>
            ) : null}
            {artifactStage !== null ? (
              <section
                aria-labelledby="add-artifact-heading"
                data-testid="add-artifact-section"
                className="mt-4 rounded-xl border border-line bg-surface-elevated p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <h2
                    id="add-artifact-heading"
                    className="text-sm font-medium text-fg"
                  >
                    Add artifact: stage {artifactStage}
                  </h2>
                  <button
                    type="button"
                    onClick={closeArtifactForm}
                    className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong"
                  >
                    Close
                  </button>
                </div>
                <ArtifactDropForm
                  tenantId={tenantId}
                  stageNumber={artifactStage}
                  workspaceId={workspaceId}
                  requiredKinds={artifactStageKinds}
                  authorities={authorities}
                  onDropped={handleArtifactDropped}
                  onClose={closeArtifactForm}
                />
              </section>
            ) : null}
          </>
        )}
      </div>
    </main>
  );
}
