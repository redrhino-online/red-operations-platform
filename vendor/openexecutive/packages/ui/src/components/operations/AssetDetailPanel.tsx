// Asset detail panel, native cockpit page fragment (asset review and approval
// spec section 3.1). Additive file (ADR 0014). Pure presentational provenance
// view over the data the client workspace screen fetches for one pinned asset
// kind: the exact-version approval records, the gate decisions whose required
// assets pin the kind, and the stored content of the kind's mapped source
// group. The backend decides what was approved; the panel renders it and can
// approve nothing.

import type {
  AmplifierRecord,
  ApprovalRecord,
  AssetContentEntry,
  DecisionRecord,
  FunnelRecord,
  LaunchQA,
  MeasurementRecord,
  MessageRecord,
  MethodVersion,
  OfferVersion,
} from "@/lib/redOperationsApi";

export interface AssetDetailPanelProps {
  assetId: string;
  approvals: ApprovalRecord[];
  decisions: DecisionRecord[];
  content: AssetContentEntry | null;
  loading?: boolean;
  error?: string | null;
}

function Field({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <p className="text-xs text-fg-muted">
      {label}: {value}
    </p>
  );
}

function FieldList({
  label,
  values,
}: {
  label: string;
  values: string[] | undefined;
}) {
  if (!values || values.length === 0) return null;
  return (
    <p className="text-xs text-fg-muted">
      {label}: {values.join(", ")}
    </p>
  );
}

function approvalMark(
  approved: boolean | null | undefined,
  label = "approved",
): string {
  return approved ? ` (${label})` : "";
}

function EmptyContent({ label }: { label: string }) {
  return (
    <p className="mt-1 text-xs text-fg-muted">
      No {label} stored for this tenant yet.
    </p>
  );
}

function MethodsContent({ methods }: { methods: MethodVersion[] }) {
  if (methods.length === 0) return <EmptyContent label="methods" />;
  return (
    <ul className="mt-2 space-y-2">
      {methods.map((method) => {
        const solution = method.signature_solution;
        const model = method.diagnostic_model;
        const currency = method.primary_currency_detail;
        return (
          <li
            key={method.method_id}
            className="rounded-lg border border-line bg-surface p-3 text-xs text-fg"
          >
            <p className="font-medium">
              {method.method_id}
              {approvalMark(method.is_approved)}
            </p>
            <Field label="Semantic version" value={method.semantic_version} />
            <Field label="Diagnostic model" value={method.diagnostic_model_id} />
            <FieldList label="Claims" values={method.claims} />
            {solution || model || currency ? (
              <>
                {solution ? (
                  <div className="mt-2">
                    <p className="font-medium text-fg">Signature solution</p>
                    <Field label="Narrative" value={solution.narrative} />
                    <Field
                      label="Starting state"
                      value={solution.starting_state}
                    />
                    <Field label="Final state" value={solution.final_state} />
                  </div>
                ) : null}
                {model ? (
                  <div className="mt-2">
                    <p className="font-medium text-fg">Diagnostic model</p>
                    <Field label="Name" value={model.name} />
                    {(model.levels ?? []).map((level, index) => (
                      <div
                        key={level.level_id ?? index}
                        className="mt-1 border-l-2 border-line pl-2"
                      >
                        <p className="font-medium text-fg">
                          {level.name ?? level.level_id ?? `Level ${index + 1}`}
                        </p>
                        <FieldList
                          label="Observable measures"
                          values={level.observable_measures}
                        />
                        <FieldList label="Symptoms" values={level.symptoms} />
                        <FieldList label="Behaviors" values={level.behaviors} />
                        <FieldList label="Problems" values={level.problems} />
                      </div>
                    ))}
                    <Field label="Progression" value={model.progression} />
                    <Field
                      label="Qualification logic"
                      value={model.qualification_logic}
                    />
                    <Field label="Visual" value={model.visual} />
                    <Field
                      label="Explanatory copy"
                      value={model.explanatory_copy}
                    />
                  </div>
                ) : null}
                {currency ? (
                  <div className="mt-2">
                    <p className="font-medium text-fg">Primary currency</p>
                    <Field label="Currency" value={currency.currency} />
                    <Field label="Audience" value={currency.audience} />
                    <Field
                      label="Current measure"
                      value={currency.current_measure}
                    />
                    <Field
                      label="Desired measure"
                      value={currency.desired_measure}
                    />
                    <Field label="Mechanism" value={currency.mechanism} />
                  </div>
                ) : null}
              </>
            ) : (
              <p
                data-testid="method-no-content-sections"
                className="mt-2 text-xs text-fg-muted"
              >
                No stored content sections for this method.
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function OffersContent({ offers }: { offers: OfferVersion[] }) {
  if (offers.length === 0) return <EmptyContent label="offers" />;
  return (
    <ul className="mt-2 space-y-2">
      {offers.map((offer) => {
        const delivery = offer.delivery;
        return (
          <li
            key={offer.offer_id}
            className="rounded-lg border border-line bg-surface p-3 text-xs text-fg"
          >
            <p className="font-medium">
              {offer.offer_id}
              {approvalMark(offer.is_production_ready, "production ready")}
            </p>
            <Field label="Audience" value={offer.audience} />
            <Field label="Promise" value={offer.promise} />
            <Field label="Eligibility" value={offer.eligibility} />
            <Field label="Price" value={offer.price_hypothesis} />
            <Field label="State" value={offer.state} />
            {delivery ? (
              <div className="mt-2">
                <p className="font-medium text-fg">Delivery specification</p>
                <Field label="Delivery model" value={delivery.delivery_model} />
                <Field label="Duration" value={delivery.duration} />
                <FieldList label="Modules" values={delivery.modules} />
                <FieldList
                  label="Responsibilities"
                  values={delivery.responsibilities}
                />
                <Field
                  label="Support cadence"
                  value={delivery.support_cadence}
                />
                {(delivery.step_deliveries ?? []).map((step, index) => (
                  <div
                    key={step.step_id ?? index}
                    className="mt-1 border-l-2 border-line pl-2"
                  >
                    <p className="font-medium text-fg">
                      {step.step_id ?? `Step ${index + 1}`}
                    </p>
                    <Field label="Action" value={step.action} />
                    <Field label="Actor" value={step.actor} />
                    <Field label="Deliverable" value={step.deliverable} />
                    <Field label="Timing" value={step.timing} />
                    <Field label="Measure" value={step.measure} />
                  </div>
                ))}
                <FieldList
                  label="Outcome measures"
                  values={delivery.outcome_measures}
                />
                <Field
                  label="Pricing and payments"
                  value={delivery.pricing_payments}
                />
                <Field label="Scope" value={delivery.scope} />
                <Field
                  label="Guarantee decision"
                  value={delivery.guarantee_decision}
                />
                <Field label="Eligibility" value={delivery.eligibility} />
                <FieldList label="Offer stack" values={delivery.offer_stack} />
              </div>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

function MessagesContent({ messages }: { messages: MessageRecord[] }) {
  if (messages.length === 0) return <EmptyContent label="messages" />;
  return (
    <ul className="mt-2 space-y-2">
      {messages.map((message) => (
        <li
          key={message.message_id}
          className="rounded-lg border border-line bg-surface p-3 text-xs text-fg"
        >
          <p className="font-medium">
            {message.message_id}
            {approvalMark(message.is_approved)}
          </p>
          <Field label="Owner" value={message.owner} />
          <Field label="Avatar" value={message.avatar} />
          <Field label="Currency" value={message.currency} />
          <Field label="Problem" value={message.problem} />
          <Field label="Promise" value={message.promise} />
          <Field label="Story" value={message.story} />
          <Field label="Hook" value={message.hook} />
          <FieldList label="Angles" values={message.angles} />
          <Field label="Landing message" value={message.landing_message} />
          <Field label="Call to action" value={message.cta} />
          <Field label="Desired outcome" value={message.desired_outcome} />
          <Field label="Lead magnet" value={message.lead_magnet} />
          <Field label="Method explanation" value={message.method_explanation} />
          <FieldList
            label="Problem hierarchy"
            values={message.problem_hierarchy}
          />
          <FieldList
            label="Proof objections"
            values={message.proof_objections}
          />
          <Field
            label="Authority amplifier outline"
            value={message.authority_amplifier_outline}
          />
          <Field label="Product offer" value={message.product_offer_id} />
        </li>
      ))}
    </ul>
  );
}

function AmplifiersContent({ amplifiers }: { amplifiers: AmplifierRecord[] }) {
  if (amplifiers.length === 0) return <EmptyContent label="amplifiers" />;
  return (
    <ul className="mt-2 space-y-2">
      {amplifiers.map((amplifier) => (
        <li
          key={amplifier.amplifier_id}
          className="rounded-lg border border-line bg-surface p-3 text-xs text-fg"
        >
          <p className="font-medium">
            {amplifier.amplifier_id}
            {approvalMark(amplifier.is_approved)}
          </p>
          <Field label="Method reference" value={amplifier.method_ref} />
          <Field label="Offer reference" value={amplifier.offer_ref} />
          {(amplifier.script_sections ?? []).map((section, index) => (
            <p
              key={`${section.kind}-${index}`}
              className="text-xs text-fg-muted"
            >
              Script ({section.kind}): {section.content}
            </p>
          ))}
          <Field label="Storyboard" value={amplifier.storyboard} />
          <Field label="Recording" value={amplifier.recording} />
          <Field label="Edited video" value={amplifier.edited_video} />
          <Field label="Hosted video" value={amplifier.hosted_video} />
          <FieldList label="Player assets" values={amplifier.player_assets} />
        </li>
      ))}
    </ul>
  );
}

function FunnelsContent({ funnels }: { funnels: FunnelRecord[] }) {
  if (funnels.length === 0) return <EmptyContent label="funnels" />;
  return (
    <ul className="mt-2 space-y-2">
      {funnels.map((funnel) => (
        <li
          key={funnel.funnel_id}
          className="rounded-lg border border-line bg-surface p-3 text-xs text-fg"
        >
          <p className="font-medium">
            {funnel.funnel_id}
            {approvalMark(funnel.is_approved)}
          </p>
          <FieldList
            label="Asset refs"
            values={(funnel.asset_refs ?? []).map(
              (ref) => `${ref.asset_id}@v${ref.version ?? "?"}`,
            )}
          />
          <Field label="Routing" value={funnel.routing} />
        </li>
      ))}
    </ul>
  );
}

function LaunchQAsContent({ launchQAs }: { launchQAs: LaunchQA[] }) {
  if (launchQAs.length === 0) return <EmptyContent label="launch QAs" />;
  return (
    <ul className="mt-2 space-y-2">
      {launchQAs.map((qa) => (
        <li
          key={qa.qa_id}
          className="rounded-lg border border-line bg-surface p-3 text-xs text-fg"
        >
          <p className="font-medium">
            {qa.qa_id}
            {approvalMark(qa.is_ready_for_traffic, "ready for traffic")}
          </p>
          <Field label="Owner" value={qa.owner} />
          <Field label="Designated authority" value={qa.designated_authority} />
          <Field label="State" value={qa.state} />
          <FieldList
            label="Checks"
            values={qa.checks.map((check) => `${check.kind}: ${check.outcome}`)}
          />
        </li>
      ))}
    </ul>
  );
}

function MeasurementsContent({ records }: { records: MeasurementRecord[] }) {
  if (records.length === 0) return <EmptyContent label="measurements" />;
  return (
    <ul className="mt-2 space-y-2">
      {records.map((record) => (
        <li
          key={record.record_id}
          className="rounded-lg border border-line bg-surface p-3 text-xs text-fg"
        >
          <p className="font-medium">
            {record.record_id}
            {approvalMark(record.is_observed, "observed")}
          </p>
          <Field label="Metric" value={record.metric?.name ?? null} />
          <Field label="Value" value={String(record.value)} />
          <Field
            label="Window"
            value={`${record.window_start} to ${record.window_end}`}
          />
          <Field label="Basis" value={record.basis} />
          <Field label="Source" value={record.source} />
        </li>
      ))}
    </ul>
  );
}

function AssetContentList({ entry }: { entry: AssetContentEntry }) {
  switch (entry.source) {
    case "methods":
      return <MethodsContent methods={entry.methods} />;
    case "offers":
      return <OffersContent offers={entry.offers} />;
    case "messages":
      return <MessagesContent messages={entry.messages} />;
    case "amplifiers":
      return <AmplifiersContent amplifiers={entry.amplifiers} />;
    case "funnels":
      return <FunnelsContent funnels={entry.funnels} />;
    case "launch-qas":
      return <LaunchQAsContent launchQAs={entry.launch_qas} />;
    case "measurements":
      return <MeasurementsContent records={entry.records} />;
  }
}

export function AssetDetailPanel({
  assetId,
  approvals,
  decisions,
  content,
  loading = false,
  error = null,
}: AssetDetailPanelProps) {
  return (
    <div data-testid="asset-detail-panel">
      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading asset detail…
        </p>
      ) : null}
      {error ? (
        <p
          role="alert"
          className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400"
        >
          {error}
        </p>
      ) : null}

      {!loading && !error ? (
        <>
          <section
            aria-labelledby={`asset-detail-approvals-${assetId}`}
            data-testid="asset-detail-approvals"
            className="mt-3"
          >
            <h3
              id={`asset-detail-approvals-${assetId}`}
              className="text-sm font-medium text-fg"
            >
              Approvals
            </h3>
            {approvals.length === 0 ? (
              <p
                data-testid="asset-detail-approvals-empty"
                className="mt-1 text-xs text-fg-muted"
              >
                No approval records found for {assetId}.
              </p>
            ) : (
              <ul className="mt-2 space-y-2">
                {approvals.map((approval) => (
                  <li
                    key={`${approval.version}-${approval.stage_number}-${approval.decided_on}-${approval.scope}`}
                    className="rounded-lg border border-line bg-surface p-3 text-xs text-fg"
                  >
                    <p className="font-medium">Version {approval.version}</p>
                    <p className="text-fg-muted">
                      Scope: {approval.scope} | Stage: {approval.stage_number}
                    </p>
                    <p className="text-fg-muted">
                      Requested by: {approval.requested_by} | Approver:{" "}
                      {approval.approver}
                    </p>
                    <p className="text-fg-muted">
                      Outcome: {approval.outcome} | Decided:{" "}
                      {approval.decided_on} | Expires:{" "}
                      {approval.expires_on ?? "none"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section
            aria-labelledby={`asset-detail-decisions-${assetId}`}
            data-testid="asset-detail-decisions"
            className="mt-3"
          >
            <h3
              id={`asset-detail-decisions-${assetId}`}
              className="text-sm font-medium text-fg"
            >
              Gate decisions
            </h3>
            {decisions.length === 0 ? (
              <p className="mt-1 text-xs text-fg-muted">
                No gate decision pinned this asset.
              </p>
            ) : (
              <ul className="mt-2 space-y-2">
                {decisions.map((decision) => (
                  <li
                    key={`${decision.stage_number}-${decision.checkpoint}-${decision.decided_on ?? ""}`}
                    className="rounded-lg border border-line bg-surface p-3 text-xs text-fg"
                  >
                    <p className="font-medium">
                      Stage {decision.stage_number}: {decision.checkpoint}
                    </p>
                    <p className="text-fg-muted">
                      Disposition: {decision.disposition} | Reviewer:{" "}
                      {decision.reviewer} | Scope: {decision.scope}
                    </p>
                    <p className="text-fg-muted">
                      Rationale: {decision.rationale}
                    </p>
                    {decision.checkpoint_evidence ? (
                      <p className="text-fg-muted">
                        Checkpoint evidence: {decision.checkpoint_evidence}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section
            aria-labelledby={`asset-detail-content-${assetId}`}
            data-testid="asset-detail-content"
            className="mt-3"
          >
            <h3
              id={`asset-detail-content-${assetId}`}
              className="text-sm font-medium text-fg"
            >
              Content
            </h3>
            {content === null ? (
              <p
                data-testid="asset-detail-no-content"
                className="mt-1 text-xs text-fg-muted"
              >
                No stored content for this asset kind — the approval records
                above are the record of what was approved.
              </p>
            ) : (
              <AssetContentList entry={content} />
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
