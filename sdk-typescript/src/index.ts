import { AsyncLocalStorage } from "node:async_hooks";
import { createHash, randomUUID } from "node:crypto";
import { z } from "zod";

export const SDK_VERSION = "0.1.0-beta.1";

export type Mode = "observe" | "guard" | "confidential";
export type Action = "allow" | "allow_fields" | "redact" | "require_approval" | "block" | "warn" | "not_evaluated";
export type Risk = "low" | "medium" | "high" | "critical";
export type ComponentType = "workflow" | "model_call" | "tool_call" | "retrieval_call" | "database_call" | "network_egress" | "approval" | "policy_decision";

export interface Policy {
  version: number;
  agent: { name: string; owner: string };
  destinations: Record<string, DestinationPolicy>;
  defaults: {
    undeclared_high_risk_egress: "block" | "warn";
    undeclared_destination: "block" | "warn";
    secrets: "block" | "require_approval";
  };
}

export interface DestinationPolicy {
  type: string;
  domain: string | null;
  risk: Risk;
  allowed_data: string[];
  redact: string[];
  require_approval: string[];
}

export interface Destination {
  id: string;
  type: string;
  domain: string | null;
  provider: string;
  environment?: string;
  risk?: Risk;
}

export interface PolicyDecision {
  action: Action;
  reason: string;
  policy_version: number | null;
  fields: string[];
}

export interface SpanRecord {
  span_id: string;
  parent_span_id: string | null;
  component_type: ComponentType;
  component_name: string;
  start_time: string;
  end_time: string;
  status: "ok" | "error" | "blocked" | "redacted" | "approval_required";
  payload_size_bytes: number;
  token_count: number | null;
  content_hash: string | null;
  data_classes: string[];
  destination_id: string | null;
  policy_decision: PolicyDecision;
  error_summary: { type: string; message: string; stack_hash: string } | null;
  redaction_markers: string[];
}

export interface TraceRecord {
  trace_schema_version: 1;
  trace_id: string;
  run_id: string;
  agent: { name: string; version: string };
  mode: Mode;
  language: "typescript";
  runtime_version: string;
  sdk_version: string;
  created_at: string;
  spans: SpanRecord[];
  destinations: Array<{
    id: string;
    type: string;
    domain: string | null;
    provider: string;
    environment: string;
    risk: Risk;
    declared_in_policy: boolean;
    allowed_data_classes: string[];
    observed_data_classes: string[];
  }>;
}

export const DATA_CLASS_RISK: Record<string, Risk> = {
  account_id: "medium",
  account_notes: "high",
  address: "high",
  claimant_name: "high",
  customer_identifier: "high",
  document_text: "high",
  email: "high",
  incident_description: "medium",
  medical_information: "high",
  model_output: "high",
  policy_number: "medium",
  prompt_content: "high",
  secrets: "critical",
  support_tier: "low",
  tool_payload: "high",
  user_identifier: "high"
};

export const FIELD_NAME_DATA_CLASSES: Record<string, string> = {
  account_id: "account_id",
  account_notes: "account_notes",
  api_key: "secrets",
  claim_notes: "account_notes",
  customer_id: "customer_identifier",
  document: "document_text",
  email: "email",
  medical_information: "medical_information",
  notes: "account_notes",
  policy_number: "policy_number",
  prompt: "prompt_content",
  support_tier: "support_tier",
  user_id: "user_identifier"
};

const riskOrder: Risk[] = ["low", "medium", "high", "critical"];

export function evaluatePolicy(
  policy: Policy,
  destinationId: string | null | undefined,
  destinationRisk: Risk,
  dataClasses: string[],
  fields: string[] = dataClasses,
  mode: Mode = "guard"
): PolicyDecision {
  const data = sortedUnique(dataClasses);
  const observedFields = sortedUnique(fields.length ? fields : data);
  const observedTokens = new Set([...data, ...observedFields]);
  const outputFields = observedFields.length ? observedFields : data;

  if (!destinationId) {
    return { action: "not_evaluated", reason: "no destination", policy_version: policy.version, fields: [] };
  }

  if (observedTokens.has("secrets")) {
    return applyMode({
      action: policy.defaults.secrets,
      reason: "secrets default rule matched",
      policy_version: policy.version,
      fields: outputFields
    }, mode);
  }

  const destination = policy.destinations[destinationId];
  const egressRisk = classifyEgressRisk(destinationRisk, data);

  if (!destination) {
    if (isHighOrCritical(egressRisk)) {
      return applyMode({
        action: policy.defaults.undeclared_high_risk_egress,
        reason: "undeclared high-risk egress",
        policy_version: policy.version,
        fields: outputFields
      }, mode);
    }
    return applyMode({
      action: policy.defaults.undeclared_destination,
      reason: "undeclared destination",
      policy_version: policy.version,
      fields: outputFields
    }, mode);
  }

  const approvalFields = matchedFields(observedFields, data, destination.require_approval);
  if (approvalFields.length) {
    return { action: "require_approval", reason: "destination approval rule matched", policy_version: policy.version, fields: approvalFields };
  }

  const redactionFields = matchedFields(observedFields, data, destination.redact);
  if (redactionFields.length) {
    return { action: "redact", reason: "destination redaction rule matched", policy_version: policy.version, fields: redactionFields };
  }

  const allowed = new Set(destination.allowed_data);
  if (allowed.size && [...observedTokens].some((token) => !allowed.has(token))) {
    let allowedFields = observedFields.filter((field) => allowed.has(field));
    if (!allowedFields.length) {
      allowedFields = data.filter((dataClass) => allowed.has(dataClass));
    }
    return { action: "allow_fields", reason: "destination allowlist excluded fields", policy_version: policy.version, fields: sortedUnique(allowedFields) };
  }

  return { action: "allow", reason: "destination declared and data allowed", policy_version: policy.version, fields: outputFields };
}

export function classifyPayload(value: unknown, fieldName = ""): string[] {
  const classes = new Set<string>();
  if (isClassified(value)) {
    for (const dataClass of value.__capsuleDataClasses) {
      classes.add(dataClass);
    }
    for (const dataClass of classifyPayload(value.value, fieldName)) {
      classes.add(dataClass);
    }
    return sortedUnique([...classes]);
  }
  const fieldClass = FIELD_NAME_DATA_CLASSES[fieldName.toLowerCase()];
  if (fieldClass) {
    classes.add(fieldClass);
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      for (const dataClass of classifyPayload(item)) {
        classes.add(dataClass);
      }
    }
  } else if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      for (const dataClass of classifyPayload(item, key)) {
        classes.add(dataClass);
      }
    }
  }
  return sortedUnique([...classes]);
}

export interface Classified<T> {
  value: T;
  __capsuleDataClasses: string[];
}

export function classified<T>(value: T, dataClasses: string[]): Classified<T> {
  return { value, __capsuleDataClasses: sortedUnique(dataClasses) };
}

export function zodClassified<T extends z.ZodTypeAny>(schema: T, dataClasses: string[]): z.ZodEffects<T, Classified<z.infer<T>>> {
  return schema.transform((value) => classified(value, dataClasses));
}

type ApprovalHandler = (request: { decision: PolicyDecision; destination: Destination; data_classes: string[] }) => boolean | Promise<boolean>;

interface CapsuleOptions {
  mode: Mode;
  policy: Policy;
  agentName: string;
  agentVersion?: string;
  approvalHandler?: ApprovalHandler;
}

interface RunContext {
  runId: string;
  traceId: string;
  createdAt: string;
  spans: SpanRecord[];
  destinations: Map<string, TraceRecord["destinations"][number]>;
}

export class Capsule {
  private readonly context = new AsyncLocalStorage<RunContext>();
  private lastRun: RunContext | null = null;

  constructor(private readonly options: CapsuleOptions) {}

  async run<T>(name: string, fn: () => Promise<T> | T, runId = `run_${safeId(name)}`): Promise<T> {
    const run: RunContext = {
      runId,
      traceId: `trc_${safeId(name)}`,
      createdAt: new Date().toISOString(),
      spans: [],
      destinations: new Map()
    };
    this.lastRun = run;
    return await this.context.run(run, async () => await fn());
  }

  wrapTool<TArgs extends unknown[], TResult>(
    componentName: string,
    destination: Destination,
    call: (...args: TArgs) => Promise<TResult> | TResult
  ): (...args: TArgs) => Promise<TResult> {
    return this.wrapCall("tool_call", componentName, destination, call);
  }

  wrapModel<TArgs extends unknown[], TResult>(
    componentName: string,
    destination: Destination,
    call: (...args: TArgs) => Promise<TResult> | TResult
  ): (...args: TArgs) => Promise<TResult> {
    return this.wrapCall("model_call", componentName, destination, call);
  }

  trace(): TraceRecord {
    const run = this.lastRun;
    if (!run) {
      throw new Error("no run has completed");
    }
    return {
      trace_schema_version: 1,
      trace_id: run.traceId,
      run_id: run.runId,
      agent: { name: this.options.agentName, version: this.options.agentVersion ?? "0.1.0" },
      mode: this.options.mode,
      language: "typescript",
      runtime_version: process.version,
      sdk_version: SDK_VERSION,
      created_at: run.createdAt,
      spans: run.spans,
      destinations: [...run.destinations.values()].sort((a, b) => a.id.localeCompare(b.id))
    };
  }

  private wrapCall<TArgs extends unknown[], TResult>(
    componentType: ComponentType,
    componentName: string,
    destination: Destination,
    call: (...args: TArgs) => Promise<TResult> | TResult
  ): (...args: TArgs) => Promise<TResult> {
    return async (...args: TArgs) => {
      const run = this.context.getStore();
      if (!run) {
        throw new Error("Agent Capsule operation requires an active run context");
      }

      const payload = args.length === 1 ? args[0] : args;
      const dataClasses = classifyPayload(payload);
      const decision = evaluatePolicy(
        this.options.policy,
        destination.id,
        destination.risk ?? "medium",
        dataClasses,
        dataClasses,
        this.options.mode
      );
      const start = new Date().toISOString();
      let status: SpanRecord["status"] = "ok";
      let guardedArgs = args;
      const redactionMarkers: string[] = [];
      const declared = Boolean(this.options.policy.destinations[destination.id]);

      run.destinations.set(destination.id, {
        id: destination.id,
        type: destination.type,
        domain: destination.domain,
        provider: destination.provider,
        environment: destination.environment ?? "production",
        risk: destination.risk ?? "medium",
        declared_in_policy: declared,
        allowed_data_classes: this.options.policy.destinations[destination.id]?.allowed_data ?? [],
        observed_data_classes: dataClasses
      });

      try {
        if (this.options.mode !== "observe" && decision.action === "block") {
          status = "blocked";
          throw new CapsuleGuardError(decision.reason);
        }
        if (this.options.mode !== "observe" && decision.action === "require_approval") {
          const approved = await this.options.approvalHandler?.({ decision, destination, data_classes: dataClasses });
          if (!approved) {
            status = "approval_required";
            throw new CapsuleGuardError(decision.reason);
          }
        }
        if (this.options.mode !== "observe" && (decision.action === "redact" || decision.action === "allow_fields")) {
          if (decision.action === "redact") {
            status = "redacted";
          }
          guardedArgs = transformArguments(args, decision.action, decision.fields) as TArgs;
          redactionMarkers.push(...decision.fields.map((field) => `${decision.action}:${field}`));
        }
        return await call(...guardedArgs);
      } catch (error) {
        if (status === "ok" || status === "redacted") {
          status = "error";
        }
        throw error;
      } finally {
        run.spans.push({
          span_id: `spn_${randomUUID().replaceAll("-", "")}`,
          parent_span_id: null,
          component_type: componentType,
          component_name: componentName,
          start_time: start,
          end_time: new Date().toISOString(),
          status,
          payload_size_bytes: payloadSize(payload),
          token_count: null,
          content_hash: contentHash(payload),
          data_classes: dataClasses,
          destination_id: destination.id,
          policy_decision: decision,
          error_summary: status === "error" ? { type: "Error", message: "call failed", stack_hash: contentHash(componentName) } : null,
          redaction_markers: redactionMarkers
        });
      }
    };
  }
}

export class CapsuleGuardError extends Error {}

function transformArguments(args: unknown[], action: Action, fields: string[]): unknown[] {
  return args.map((arg) => action === "redact" ? redactPayload(arg, fields) : allowFieldsPayload(arg, fields));
}

function redactPayload(value: unknown, fields: string[], fieldName = ""): unknown {
  const selected = new Set(fields);
  if (isClassified(value)) {
    if (value.__capsuleDataClasses.some((dataClass) => selected.has(dataClass))) {
      return `[redacted:${value.__capsuleDataClasses.find((dataClass) => selected.has(dataClass)) ?? "field"}]`;
    }
    return redactPayload(value.value, fields, fieldName);
  }
  const fieldClass = FIELD_NAME_DATA_CLASSES[fieldName.toLowerCase()];
  if ((fieldClass && selected.has(fieldClass)) || (fieldName && selected.has(fieldName))) {
    return `[redacted:${fieldClass ?? fieldName}]`;
  }
  if (Array.isArray(value)) {
    return value.map((item) => redactPayload(item, fields));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, redactPayload(item, fields, key)]));
  }
  return value;
}

function allowFieldsPayload(value: unknown, fields: string[], fieldName = ""): unknown {
  const selected = new Set(fields);
  if (isClassified(value)) {
    return value.__capsuleDataClasses.some((dataClass) => selected.has(dataClass)) ? value.value : "[redacted:allow_fields]";
  }
  const fieldClass = FIELD_NAME_DATA_CLASSES[fieldName.toLowerCase()];
  if (fieldName && fieldClass && !selected.has(fieldClass) && !selected.has(fieldName)) {
    return "[redacted:allow_fields]";
  }
  if (Array.isArray(value)) {
    return value.map((item) => allowFieldsPayload(item, fields));
  }
  if (value && typeof value === "object") {
    const output: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      const keyClass = FIELD_NAME_DATA_CLASSES[key.toLowerCase()];
      if (keyClass && !selected.has(keyClass) && !selected.has(key)) {
        continue;
      }
      output[key] = allowFieldsPayload(item, fields, key);
    }
    return output;
  }
  return value;
}

function matchedFields(fields: string[], dataClasses: string[], rules: string[]): string[] {
  const ruleSet = new Set(rules);
  return sortedUnique([...fields.filter((field) => ruleSet.has(field)), ...dataClasses.filter((dataClass) => ruleSet.has(dataClass))]);
}

function classifyDataRisk(dataClasses: string[]): Risk {
  return dataClasses.reduce<Risk>((risk, dataClass) => maxRisk(risk, DATA_CLASS_RISK[dataClass] ?? "medium"), "low");
}

function classifyEgressRisk(destinationRisk: Risk, dataClasses: string[]): Risk {
  return maxRisk(destinationRisk, classifyDataRisk(dataClasses));
}

function maxRisk(a: Risk, b: Risk): Risk {
  return riskOrder[Math.max(riskOrder.indexOf(a), riskOrder.indexOf(b))] ?? "medium";
}

function isHighOrCritical(risk: Risk): boolean {
  return risk === "high" || risk === "critical";
}

function applyMode(decision: PolicyDecision, mode: Mode): PolicyDecision {
  if (mode === "observe" && decision.action === "block") {
    return { ...decision, action: "warn", reason: `observe_only: ${decision.reason}` };
  }
  return decision;
}

function isClassified(value: unknown): value is Classified<unknown> {
  return Boolean(value && typeof value === "object" && Array.isArray((value as Classified<unknown>).__capsuleDataClasses));
}

function sortedUnique(values: string[]): string[] {
  return [...new Set(values)].sort();
}

function contentHash(value: unknown): string {
  return `sha256:${createHash("sha256").update(JSON.stringify(value, replacer)).digest("hex")}`;
}

function payloadSize(value: unknown): number {
  return Buffer.byteLength(JSON.stringify(value, replacer) ?? "", "utf8");
}

function replacer(_key: string, value: unknown): unknown {
  if (isClassified(value)) {
    return { data_classes: value.__capsuleDataClasses, value: value.value };
  }
  return value;
}

function safeId(value: string): string {
  const slug = value.toLowerCase().replace(/[^a-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
  return slug || randomUUID().replaceAll("-", "");
}
