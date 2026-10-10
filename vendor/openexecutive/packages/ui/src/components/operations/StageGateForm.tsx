// Schema-driven stage gate form, native cockpit page fragment (asset review and
// approval spec sections 3.3, 3.4 and 4.2). Additive file (ADR 0014). It reads
// the stage's request JSON Schema from `GET /red/stages/{n}/gate-schema` — the
// exact body `POST /red/clients/{tenant}/stages/{n}/gate` accepts — resolves the
// schema's internal `$defs`, renders labeled inputs from it (enums as selects,
// booleans as checkboxes, arrays as add/remove row editors, nested objects one
// level deep and further where the schema nests) and assembles the POST body
// with the pure `assembleGateBody`. The backend remains the sole enforcer of
// prerequisites, expiry and authority: a refusal is rendered verbatim inline
// and nothing is recorded locally.

import { useEffect, useRef, useState } from "react";

import {
  getGateSchema,
  recordStageGate,
  type GateSchema,
} from "@/lib/redOperationsApi";

// One form value as the DOM inputs hold it: text/number inputs and selects
// yield strings, checkboxes yield booleans, row editors yield arrays and
// nested objects.
export type GateFormValue =
  | string
  | number
  | boolean
  | GateFormValue[]
  | { [key: string]: GateFormValue };

export type GateFormValues = { [key: string]: GateFormValue };

interface SchemaNode {
  $ref?: string;
  $defs?: SchemaDefs;
  anyOf?: SchemaNode[];
  type?: string;
  format?: string;
  properties?: Record<string, SchemaNode>;
  required?: string[];
  items?: SchemaNode;
  enum?: unknown[];
  default?: unknown;
}

type SchemaDefs = Record<string, SchemaNode>;

// Dereference one schema node: follow `$ref` into the schema's `$defs` and
// collapse a nullable `anyOf` to its non-null branch (the form renders a
// nullable field as the plain input its non-null branch describes).
export function resolveSchemaNode(node: SchemaNode, defs: SchemaDefs): SchemaNode {
  let current = node;
  if (typeof current.$ref === "string") {
    const name = current.$ref.split("/").pop() ?? "";
    current = defs[name] ?? {};
  }
  if (Array.isArray(current.anyOf)) {
    const branch = current.anyOf.find((candidate) => candidate.type !== "null");
    return branch ? resolveSchemaNode(branch, defs) : {};
  }
  return current;
}

// "intake_package_id" -> "Intake package id": the label a field renders.
export function humanizeFieldName(name: string): string {
  return name.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

// Derivable defaults (asset review and approval spec section 3.3): the current
// workspace, today's date, version 1, and the workspace's registered
// authorities for the actor fields.
export interface GateFormDefaults {
  workspaceId: string;
  authorities: string[];
}

const AUTHORITY_FIELDS = new Set([
  "stage_owner",
  "assigned_owner",
  "approver",
  "proposed_by",
]);

// The domain refuses self-approval, so `proposed_by` starts on a different
// authority than the default approver when the registry offers one.
function proposedByDefault(authorities: string[]): string {
  return authorities[1] ?? authorities[0] ?? "";
}

// The initial form values for one stage's schema, with the derivable defaults
// prefilled. Arrays start empty; the user adds rows.
export function initialGateValues(
  schema: GateSchema,
  defaults: GateFormDefaults,
): GateFormValues {
  const root = schema as SchemaNode;
  return buildObjectValues(root, root.$defs as SchemaDefs | undefined, defaults);
}

function buildObjectValues(
  node: SchemaNode,
  defs: SchemaDefs | undefined,
  defaults: GateFormDefaults,
): GateFormValues {
  const resolved = resolveSchemaNode(node, defs ?? {});
  const values: GateFormValues = {};
  for (const [name, prop] of Object.entries(resolved.properties ?? {})) {
    values[name] = buildPropertyValue(name, prop, defs ?? {}, defaults);
  }
  return values;
}

function buildPropertyValue(
  name: string,
  prop: SchemaNode,
  defs: SchemaDefs,
  defaults: GateFormDefaults,
): GateFormValue {
  const node = resolveSchemaNode(prop, defs);
  if (node.type === "object") return buildObjectValues(node, defs, defaults);
  if (node.type === "array") return [];
  if (name === "workspace_id") return defaults.workspaceId;
  if (name === "on") return today();
  if (name === "version") return "1";
  if (Array.isArray(node.enum)) {
    return node.enum.length > 0 ? String(node.enum[0]) : "";
  }
  if (node.default !== undefined && node.default !== null) {
    return String(node.default);
  }
  if (name === "proposed_by") return proposedByDefault(defaults.authorities);
  if (AUTHORITY_FIELDS.has(name)) return defaults.authorities[0] ?? "";
  return "";
}

// Marker for a value the form leaves unset: the assembled body omits it and
// the backend enforces whatever the field's absence means.
const OMITTED: unique symbol = Symbol("omitted");

// Map form values to the exact POST body the stage's gate route accepts
// (asset review and approval spec section 3.3). Pure so the seed payloads can
// be round-tripped through it without driving the DOM. Strings from number
// inputs coerce back to integers, empty inputs mean "unset" and are omitted,
// and array rows assemble through the same rules recursively.
export function assembleGateBody(
  schema: GateSchema,
  values: GateFormValues,
): Record<string, unknown> {
  const root = schema as SchemaNode;
  return assembleObjectValues(root, root.$defs as SchemaDefs | undefined, values);
}

function assembleObjectValues(
  node: SchemaNode,
  defs: SchemaDefs | undefined,
  values: GateFormValues,
): Record<string, unknown> {
  const resolved = resolveSchemaNode(node, defs ?? {});
  const body: Record<string, unknown> = {};
  for (const [name, prop] of Object.entries(resolved.properties ?? {})) {
    if (!(name in values)) continue;
    const assembled = assemblePropertyValue(prop, defs ?? {}, values[name]);
    if (assembled !== OMITTED) body[name] = assembled;
  }
  return body;
}

function assemblePropertyValue(
  prop: SchemaNode,
  defs: SchemaDefs,
  value: GateFormValue | undefined,
): unknown {
  const node = resolveSchemaNode(prop, defs);
  if (node.type === "object") {
    return assembleObjectValues(node, defs, (value ?? {}) as GateFormValues);
  }
  if (node.type === "array") {
    if (!Array.isArray(value)) return OMITTED;
    const items = node.items ? resolveSchemaNode(node.items, defs) : {};
    if (items.type === "object") {
      return value.map((row) =>
        assembleObjectValues(items, defs, (row ?? {}) as GateFormValues),
      );
    }
    // An empty text input is "no value", so empty items are dropped.
    return value
      .filter((item) => item !== "")
      .map((item) => (typeof item === "string" ? item : String(item)));
  }
  if (node.type === "integer") {
    if (value === "" || value === null || value === undefined) return OMITTED;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.trunc(parsed) : OMITTED;
  }
  if (node.type === "boolean") {
    if (value === null || value === undefined) return OMITTED;
    return Boolean(value);
  }
  // string, including the nullable strings rendered as plain text inputs
  if (value === "" || value === null || value === undefined) return OMITTED;
  return typeof value === "string" ? value : String(value);
}

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

interface EditorProps {
  node: SchemaNode;
  defs: SchemaDefs;
  values: GateFormValues;
  onChange: (next: GateFormValues) => void;
  prefix: string;
  defaults: GateFormDefaults;
}

// The labeled inputs for one object level. Field labels carry their path
// ("Avatar version", "Assets row 1 kind") so repeated field names stay
// distinguishable and every control keeps a unique accessible name.
function ObjectFields({
  node,
  defs,
  values,
  onChange,
  prefix,
  defaults,
}: EditorProps) {
  const resolved = resolveSchemaNode(node, defs);
  const properties = resolved.properties ?? {};
  // The backend pins the canonical kind name as an intake asset's asset_id, so
  // a row's asset_id follows its kind until it is edited by hand.
  const kindLinkage = "kind" in properties && "asset_id" in properties;
  const setField = (name: string, next: GateFormValue) => {
    const updated: GateFormValues = { ...values, [name]: next };
    if (kindLinkage && name === "kind") {
      const currentAssetId = values["asset_id"];
      const previousKind = values["kind"];
      if (currentAssetId === "" || currentAssetId === previousKind) {
        updated["asset_id"] = next;
      }
    }
    onChange(updated);
  };
  return (
    <>
      {Object.entries(properties).map(([name, prop]) => (
        <PropertyValueEditor
          key={name}
          name={name}
          prop={prop}
          defs={defs}
          value={values[name]}
          onChange={(next) => setField(name, next)}
          prefix={prefix === "" ? humanizeFieldName(name) : `${prefix} ${humanizeFieldName(name)}`}
          defaults={defaults}
        />
      ))}
    </>
  );
}

interface PropertyEditorProps {
  name: string;
  prop: SchemaNode;
  defs: SchemaDefs;
  value: GateFormValue | undefined;
  onChange: (next: GateFormValue) => void;
  prefix: string;
  defaults: GateFormDefaults;
}

function PropertyValueEditor({
  name,
  prop,
  defs,
  value,
  onChange,
  prefix,
  defaults,
}: PropertyEditorProps) {
  const node = resolveSchemaNode(prop, defs);
  if (node.type === "object") {
    return (
      <fieldset className="mt-3 rounded-lg border border-line bg-surface p-3">
        <legend className="text-xs font-medium text-fg">{prefix}</legend>
        <ObjectFields
          node={node}
          defs={defs}
          values={(value ?? {}) as GateFormValues}
          onChange={onChange}
          prefix={prefix}
          defaults={defaults}
        />
      </fieldset>
    );
  }
  if (node.type === "array") {
    const items = node.items ? resolveSchemaNode(node.items, defs) : {};
    if (items.type === "object") {
      return (
        <RowArrayEditor
          items={items}
          defs={defs}
          rows={Array.isArray(value) ? value : []}
          onChange={onChange}
          prefix={prefix}
          defaults={defaults}
        />
      );
    }
    return (
      <StringArrayEditor
        items={Array.isArray(value) ? value.map(String) : []}
        onChange={onChange}
        prefix={prefix}
      />
    );
  }
  return (
    <ScalarInput
      name={name}
      node={node}
      value={value}
      onChange={onChange}
      prefix={prefix}
      authorities={defaults.authorities}
    />
  );
}

interface ScalarInputProps {
  name: string;
  node: SchemaNode;
  value: GateFormValue | undefined;
  onChange: (next: GateFormValue) => void;
  prefix: string;
  authorities: string[];
}

function ScalarInput({
  name,
  node,
  value,
  onChange,
  prefix,
  authorities,
}: ScalarInputProps) {
  if (Array.isArray(node.enum) && node.enum.length > 0) {
    return labelClass(
      <select
        value={String(value ?? "")}
        onChange={(event) => onChange(event.target.value)}
        className={inputClass}
      >
        {node.enum.map((option) => (
          <option key={String(option)} value={String(option)}>
            {String(option)}
          </option>
        ))}
      </select>,
      prefix,
    );
  }
  if (node.type === "boolean") {
    return (
      <label className="text-xs text-fg-muted flex items-center gap-2">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(event.target.checked)}
          className="rounded border border-line bg-surface text-fg focus:outline-none focus:border-line-strong"
        />
        {prefix}
      </label>
    );
  }
  if (AUTHORITY_FIELDS.has(name) && authorities.length > 0) {
    return labelClass(
      <select
        value={String(value ?? "")}
        onChange={(event) => onChange(event.target.value)}
        className={inputClass}
      >
        {authorities.map((authority) => (
          <option key={authority} value={authority}>
            {authority}
          </option>
        ))}
      </select>,
      prefix,
    );
  }
  const type =
    node.format === "date"
      ? "date"
      : node.type === "integer"
        ? "number"
        : "text";
  return labelClass(
    <input
      type={type}
      value={String(value ?? "")}
      onChange={(event) => onChange(event.target.value)}
      className={inputClass}
    />,
    prefix,
  );
}

interface RowArrayEditorProps {
  items: SchemaNode;
  defs: SchemaDefs;
  rows: GateFormValue[];
  onChange: (next: GateFormValue) => void;
  prefix: string;
  defaults: GateFormDefaults;
}

function RowArrayEditor({
  items,
  defs,
  rows,
  onChange,
  prefix,
  defaults,
}: RowArrayEditorProps) {
  return (
    <fieldset className="mt-3 rounded-lg border border-line bg-surface p-3">
      <legend className="text-xs font-medium text-fg">{prefix}</legend>
      <ol className="space-y-3">
        {rows.map((row, index) => (
          <li
            key={index}
            className="rounded-lg border border-line bg-surface-elevated p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-medium text-fg">
                {prefix} row {index + 1}
              </p>
              <button
                type="button"
                aria-label={`Remove ${prefix} row ${index + 1}`}
                onClick={() =>
                  onChange(rows.filter((_, rowIndex) => rowIndex !== index))
                }
                className={quietButtonClass}
              >
                Remove
              </button>
            </div>
            <ObjectFields
              node={items}
              defs={defs}
              values={(row ?? {}) as GateFormValues}
              onChange={(nextRow) =>
                onChange(
                  rows.map((existing, rowIndex) =>
                    rowIndex === index ? nextRow : existing,
                  ),
                )
              }
              prefix={`${prefix} row ${index + 1}`}
              defaults={defaults}
            />
          </li>
        ))}
      </ol>
      <button
        type="button"
        aria-label={`Add ${prefix} row`}
        onClick={() =>
          onChange([...rows, buildObjectValues(items, defs, defaults)])
        }
        className={quietButtonClass}
      >
        Add row
      </button>
    </fieldset>
  );
}

interface StringArrayEditorProps {
  items: string[];
  onChange: (next: GateFormValue) => void;
  prefix: string;
}

function StringArrayEditor({ items, onChange, prefix }: StringArrayEditorProps) {
  return (
    <fieldset className="mt-3 rounded-lg border border-line bg-surface p-3">
      <legend className="text-xs font-medium text-fg">{prefix}</legend>
      <ul className="space-y-2">
        {items.map((item, index) => (
          <li key={index} className="flex items-center gap-2">
            {labelClass(
              <input
                type="text"
                value={item}
                onChange={(event) =>
                  onChange(
                    items.map((existing, itemIndex) =>
                      itemIndex === index ? event.target.value : existing,
                    ),
                  )
                }
                className={inputClass}
              />,
              `${prefix} item ${index + 1}`,
            )}
            <button
              type="button"
              aria-label={`Remove ${prefix} item ${index + 1}`}
              onClick={() => onChange(items.filter((_, i) => i !== index))}
              className={quietButtonClass}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        aria-label={`Add ${prefix} item`}
        onClick={() => onChange([...items, ""])}
        className={quietButtonClass}
      >
        Add item
      </button>
    </fieldset>
  );
}

export interface StageGateFormProps {
  tenantId: string;
  stageNumber: number;
  workspaceId: string;
  authorities: string[];
  onRecorded: () => void;
  onClose: () => void;
}

export function StageGateForm({
  tenantId,
  stageNumber,
  workspaceId,
  authorities,
  onRecorded,
  onClose,
}: StageGateFormProps) {
  const [schema, setSchema] = useState<GateSchema | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [values, setValues] = useState<GateFormValues>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // The defaults snapshot at open time: a later authorities refresh must not
  // reset in-progress edits.
  const defaultsRef = useRef({ workspaceId, authorities });
  defaultsRef.current = { workspaceId, authorities };

  useEffect(() => {
    let cancelled = false;
    setSchema(null);
    setValues({});
    setLoadError(null);
    setSubmitError(null);
    getGateSchema(stageNumber)
      .then((loaded) => {
        if (cancelled) return;
        setSchema(loaded);
        setValues(initialGateValues(loaded, defaultsRef.current));
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(
          err instanceof Error
            ? err.message
            : "Failed to load the gate schema",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [stageNumber]);

  const proposedBy = values["proposed_by"];
  const approver = values["approver"];
  const selfApprovalRefusal =
    typeof proposedBy === "string" &&
    proposedBy !== "" &&
    proposedBy === approver;

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!schema || submitting) return;
    const body = assembleGateBody(schema, values);
    setSubmitting(true);
    setSubmitError(null);
    recordStageGate(tenantId, stageNumber, body)
      .then(() => {
        setSubmitting(false);
        onRecorded();
      })
      .catch((err) => {
        setSubmitting(false);
        setSubmitError(
          err instanceof Error
            ? err.message
            : "Failed to record the stage gate",
        );
      });
  };

  return (
    <form data-testid="stage-gate-form" onSubmit={handleSubmit}>
      {loadError ? (
        <p
          role="alert"
          className="mt-3 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400"
        >
          {loadError}
        </p>
      ) : null}
      {!schema && !loadError ? (
        <p role="status" className="mt-3 text-sm text-fg-muted">
          Loading gate schema…
        </p>
      ) : null}
      {schema ? (
        <ObjectFields
          node={schema as SchemaNode}
          defs={(schema as SchemaNode).$defs as SchemaDefs}
          values={values}
          onChange={setValues}
          prefix=""
          defaults={defaultsRef.current}
        />
      ) : null}
      {selfApprovalRefusal ? (
        <p
          data-testid="gate-self-approval-warning"
          className="mt-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-400"
        >
          the domain refuses self-approval
        </p>
      ) : null}
      {submitError ? (
        <p
          role="alert"
          data-testid="gate-error"
          className="mt-3 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400"
        >
          {submitError}
        </p>
      ) : null}
      <div className="mt-4 flex items-center gap-3">
        <button
          type="submit"
          data-testid="gate-submit"
          disabled={!schema || submitting}
          className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong focus:outline-none focus:border-line-strong"
        >
          Record gate
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong focus:outline-none focus:border-line-strong"
        >
          Cancel
        </button>
        {submitting ? (
          <span role="status" className="text-xs text-fg-muted">
            Recording gate…
          </span>
        ) : null}
      </div>
    </form>
  );
}
