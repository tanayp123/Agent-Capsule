import { manifestInspection, privacyMap, replayComparison, runs, safeTrace } from "@/lib/fixture-data";
import type { ManifestInspection, PrivacyMap, ReplayComparison, RunSummary, SafeTrace } from "@/lib/types";

export type ConsoleSnapshot = {
  runs: RunSummary[];
  safeTrace: SafeTrace;
  privacyMap: PrivacyMap;
  replayComparison: ReplayComparison;
  manifest: ManifestInspection;
  source: "fixture" | "local-api";
};

export type LiveAgentRunResult = {
  ok: boolean;
  message: string;
  run: {
    run_id: string;
    trace_id: string;
    agent: { name?: string; version?: string };
    mode?: string;
    created_at?: string;
    span_count?: number;
    destinations?: unknown[];
  };
  safe_trace: SafeTrace;
  privacy_map: PrivacyMap;
  test_scenario?: {
    id: string;
    name: string;
    description: string;
    expected_result: string;
    data_classes: string[];
    destination_id: string;
  };
  agent_under_test?: {
    execution_mode: string;
    language: string;
    source_file: string;
    entrypoint: string;
    instrumentation: string[];
    scenario_id: string;
  };
  test_result?: {
    status: string;
    summary: string;
    expected_result: string;
    safe_payloads_only: boolean;
    encrypted_payloads: number;
  };
  proof: {
    safe_trace_ready: boolean;
    encrypted_payloads: number;
    redaction_markers: string[];
    policy_findings: number;
  };
  next_actions: string[];
};

export type ScenarioSuiteResult = {
  scenario_id: string;
  scenario_name: string;
  expected_result: string;
  data_classes: string[];
  destination_id: string;
  status: string;
  summary: string;
  run_id: string;
  trace_id: string;
  finding_count: number;
  encrypted_payloads: number;
  safe_payloads_only: boolean;
};

export type ScenarioSuiteRunResult = {
  ok: boolean;
  suite_id: string;
  agent_id: string;
  agent_name: string;
  created_at: string;
  overall_status: string;
  scenario_count: number;
  total_findings: number;
  safe_payloads_only: boolean;
  results: ScenarioSuiteResult[];
  next_action: string;
};

export type OpenedSuiteRunResult = {
  run: RunSummary;
  safe_trace: SafeTrace;
  privacy_map: PrivacyMap;
  replay_comparison: ReplayComparison;
};

export type EvidencePackageResult = {
  ok: boolean;
  evidence_package_version: number;
  package_id: string;
  created_at: string;
  download_filename: string;
  run: {
    run_id: string;
    trace_id: string;
    agent?: { name?: string; version?: string };
  };
  selected_policy_response: {
    action: string;
    title: string;
    outcome: string;
    ci_status: string;
    patch_preview: string[];
  };
  ci_gate: {
    status: string;
    summary: string;
    open_high_risk_findings: number;
    requires_policy_commit: boolean;
    blocks_plaintext_payloads: boolean;
  };
  redaction_attestation: {
    contains_plaintext_payloads: boolean;
    safe_trace_profile?: string;
    redaction_markers: string[];
    content_hash_count: number;
  };
  artifact?: {
    saved: boolean;
    path?: string;
    relative_path?: string;
    sha256?: string;
    sidecar_relative_path?: string;
    verification_status?: string;
  };
  contents: {
    safe_trace: SafeTrace;
    privacy_map: PrivacyMap;
  };
};

export type EvidencePackageVerificationResult = {
  ok: boolean;
  package_id: string;
  checked_at: string;
  verification_status: string;
  sha256: string;
  expected_sha256: string;
  artifact: {
    path: string;
    relative_path: string;
    sidecar_path: string;
    sidecar_relative_path: string;
  };
};

export type CustomerVerificationReport = {
  ok: boolean;
  report_version: number;
  package_id: string;
  generated_at: string;
  title: string;
  verification: {
    status: string;
    sha256: string;
    sidecar: string;
  };
  customer_summary: {
    headline: string;
    audience: string;
    status: string;
  };
  run: {
    run_id?: string;
    trace_id?: string;
    agent_name?: string;
    agent_version?: string;
    mode?: string;
    span_count?: number;
  };
  policy_response: {
    action: string;
    title: string;
    outcome: string;
    ci_status: string;
    patch_preview: string[];
  };
  ci_gate: {
    status: string;
    summary: string;
    open_high_risk_findings: number;
    requires_policy_commit: boolean;
    blocks_plaintext_payloads: boolean;
  };
  scorecard: {
    score: number;
    status: string;
    summary: string;
    checks: Array<{
      id: string;
      label: string;
      status: "pass" | "review" | "fail" | string;
      detail: string;
    }>;
  };
  privacy_summary: {
    destination_count: number;
    finding_count: number;
    redaction_marker_count: number;
    content_hash_count: number;
    plaintext_payloads_included: boolean;
  };
  controls: string[];
  destinations: Array<{
    id: string;
    domain: string | null;
    egress_risk: string;
    declared_in_policy: boolean;
    observed_data_classes: string[];
    findings: string[];
    actions?: string[];
  }>;
};

export class LocalApiBridgeClient {
  constructor(
    private readonly baseUrl: string | null,
    private readonly sessionToken: string
  ) {}

  async loadSnapshot(): Promise<ConsoleSnapshot> {
    if (!this.baseUrl) {
      return fixtureSnapshot();
    }

    try {
      const apiRuns = normalizeRuns(await this.fetchJson<RunsResponse>("/runs"));
      const runId = apiRuns[0]?.run_id;
      if (!runId) {
        throw new Error("Local API returned no runs");
      }
      const [apiTrace, apiPrivacyMap, apiReplay, apiManifest] = await Promise.all([
        this.fetchJson<SafeTrace>(`/runs/${runId}/timeline`),
        this.fetchJson<PrivacyMap>(`/runs/${runId}/privacy-map`),
        this.fetchJson<ReplayResponse>(`/runs/${runId}/replay`, {
          method: "POST",
          body: { mode: "structural" }
        }).then(normalizeReplay),
        this.fetchJson<Partial<ManifestInspection>>("/manifests/claims-triage")
          .then(normalizeManifest)
          .catch(() => manifestInspection)
      ]);
      return {
        runs: apiRuns,
        safeTrace: apiTrace,
        privacyMap: apiPrivacyMap,
        replayComparison: apiReplay,
        manifest: apiManifest,
        source: "local-api"
      };
    } catch {
      return fixtureSnapshot();
    }
  }

  async endSession(): Promise<void> {
    if (!this.baseUrl) {
      return;
    }
    try {
      await this.fetchJson<{ ok: boolean }>("/session/end", { method: "POST", keepalive: true });
    } catch {
      // The bridge may already be gone when the browser tab is closing.
    }
  }

  async runLiveAgent(agentId: string, scenarioId: string): Promise<LiveAgentRunResult | null> {
    if (!this.baseUrl) {
      return null;
    }
    return this.fetchJson<LiveAgentRunResult>(`/live-agents/${agentId}/run`, {
      method: "POST",
      body: {
        scenario_id: scenarioId
      }
    });
  }

  async runScenarioSuite(agentId: string): Promise<ScenarioSuiteRunResult | null> {
    if (!this.baseUrl) {
      return null;
    }
    return this.fetchJson<ScenarioSuiteRunResult>(`/live-agents/${agentId}/scenario-suite`, {
      method: "POST",
      body: {}
    });
  }

  async loadRunEvidence(runId: string): Promise<OpenedSuiteRunResult | null> {
    if (!this.baseUrl) {
      return null;
    }
    const [run, safeTrace, privacyMap, replayComparison] = await Promise.all([
      this.fetchJson<Partial<RunSummary> & { agent?: { name?: string }; span_count?: number }>(`/runs/${runId}`),
      this.fetchJson<SafeTrace>(`/runs/${runId}/timeline`),
      this.fetchJson<PrivacyMap>(`/runs/${runId}/privacy-map`),
      this.fetchJson<ReplayResponse>(`/runs/${runId}/replay`, {
        method: "POST",
        body: { mode: "structural" }
      }).then(normalizeReplay)
    ]);
    return {
      run: normalizeRunDetail(run, runId),
      safe_trace: safeTrace,
      privacy_map: privacyMap,
      replay_comparison: replayComparison
    };
  }

  async createEvidencePackage(
    runId: string,
    policyResponse: Record<string, unknown>
  ): Promise<EvidencePackageResult | null> {
    if (!this.baseUrl) {
      return null;
    }
    return this.fetchJson<EvidencePackageResult>(`/runs/${runId}/evidence-package`, {
      method: "POST",
      body: {
        policy_response: policyResponse
      }
    });
  }

  async verifyEvidencePackage(packageId: string): Promise<EvidencePackageVerificationResult | null> {
    if (!this.baseUrl) {
      return null;
    }
    return this.fetchJson<EvidencePackageVerificationResult>(`/evidence-packages/${packageId}/verify`);
  }

  async getCustomerVerificationReport(packageId: string): Promise<CustomerVerificationReport | null> {
    if (!this.baseUrl) {
      return null;
    }
    return this.fetchJson<CustomerVerificationReport>(`/evidence-packages/${packageId}/customer-report`);
  }

  private async fetchJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: options.method ?? "GET",
      headers: {
        Authorization: `Bearer ${this.sessionToken}`,
        "X-Agent-Capsule-Session": this.sessionToken,
        ...(options.body ? { "Content-Type": "application/json" } : {})
      },
      cache: "no-store",
      keepalive: options.keepalive,
      body: options.body ? JSON.stringify(options.body) : undefined
    });
    if (!response.ok) {
      throw new Error(`Local API request failed: ${response.status}`);
    }
    return (await response.json()) as T;
  }
}

type RequestOptions = {
  method?: "GET" | "POST";
  body?: Record<string, unknown>;
  keepalive?: boolean;
};

type RunsResponse = RunSummary[] | { ok?: boolean; runs?: RunSummary[] };

type ReplayResponse = ReplayComparison | {
  source_trace_id?: string;
  workflow?: { span_count?: number };
  spans?: unknown[];
};

function normalizeRuns(response: RunsResponse): RunSummary[] {
  const values = Array.isArray(response) ? response : response.runs ?? [];
  return values.map((run) => ({
    ...run,
    status: run.status ?? "ok"
  }));
}

function normalizeRunDetail(
  response: Partial<RunSummary> & { agent?: { name?: string }; span_count?: number },
  runId: string
): RunSummary {
  return {
    run_id: response.run_id ?? runId,
    trace_id: response.trace_id ?? "local-trace",
    agent_name: response.agent_name ?? response.agent?.name ?? "agent",
    status: response.status ?? "prepared",
    span_count: response.span_count ?? 0,
    created_at: response.created_at ?? new Date().toISOString()
  };
}

function normalizeReplay(response: ReplayResponse): ReplayComparison {
  if ("comparison_version" in response) {
    return response;
  }
  return {
    comparison_version: 1,
    source_trace_id: response.source_trace_id ?? "local-trace",
    candidate_replay_source_trace_id: response.source_trace_id ?? "local-trace",
    status: "prepared",
    summary: {
      difference_count: 0,
      span_count: response.workflow?.span_count ?? response.spans?.length ?? 0
    },
    differences: []
  };
}

function normalizeManifest(response: Partial<ManifestInspection>): ManifestInspection {
  return {
    manifest_version: response.manifest_version ?? manifestInspection.manifest_version,
    agent_name: response.agent_name ?? manifestInspection.agent_name,
    agent_version: response.agent_version ?? manifestInspection.agent_version,
    language: response.language ?? manifestInspection.language,
    runtime_version: response.runtime_version ?? manifestInspection.runtime_version,
    sdk_version: response.sdk_version ?? manifestInspection.sdk_version,
    container_digest: response.container_digest ?? "local-development",
    policy_hash: response.policy_hash ?? "local-policy",
    policy_version: response.policy_version ?? manifestInspection.policy_version,
    network_destinations: response.network_destinations ?? [],
    required_secrets: response.required_secrets ?? [],
    usage_meters: response.usage_meters ?? [],
    signature: {
      algorithm: response.signature?.algorithm ?? manifestInspection.signature.algorithm,
      key_id: response.signature?.key_id ?? manifestInspection.signature.key_id,
      present: Boolean(response.signature?.present)
    }
  };
}

export function fixtureSnapshot(): ConsoleSnapshot {
  return {
    runs,
    safeTrace,
    privacyMap,
    replayComparison,
    manifest: manifestInspection,
    source: "fixture"
  };
}
