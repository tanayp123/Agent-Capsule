export type SpanStatus = "ok" | "error" | "blocked" | "redacted" | "approval_required" | string;

export type SafeTraceSpan = {
  span_id: string;
  component_type: string;
  component_name: string;
  duration_ms: number;
  payload_size_bytes: number;
  token_count: number | null;
  status: SpanStatus;
  error_summary: string | null;
  policy_decision: string;
  redaction_markers: string[];
};

export type SafeTrace = {
  safe_trace_version: number;
  source_trace_id: string;
  created_at: string;
  created_by: string;
  redaction_profile: string;
  workflow_graph: {
    nodes: Array<{ id: string; label: string; component_type: string }>;
    edges: Array<{ from: string; to: string }>;
  };
  spans: SafeTraceSpan[];
  component_versions: Record<string, string>;
  policy_decisions: Array<{ span_id: string; action: string; reason: string }>;
  content_hashes: string[];
  redaction_markers: string[];
  diagnostic_summary: {
    status: string;
    failure_span_id: string | null;
    summary: string;
  };
};

export type PrivacyMap = {
  trace_id: string;
  run_id: string;
  policy_version: number;
  destinations: Array<{
    id: string;
    type: string;
    domain: string | null;
    provider?: string;
    environment: string;
    declared_in_policy: boolean;
    destination_risk: string;
    egress_risk: string;
    observed_data_classes: string[];
    allowed_data_classes: string[];
    span_count: number;
    actions: string[];
    findings: string[];
  }>;
  findings: Array<{
    kind: string;
    severity: string;
    destination_id: string;
    risk: string;
    data_classes: string[];
    message: string;
  }>;
  policy_suggestions: Array<{
    destination_id: string;
    action: string;
    description: string;
  }>;
};

export type ReplayComparison = {
  comparison_version: number;
  source_trace_id: string;
  candidate_replay_source_trace_id: string;
  status: string;
  summary: {
    difference_count: number;
    span_count: number;
  };
  differences: Array<{
    category: string;
    span_id?: string;
    message: string;
    expected?: unknown;
    actual?: unknown;
  }>;
};

export type ManifestInspection = {
  manifest_version: number;
  agent_name: string;
  agent_version: string;
  language: string;
  runtime_version: string;
  sdk_version: string;
  container_digest: string;
  policy_hash: string;
  policy_version: number;
  network_destinations: Array<{ id: string; type: string; domain: string; risk: string }>;
  required_secrets: string[];
  usage_meters: Array<{ name: string; unit: string }>;
  signature: {
    algorithm: string;
    key_id: string;
    present: boolean;
  };
};

export type RunSummary = {
  run_id: string;
  trace_id: string;
  agent_name: string;
  status: string;
  span_count: number;
  created_at: string;
};
