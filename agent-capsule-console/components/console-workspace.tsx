"use client";

import * as React from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Download,
  Eye,
  FileJson,
  LockKeyhole,
  PlayCircle,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";
import {
  LocalApiBridgeClient,
  type ConsoleSnapshot,
  fixtureSnapshot,
  type CustomerVerificationReport,
  type EvidencePackageResult,
  type LiveAgentRunResult,
  type ScenarioSuiteRunResult,
  type ScenarioSuiteResult
} from "@/lib/api-client";
import { getEphemeralSessionToken, rotateEphemeralSessionToken, setEphemeralSessionToken } from "@/lib/session-token";
import type { PrivacyMap, RunSummary, SafeTrace } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";

type StepId = "overview" | "agents" | "flow" | "proof";
type AgentStatus = "Ready" | "Needs review" | "Blocked";
type AgentRisk = "Low" | "Medium" | "High" | "Critical";

type AgentRecord = {
  id: string;
  name: string;
  work: string;
  owner: string;
  language: string;
  status: AgentStatus;
  risk: AgentRisk;
  runsToday: number;
  findings: number;
  policyAction: string;
  destination: string;
  dataClasses: string[];
};

type LiveTestScenario = {
  id: string;
  title: string;
  body: string;
  expectedResult: string;
  dataClasses: string[];
};

type LiveRunStatus = {
  state: "idle" | "running" | "ready" | "demo" | "error";
  message: string;
  agentId?: string;
  scenarioId?: string;
  scenarioName?: string;
  resultStatus?: string;
  resultSummary?: string;
  expectedResult?: string;
  encryptedPayloads?: number;
  safePayloadsOnly?: boolean;
  runId?: string;
  traceId?: string;
  spanCount?: number;
  findings?: number;
};

type ScenarioSuiteStatus = {
  state: "idle" | "running" | "ready" | "demo" | "error";
  message: string;
  suiteId?: string;
  agentId?: string;
  overallStatus?: string;
  scenarioCount?: number;
  totalFindings?: number;
  safePayloadsOnly?: boolean;
  results?: ScenarioSuiteResult[];
  nextAction?: string;
};

type EvidencePackageStatus = {
  state: "idle" | "building" | "ready" | "demo" | "verifying" | "error";
  message: string;
  packageId?: string;
  filename?: string;
  relativePath?: string;
  sha256?: string;
  sidecarPath?: string;
  verificationStatus?: string;
  ciStatus?: string;
  customerReportStatus?: string;
  customerReportHeadline?: string;
  customerReportDestinations?: number;
  customerReportFindings?: number;
  customerReportControls?: number;
  customerReport?: CustomerVerificationReport;
  source?: "local-api" | "fixture";
};

type PolicyDecisionId = "allow" | "allow_fields" | "redact" | "require_approval" | "block";

type PolicyDecisionOption = {
  id: PolicyDecisionId;
  title: string;
  body: string;
  outcome: string;
  ciStatus: string;
  proofStatus: string;
  patchLines: string[];
  tone: "neutral" | "green" | "amber" | "red" | "blue";
};

type ReleaseGateCheckStatus = "pass" | "review" | "fail";

type ReleaseGateStatus = "ready" | "review" | "blocked";

type ReleaseGateCheck = {
  label: string;
  status: ReleaseGateCheckStatus;
  detail: string;
};

type ReleaseGate = {
  status: ReleaseGateStatus;
  label: string;
  summary: string;
  tone: "green" | "amber" | "red";
  checks: ReleaseGateCheck[];
};

const steps: Array<{ id: StepId; title: string; plainTitle: string; helper: string }> = [
  {
    id: "overview",
    title: "Company overview",
    plainTitle: "Start here",
    helper: "Show the company, the problem, and the value in one screen."
  },
  {
    id: "agents",
    title: "Choose an agent",
    plainTitle: "Pick an agent",
    helper: "Select one of the company agents to inspect."
  },
  {
    id: "flow",
    title: "Review data flow",
    plainTitle: "See where data went",
    helper: "Show destinations, data classes, and policy status without plaintext."
  },
  {
    id: "proof",
    title: "Share proof",
    plainTitle: "Export safe evidence",
    helper: "Show the safe trace and enterprise evidence packet."
  }
];

const company = {
  name: "Northstar Claims Group",
  description: "A company using AI agents across claims, support, legal, finance, and risk teams.",
  environment: "Production-like demo workspace",
  buyerLine: "For AI startups selling agents to enterprise customers"
};

const liveTestScenarios: LiveTestScenario[] = [
  {
    id: "sensitive-crm-egress",
    title: "Sensitive CRM egress",
    body: "Contact and account-note data reaches an external CRM.",
    expectedResult: "High-risk destination review",
    dataClasses: ["email", "account_notes"]
  },
  {
    id: "metadata-only-check",
    title: "Metadata-only update",
    body: "Operational metadata moves through the same tool path.",
    expectedResult: "Destination declaration review",
    dataClasses: ["operational_metadata"]
  },
  {
    id: "approval-required",
    title: "Approval-required note",
    body: "Sensitive notes are prepared for a human approval gate.",
    expectedResult: "Human approval control",
    dataClasses: ["email", "account_notes", "medical_context"]
  }
];

const agents: AgentRecord[] = [
  {
    id: "claims-triage",
    name: "Claims Triage",
    work: "Routes insurance claims and updates CRM records.",
    owner: "Claims team",
    language: "Python",
    status: "Needs review",
    risk: "High",
    runsToday: 1842,
    findings: 2,
    policyAction: "Redact email and account notes before CRM egress.",
    destination: "api.crm.example",
    dataClasses: ["email", "account_notes"]
  },
  {
    id: "support-copilot",
    name: "Support Copilot",
    work: "Drafts support replies from safe case metadata.",
    owner: "Support team",
    language: "TypeScript",
    status: "Ready",
    risk: "Medium",
    runsToday: 3218,
    findings: 0,
    policyAction: "Allowed under support metadata policy.",
    destination: "tickets.internal",
    dataClasses: ["account_id", "support_tier"]
  },
  {
    id: "contract-review",
    name: "Contract Review",
    work: "Reviews vendor contracts and flags risky clauses.",
    owner: "Legal team",
    language: "Java",
    status: "Needs review",
    risk: "Critical",
    runsToday: 96,
    findings: 3,
    policyAction: "Require human approval for document text.",
    destination: "docs.legal.internal",
    dataClasses: ["document_text", "user_identifier"]
  },
  {
    id: "invoice-recon",
    name: "Invoice Reconciliation",
    work: "Matches invoices, purchase orders, and exceptions.",
    owner: "Finance team",
    language: "Go",
    status: "Ready",
    risk: "Medium",
    runsToday: 612,
    findings: 0,
    policyAction: "Allowed for internal ERP destination.",
    destination: "erp.internal",
    dataClasses: ["account_id", "tool_payload"]
  },
  {
    id: "sales-research",
    name: "Sales Research",
    work: "Builds account briefs from public and CRM metadata.",
    owner: "Revenue team",
    language: "TypeScript",
    status: "Ready",
    risk: "Medium",
    runsToday: 1450,
    findings: 1,
    policyAction: "Allow selected CRM fields only.",
    destination: "api.crm.example",
    dataClasses: ["account_id", "support_tier"]
  },
  {
    id: "benefits-eligibility",
    name: "Benefits Eligibility",
    work: "Checks eligibility rules and prepares review packets.",
    owner: "Benefits team",
    language: "Rust",
    status: "Blocked",
    risk: "Critical",
    runsToday: 284,
    findings: 4,
    policyAction: "Block medical data to model provider.",
    destination: "api.model.example",
    dataClasses: ["medical_information"]
  },
  {
    id: "fraud-signal",
    name: "Fraud Signal Triage",
    work: "Recommends investigation queues from risk signals.",
    owner: "Risk team",
    language: "Python",
    status: "Ready",
    risk: "High",
    runsToday: 421,
    findings: 0,
    policyAction: "Allowed in confidential customer route.",
    destination: "risk.internal",
    dataClasses: ["customer_identifier", "tool_payload"]
  },
  {
    id: "underwriting",
    name: "Underwriting Assistant",
    work: "Summarizes application evidence for underwriters.",
    owner: "Underwriting team",
    language: "Python",
    status: "Needs review",
    risk: "High",
    runsToday: 173,
    findings: 2,
    policyAction: "Require approval for account notes.",
    destination: "api.crm.example",
    dataClasses: ["account_notes"]
  },
  {
    id: "vendor-risk",
    name: "Vendor Risk Monitor",
    work: "Reviews vendor updates and prepares risk summaries.",
    owner: "Security team",
    language: "Java",
    status: "Ready",
    risk: "Medium",
    runsToday: 58,
    findings: 0,
    policyAction: "Allowed for vendor portal metadata.",
    destination: "vendors.internal",
    dataClasses: ["document_text", "account_id"]
  },
  {
    id: "renewal-forecasting",
    name: "Renewal Forecasting",
    work: "Forecasts renewal risk and summarizes account changes.",
    owner: "Success team",
    language: "Go",
    status: "Ready",
    risk: "Medium",
    runsToday: 903,
    findings: 0,
    policyAction: "Allowed for declared CRM fields.",
    destination: "analytics.internal",
    dataClasses: ["account_id"]
  }
];

const policyDecisionOptions: PolicyDecisionOption[] = [
  {
    id: "allow",
    title: "Allow destination",
    body: "Declare this destination and allow the observed data classes.",
    outcome: "Destination allowed after security review.",
    ciStatus: "CI gate: requires reviewer sign-off for high-risk data.",
    proofStatus: "Policy update prepared",
    patchLines: ["crm_tool:", "  allowed_data: [email, account_notes]", "  redact: []"],
    tone: "amber"
  },
  {
    id: "allow_fields",
    title: "Allow selected fields",
    body: "Keep the destination, but send only approved fields.",
    outcome: "Only selected fields may leave the agent.",
    ciStatus: "CI gate: passes when unapproved fields are absent.",
    proofStatus: "Field allowlist prepared",
    patchLines: ["crm_tool:", "  allowed_data: [account_id]", "  redact: [email, account_notes]"],
    tone: "blue"
  },
  {
    id: "redact",
    title: "Redact fields",
    body: "Hash or remove sensitive fields before tool egress.",
    outcome: "Email and account notes are redacted before CRM egress.",
    ciStatus: "CI gate: passes when redaction markers are present.",
    proofStatus: "Redaction policy ready",
    patchLines: ["crm_tool:", "  allowed_data: []", "  redact: [email, account_notes]"],
    tone: "green"
  },
  {
    id: "require_approval",
    title: "Require human approval",
    body: "Pause risky egress until an approved reviewer allows it.",
    outcome: "Human approval is required before CRM update.",
    ciStatus: "CI gate: passes with approval control recorded.",
    proofStatus: "Approval control ready",
    patchLines: ["crm_tool:", "  require_approval: [email, account_notes]", "  allowed_data: []"],
    tone: "amber"
  },
  {
    id: "block",
    title: "Block tool",
    body: "Stop this tool from receiving the observed data.",
    outcome: "CRM tool is blocked for this data class.",
    ciStatus: "CI gate: passes because high-risk egress is blocked.",
    proofStatus: "Block rule ready",
    patchLines: ["crm_tool:", "  allowed_data: []", "  action: block"],
    tone: "red"
  }
];

const policyDecisionById = Object.fromEntries(
  policyDecisionOptions.map((option) => [option.id, option])
) as Record<PolicyDecisionId, PolicyDecisionOption>;

export function ConsoleWorkspace() {
  const [snapshot, setSnapshot] = React.useState<ConsoleSnapshot>(() => fixtureSnapshot());
  const [activeStep, setActiveStep] = React.useState<StepId>("overview");
  const [selectedAgentId, setSelectedAgentId] = React.useState("claims-triage");
  const [selectedScenarioId, setSelectedScenarioId] = React.useState("sensitive-crm-egress");
  const [sessionToken, setSessionToken] = React.useState("pending");
  const [bridgeUrl, setBridgeUrl] = React.useState("http://127.0.0.1:3847");
  const [bridgeBaseUrl, setBridgeBaseUrl] = React.useState<string | null>(null);
  const [revealEnabled, setRevealEnabled] = React.useState(false);
  const [revealConfirmed, setRevealConfirmed] = React.useState(false);
  const [exportState, setExportState] = React.useState("Not exported");
  const [showSettings, setShowSettings] = React.useState(false);
  const [liveRunStatus, setLiveRunStatus] = React.useState<LiveRunStatus>({
    state: "idle",
    message: "No live test has been run in this console session."
  });
  const [scenarioSuiteStatus, setScenarioSuiteStatus] = React.useState<ScenarioSuiteStatus>({
    state: "idle",
    message: "Run the scenario suite to compare all built-in tests for the selected agent."
  });
  const [evidencePackageStatus, setEvidencePackageStatus] = React.useState<EvidencePackageStatus>({
    state: "idle",
    message: "No evidence package has been generated in this console session."
  });
  const [policyChoices, setPolicyChoices] = React.useState<Record<string, PolicyDecisionId>>({});

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const queryToken = params.get("session");
    const queryBridge = params.get("bridge");
    const token = queryToken ? setEphemeralSessionToken(queryToken) : getEphemeralSessionToken();
    setSessionToken(token);

    const configuredUrl = queryBridge || window.localStorage.getItem("agent-capsule-console-bridge-url");
    const baseUrl = configuredUrl || null;
    setBridgeBaseUrl(baseUrl);
    if (configuredUrl) {
      setBridgeUrl(configuredUrl);
      window.localStorage.setItem("agent-capsule-console-bridge-url", configuredUrl);
    }

    const client = new LocalApiBridgeClient(baseUrl, token);
    client.loadSnapshot().then(setSnapshot);
    const endSession = () => {
      void client.endSession();
    };
    window.addEventListener("pagehide", endSession);
    return () => window.removeEventListener("pagehide", endSession);
  }, []);

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? agents[0];
  const selectedScenario =
    liveTestScenarios.find((scenario) => scenario.id === selectedScenarioId) ?? liveTestScenarios[0];
  const currentRun = resolveRun(selectedAgent, snapshot.runs, liveRunStatus);
  const currentStepIndex = steps.findIndex((step) => step.id === activeStep);
  const selectedPolicyDecision =
    policyDecisionById[policyChoices[selectedAgent.id] ?? defaultPolicyDecisionId(selectedAgent)];

  const updateBridgeUrl = React.useCallback((value: string) => {
    setBridgeUrl(value);
    setBridgeBaseUrl(value || null);
    window.localStorage.setItem("agent-capsule-console-bridge-url", value);
  }, []);

  const handleRunLiveAgent = React.useCallback(async () => {
    setLiveRunStatus({
      state: "running",
      message: `Running ${selectedAgent.name} through the local trace bridge.`,
      agentId: selectedAgent.id,
      scenarioId: selectedScenario.id,
      scenarioName: selectedScenario.title,
      expectedResult: selectedScenario.expectedResult
    });

    if (!bridgeBaseUrl) {
      setLiveRunStatus({
        state: "demo",
        message: "Demo mode prepared the same privacy workflow. Connect the local API bridge to capture a new encrypted trace.",
        agentId: selectedAgent.id,
        scenarioId: selectedScenario.id,
        scenarioName: selectedScenario.title,
        resultStatus: "needs_review",
        resultSummary: `${selectedAgent.findings} policy ${selectedAgent.findings === 1 ? "finding" : "findings"} across 1 destination.`,
        expectedResult: selectedScenario.expectedResult,
        encryptedPayloads: 4,
        safePayloadsOnly: true,
        runId: `run_live_${selectedAgent.id}_demo`,
        traceId: `trc_live_${selectedAgent.id}_demo`,
        spanCount: 4,
        findings: selectedAgent.findings
      });
      setActiveStep("flow");
      return;
    }

    try {
      const client = new LocalApiBridgeClient(bridgeBaseUrl, sessionToken);
      const result = await client.runLiveAgent(selectedAgent.id, selectedScenario.id);
      if (!result) {
        throw new Error("Live agent endpoint unavailable");
      }
      setSnapshot((previous) => snapshotWithLiveResult(previous, result));
      setLiveRunStatus({
        state: "ready",
        message: result.message,
        agentId: selectedAgent.id,
        scenarioId: result.test_scenario?.id ?? selectedScenario.id,
        scenarioName: result.test_scenario?.name ?? selectedScenario.title,
        resultStatus: result.test_result?.status,
        resultSummary: result.test_result?.summary,
        expectedResult: result.test_result?.expected_result ?? selectedScenario.expectedResult,
        encryptedPayloads: result.test_result?.encrypted_payloads ?? result.proof.encrypted_payloads,
        safePayloadsOnly: result.test_result?.safe_payloads_only ?? true,
        runId: result.run.run_id,
        traceId: result.run.trace_id,
        spanCount: result.run.span_count ?? result.safe_trace.spans.length,
        findings: result.proof.policy_findings
      });
      setExportState(`${result.run.run_id}-safe-trace.json ready`);
      setEvidencePackageStatus({
        state: "idle",
        message: "Live run captured. Generate an evidence package from the proof step."
      });
      setActiveStep("flow");
    } catch {
      setLiveRunStatus({
        state: "error",
        message: "The local bridge did not answer. Demo evidence is still loaded, and no private payload was requested.",
        agentId: selectedAgent.id,
        scenarioId: selectedScenario.id,
        scenarioName: selectedScenario.title,
        expectedResult: selectedScenario.expectedResult
      });
    }
  }, [bridgeBaseUrl, selectedAgent, selectedScenario, sessionToken]);

  const handleRunScenarioSuite = React.useCallback(async () => {
    setScenarioSuiteStatus({
      state: "running",
      message: `Running all privacy scenarios for ${selectedAgent.name}.`,
      agentId: selectedAgent.id
    });

    if (!bridgeBaseUrl) {
      const fixtureSuite = fixtureScenarioSuite(selectedAgent);
      setScenarioSuiteStatus({
        state: "demo",
        message: "Demo suite prepared from fixture metadata. Connect the local API bridge to create encrypted traces for every scenario.",
        suiteId: fixtureSuite.suite_id,
        agentId: fixtureSuite.agent_id,
        overallStatus: fixtureSuite.overall_status,
        scenarioCount: fixtureSuite.scenario_count,
        totalFindings: fixtureSuite.total_findings,
        safePayloadsOnly: fixtureSuite.safe_payloads_only,
        results: fixtureSuite.results,
        nextAction: fixtureSuite.next_action
      });
      return;
    }

    try {
      const client = new LocalApiBridgeClient(bridgeBaseUrl, sessionToken);
      const result = await client.runScenarioSuite(selectedAgent.id);
      if (!result) {
        throw new Error("Scenario suite endpoint unavailable");
      }
      setScenarioSuiteStatus({
        state: "ready",
        message: "Scenario suite captured as encrypted local traces.",
        suiteId: result.suite_id,
        agentId: result.agent_id,
        overallStatus: result.overall_status,
        scenarioCount: result.scenario_count,
        totalFindings: result.total_findings,
        safePayloadsOnly: result.safe_payloads_only,
        results: result.results,
        nextAction: result.next_action
      });
    } catch {
      setScenarioSuiteStatus({
        state: "error",
        message: "The local bridge could not run the scenario suite. No private payload was requested.",
        agentId: selectedAgent.id
      });
    }
  }, [bridgeBaseUrl, selectedAgent, sessionToken]);

  const handleOpenSuiteResult = React.useCallback(async (result: ScenarioSuiteResult) => {
    const scenario = liveTestScenarios.find((item) => item.id === result.scenario_id) ?? selectedScenario;
    const nextStatus: LiveRunStatus = {
      state: "ready",
      message: "Suite result opened from safe run metadata.",
      agentId: selectedAgent.id,
      scenarioId: scenario.id,
      scenarioName: result.scenario_name,
      resultStatus: result.status,
      resultSummary: result.summary,
      expectedResult: result.expected_result,
      encryptedPayloads: result.encrypted_payloads,
      safePayloadsOnly: result.safe_payloads_only,
      runId: result.run_id,
      traceId: result.trace_id,
      spanCount: 4,
      findings: result.finding_count
    };

    if (!bridgeBaseUrl || scenarioSuiteStatus.state === "demo") {
      setLiveRunStatus(nextStatus);
      setSnapshot((previous) => ({
        ...previous,
        runs: [
          {
            run_id: result.run_id,
            trace_id: result.trace_id,
            agent_name: selectedAgent.id,
            status: result.status,
            span_count: 4,
            created_at: new Date().toISOString()
          },
          ...previous.runs.filter((run) => run.run_id !== result.run_id)
        ],
        source: previous.source
      }));
      setEvidencePackageStatus({
        state: "idle",
        message: "Suite result opened. Generate an evidence package from the proof step."
      });
      setActiveStep("flow");
      return;
    }

    setLiveRunStatus({
      ...nextStatus,
      state: "running",
      message: "Opening suite result from local safe metadata."
    });

    try {
      const client = new LocalApiBridgeClient(bridgeBaseUrl, sessionToken);
      const opened = await client.loadRunEvidence(result.run_id);
      if (!opened) {
        throw new Error("Suite run evidence unavailable");
      }
      setSnapshot((previous) => ({
        ...previous,
        runs: [
          opened.run,
          ...previous.runs.filter((run) => run.run_id !== opened.run.run_id)
        ],
        safeTrace: opened.safe_trace,
        privacyMap: opened.privacy_map,
        replayComparison: opened.replay_comparison,
        source: "local-api"
      }));
      setLiveRunStatus({
        ...nextStatus,
        state: "ready",
        spanCount: opened.run.span_count || opened.safe_trace.spans.length,
        message: "Suite result opened from local safe metadata."
      });
      setExportState(`${result.run_id}-safe-trace.json ready`);
      setEvidencePackageStatus({
        state: "idle",
        message: "Suite result opened. Generate an evidence package from the proof step."
      });
      setActiveStep("flow");
    } catch {
      setLiveRunStatus({
        ...nextStatus,
        state: "error",
        message: "The local bridge could not open this suite result."
      });
    }
  }, [bridgeBaseUrl, scenarioSuiteStatus.state, selectedAgent.id, selectedScenario, sessionToken]);

  const handleCreateEvidencePackage = React.useCallback(async () => {
    const policyResponse = policyResponsePayload(selectedPolicyDecision);
    setEvidencePackageStatus({
      state: "building",
      message: "Building a safe evidence package from trace metadata, privacy map, and policy response."
    });

    if (!bridgeBaseUrl) {
      const fixturePackage = fixtureEvidencePackage(currentRun, selectedPolicyDecision, snapshot);
      setEvidencePackageStatus({
        state: "demo",
        message: "Demo package generated from fixture metadata. Connect the local API bridge for a stored evidence package.",
        packageId: fixturePackage.package_id,
        filename: fixturePackage.download_filename,
        relativePath: fixturePackage.artifact?.relative_path,
        sha256: fixturePackage.artifact?.sha256,
        sidecarPath: fixturePackage.artifact?.sidecar_relative_path,
        verificationStatus: fixturePackage.artifact?.verification_status,
        ciStatus: fixturePackage.ci_gate.summary,
        source: "fixture"
      });
      return;
    }

    try {
      const client = new LocalApiBridgeClient(bridgeBaseUrl, sessionToken);
      const result = await client.createEvidencePackage(currentRun.run_id, policyResponse);
      if (!result) {
        throw new Error("Evidence package endpoint unavailable");
      }
      setEvidencePackageStatus({
        state: "ready",
        message: "Evidence package generated without plaintext payloads.",
        packageId: result.package_id,
        filename: result.download_filename,
        relativePath: result.artifact?.relative_path,
        sha256: result.artifact?.sha256,
        sidecarPath: result.artifact?.sidecar_relative_path,
        verificationStatus: result.artifact?.verification_status,
        ciStatus: result.ci_gate.summary,
        source: "local-api"
      });
    } catch {
      setEvidencePackageStatus({
        state: "error",
        message: "The local bridge could not generate the package. No plaintext payload was requested."
      });
    }
  }, [bridgeBaseUrl, currentRun, selectedPolicyDecision, sessionToken, snapshot]);

  const handleVerifyEvidencePackage = React.useCallback(async () => {
    if (!evidencePackageStatus.packageId) {
      return;
    }
    if (!bridgeBaseUrl || evidencePackageStatus.source === "fixture") {
      setEvidencePackageStatus((current) => ({
        ...current,
        state: "demo",
        message: "Fixture verification is simulated. Connect the local API bridge to verify a saved artifact.",
        verificationStatus: current.verificationStatus ?? "demo"
      }));
      return;
    }

    setEvidencePackageStatus((current) => ({
      ...current,
      state: "verifying",
      message: "Recomputing the saved package hash and comparing it with the sidecar."
    }));

    try {
      const client = new LocalApiBridgeClient(bridgeBaseUrl, sessionToken);
      const result = await client.verifyEvidencePackage(evidencePackageStatus.packageId);
      if (!result) {
        throw new Error("Evidence verification endpoint unavailable");
      }
      setEvidencePackageStatus((current) => ({
        ...current,
        state: result.verification_status === "verified" ? "ready" : "error",
        message: result.verification_status === "verified"
          ? "Saved package hash matches the sidecar."
          : "Saved package hash does not match the sidecar.",
        sha256: result.sha256,
        sidecarPath: result.artifact.sidecar_relative_path,
        relativePath: result.artifact.relative_path,
        verificationStatus: result.verification_status
      }));
    } catch {
      setEvidencePackageStatus((current) => ({
        ...current,
        state: "error",
        message: "The local bridge could not verify the saved package."
      }));
    }
  }, [bridgeBaseUrl, evidencePackageStatus.packageId, evidencePackageStatus.source, sessionToken]);

  const handleCreateCustomerReport = React.useCallback(async () => {
    if (!evidencePackageStatus.packageId) {
      return;
    }

    if (!bridgeBaseUrl || evidencePackageStatus.source === "fixture") {
      const report = fixtureCustomerReport(
        currentRun,
        selectedPolicyDecision,
        snapshot,
        evidencePackageStatus.packageId
      );
      setEvidencePackageStatus((current) => ({
        ...current,
        state: "demo",
        message: "Demo customer report prepared from fixture metadata. Connect the local API bridge to build it from a saved package.",
        customerReportStatus: customerReportStatusLabel(report),
        customerReportHeadline: report.customer_summary.headline,
        customerReportDestinations: report.privacy_summary.destination_count,
        customerReportFindings: report.privacy_summary.finding_count,
        customerReportControls: report.controls.length,
        customerReport: report
      }));
      return;
    }

    setEvidencePackageStatus((current) => ({
      ...current,
      state: "verifying",
      message: "Building a customer verification report from the saved evidence package."
    }));

    try {
      const client = new LocalApiBridgeClient(bridgeBaseUrl, sessionToken);
      const result = await client.getCustomerVerificationReport(evidencePackageStatus.packageId);
      if (!result) {
        throw new Error("Customer report endpoint unavailable");
      }
      setEvidencePackageStatus((current) => ({
        ...current,
        state: result.customer_summary.status === "ready" ? "ready" : "error",
        message: "Customer verification report generated from saved evidence package.",
        customerReportStatus: customerReportStatusLabel(result),
        customerReportHeadline: result.customer_summary.headline,
        customerReportDestinations: result.privacy_summary.destination_count,
        customerReportFindings: result.privacy_summary.finding_count,
        customerReportControls: result.controls.length,
        customerReport: result,
        verificationStatus: result.verification.status,
        sha256: result.verification.sha256,
        sidecarPath: result.verification.sidecar
      }));
    } catch {
      setEvidencePackageStatus((current) => ({
        ...current,
        state: "error",
        message: "The local bridge could not build the customer report."
      }));
    }
  }, [
    bridgeBaseUrl,
    currentRun,
    evidencePackageStatus.packageId,
    evidencePackageStatus.source,
    selectedPolicyDecision,
    sessionToken,
    snapshot
  ]);

  return (
    <main className="demo-shell">
      <header className="demo-header">
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true">T</div>
          <div>
            <div className="eyebrow">Traceryx demo console</div>
            <h1>Private AI agent debugging, without private logs</h1>
          </div>
        </div>
        <div className="header-actions">
          <Badge tone={snapshot.source === "local-api" ? "green" : "blue"}>
            {snapshot.source === "local-api" ? "Local API connected" : "Demo data"}
          </Badge>
          <Button variant="outline" onClick={() => setShowSettings((value) => !value)}>
            <LockKeyhole className="h-4 w-4" aria-hidden="true" />
            Local settings
          </Button>
        </div>
      </header>

      {showSettings ? (
        <LocalSettings
          bridgeUrl={bridgeUrl}
          setBridgeUrl={updateBridgeUrl}
          sessionToken={sessionToken}
          setSessionToken={setSessionToken}
          revealEnabled={revealEnabled}
          setRevealEnabled={setRevealEnabled}
          revealConfirmed={revealConfirmed}
          setRevealConfirmed={setRevealConfirmed}
        />
      ) : null}

      <section className="demo-layout">
        <aside className="guide-panel" aria-label="Demo guide">
          <div className="guide-card">
            <div className="eyebrow">Use this order</div>
            <h2>Four-click demo</h2>
            <p>Each step has one job and one next action.</p>
          </div>
          <nav className="step-nav">
            {steps.map((step, index) => {
              const active = activeStep === step.id;
              const complete = index < currentStepIndex;
              return (
                <button
                  key={step.id}
                  className={["step-button", active ? "step-button-active" : "", complete ? "step-button-complete" : ""].join(" ")}
                  onClick={() => setActiveStep(step.id)}
                  type="button"
                >
                  <span className="step-number">{complete ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : index + 1}</span>
                  <span>
                    <span className="step-title">{step.plainTitle}</span>
                    <span className="step-helper">{step.helper}</span>
                  </span>
                </button>
              );
            })}
          </nav>
          <div className="talk-track">
            <div className="eyebrow">Say this</div>
            <p>{talkTrack(activeStep, selectedAgent)}</p>
          </div>
        </aside>

        <section className="stage-panel">
          {activeStep === "overview" ? (
            <OverviewStep
              setActiveStep={setActiveStep}
              snapshot={snapshot}
              selectedAgent={selectedAgent}
              setSelectedAgentId={setSelectedAgentId}
              selectedScenario={selectedScenario}
              setSelectedScenarioId={setSelectedScenarioId}
              liveRunStatus={liveRunStatus}
              scenarioSuiteStatus={scenarioSuiteStatus}
              onRunLiveAgent={handleRunLiveAgent}
              onRunScenarioSuite={handleRunScenarioSuite}
              onOpenSuiteResult={handleOpenSuiteResult}
            />
          ) : null}
          {activeStep === "agents" ? (
            <AgentStep
              selectedAgent={selectedAgent}
              setSelectedAgentId={setSelectedAgentId}
              setActiveStep={setActiveStep}
            />
          ) : null}
          {activeStep === "flow" ? (
            <FlowStep
              selectedAgent={selectedAgent}
              selectedScenario={selectedScenario}
              currentRun={currentRun}
              liveRunStatus={liveRunStatus}
              safeTrace={snapshot.safeTrace}
              privacyMap={snapshot.privacyMap}
              policyDecision={selectedPolicyDecision}
              setPolicyDecision={(decisionId) => {
                setPolicyChoices((current) => ({
                  ...current,
                  [selectedAgent.id]: decisionId
                }));
                setEvidencePackageStatus({
                  state: "idle",
                  message: "Policy response changed. Generate a fresh evidence package from the proof step."
                });
              }}
              setActiveStep={setActiveStep}
            />
          ) : null}
          {activeStep === "proof" ? (
            <ProofStep
              selectedAgent={selectedAgent}
              currentRun={currentRun}
              snapshot={snapshot}
              policyDecision={selectedPolicyDecision}
              scenarioSuiteStatus={scenarioSuiteStatus}
              evidencePackageStatus={evidencePackageStatus}
              onCreateEvidencePackage={handleCreateEvidencePackage}
              onVerifyEvidencePackage={handleVerifyEvidencePackage}
              onCreateCustomerReport={handleCreateCustomerReport}
              exportState={exportState}
              setExportState={setExportState}
              setActiveStep={setActiveStep}
            />
          ) : null}
        </section>
      </section>
    </main>
  );
}

function OverviewStep({
  setActiveStep,
  snapshot,
  selectedAgent,
  setSelectedAgentId,
  selectedScenario,
  setSelectedScenarioId,
  liveRunStatus,
  scenarioSuiteStatus,
  onRunLiveAgent,
  onRunScenarioSuite,
  onOpenSuiteResult
}: {
  setActiveStep: (step: StepId) => void;
  snapshot: ConsoleSnapshot;
  selectedAgent: AgentRecord;
  setSelectedAgentId: (id: string) => void;
  selectedScenario: LiveTestScenario;
  setSelectedScenarioId: (id: string) => void;
  liveRunStatus: LiveRunStatus;
  scenarioSuiteStatus: ScenarioSuiteStatus;
  onRunLiveAgent: () => void;
  onRunScenarioSuite: () => void;
  onOpenSuiteResult: (result: ScenarioSuiteResult) => void;
}) {
  const totals = {
    runs: agents.reduce((sum, agent) => sum + agent.runsToday, 0),
    findings: agents.reduce((sum, agent) => sum + agent.findings, 0),
    blocked: agents.filter((agent) => agent.status === "Blocked").length,
    traces: snapshot.safeTrace.spans.length
  };

  return (
    <div className="stage-content">
      <div className="hero-card">
        <Badge tone="blue">{company.environment}</Badge>
        <h2>{company.name}</h2>
        <p>{company.description}</p>
        <div className="run-id-strip">
          <span>{liveRunStatus.state === "ready" ? "Latest live run" : "Current demo run"}</span>
          <strong>{liveRunStatus.runId ?? snapshot.runs[0]?.run_id ?? "run_demo"}</strong>
          <span>{liveRunStatus.traceId ?? snapshot.runs[0]?.trace_id ?? "trace_demo"}</span>
        </div>
        <div className="summary-grid">
          <SummaryCard label="AI agents" value={String(agents.length)} detail="Across business teams" />
          <SummaryCard label="Runs today" value={formatNumber(totals.runs)} detail="Safe metadata captured" />
          <SummaryCard label="Open privacy items" value={String(totals.findings)} detail="Ready for review" />
          <SummaryCard label="Blocked agents" value={String(totals.blocked)} detail="Unsafe egress stopped" />
        </div>
      </div>

      <div className="plain-card live-test-card">
        <div className="card-icon"><PlayCircle className="h-5 w-5" aria-hidden="true" /></div>
        <div>
          <h3>Run a privacy test on {selectedAgent.name}</h3>
          <p>
            Capture a run, encrypt payloads locally, and review only the safe metadata:
            workflow structure, hashes, data classes, destinations, and policy decisions.
          </p>
          <div className="live-run-status">
            <Badge tone={liveRunTone(liveRunStatus.state)}>{liveRunLabel(liveRunStatus.state)}</Badge>
            <span>{liveRunStatus.message}</span>
          </div>
          <div className="scenario-picker" role="group" aria-label="Live test scenarios">
            {liveTestScenarios.map((scenario) => (
              <button
                key={scenario.id}
                className={["scenario-button", scenario.id === selectedScenario.id ? "scenario-button-active" : ""].join(" ")}
                onClick={() => setSelectedScenarioId(scenario.id)}
                type="button"
              >
                <span>{scenario.title}</span>
                <small>{scenario.expectedResult}</small>
              </button>
            ))}
          </div>
        </div>
      </div>

      <AgentTestMatrix
        selectedAgent={selectedAgent}
        selectedScenario={selectedScenario}
        setSelectedAgentId={setSelectedAgentId}
      />

      <ScenarioSuitePanel
        suiteStatus={scenarioSuiteStatus}
        onOpenResult={onOpenSuiteResult}
      />

      <div className="button-row button-row-between">
        <div className="button-row">
          <Button
            onClick={onRunLiveAgent}
            disabled={liveRunStatus.state === "running" || scenarioSuiteStatus.state === "running"}
          >
            <PlayCircle className="h-4 w-4" aria-hidden="true" />
            {liveRunStatus.state === "running" ? "Running test" : "Run live agent test"}
          </Button>
          <Button
            variant="outline"
            onClick={onRunScenarioSuite}
            disabled={liveRunStatus.state === "running" || scenarioSuiteStatus.state === "running"}
          >
            <PlayCircle className="h-4 w-4" aria-hidden="true" />
            {scenarioSuiteStatus.state === "running" ? "Running suite" : "Run scenario suite"}
          </Button>
        </div>
        <Button variant="outline" onClick={() => setActiveStep("agents")}>
          Start with an agent
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

function AgentTestMatrix({
  selectedAgent,
  selectedScenario,
  setSelectedAgentId
}: {
  selectedAgent: AgentRecord;
  selectedScenario: LiveTestScenario;
  setSelectedAgentId: (id: string) => void;
}) {
  const rankedAgents = [...agents].sort((left, right) => {
    const riskDelta = agentTestScore(right, selectedScenario) - agentTestScore(left, selectedScenario);
    if (riskDelta !== 0) {
      return riskDelta;
    }
    return right.runsToday - left.runsToday;
  });
  return (
    <section className="test-matrix-panel" aria-label="Company test matrix">
      <div className="test-matrix-header">
        <div>
          <div className="eyebrow">Company test matrix</div>
          <h3>{selectedScenario.title}</h3>
          <p>{selectedScenario.body}</p>
        </div>
        <Badge tone="blue">{selectedScenario.expectedResult}</Badge>
      </div>
      <div className="test-matrix-table">
        <div className="test-matrix-row test-matrix-head">
          <span>Agent</span>
          <span>Risk</span>
          <span>Expected outcome</span>
          <span>Finding load</span>
        </div>
        {rankedAgents.map((agent) => {
          const outcome = scenarioOutcome(agent, selectedScenario);
          const active = selectedAgent.id === agent.id;
          return (
            <button
              key={agent.id}
              className={["test-matrix-row", active ? "test-matrix-row-active" : ""].join(" ")}
              onClick={() => setSelectedAgentId(agent.id)}
              type="button"
            >
              <span>
                <strong>{agent.name}</strong>
                <small>{agent.owner} · {agent.language}</small>
              </span>
              <span><Badge tone={riskTone(agent.risk)}>{agent.risk}</Badge></span>
              <span>
                <strong>{outcome.label}</strong>
                <small>{outcome.detail}</small>
              </span>
              <span>
                <strong>{agent.findings ? `${agent.findings} open` : "Clear"}</strong>
                <small>{agent.destination}</small>
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function ScenarioSuitePanel({
  suiteStatus,
  onOpenResult
}: {
  suiteStatus: ScenarioSuiteStatus;
  onOpenResult: (result: ScenarioSuiteResult) => void;
}) {
  return (
    <section className="suite-panel" aria-label="Scenario suite results">
      <div className="suite-header">
        <div>
          <div className="eyebrow">Scenario suite</div>
          <h3>{suiteStatus.suiteId ?? "Not run yet"}</h3>
          <p>{suiteStatus.message}</p>
        </div>
        <Badge tone={suiteStatus.state === "ready" || suiteStatus.state === "demo" ? "green" : suiteStatus.state === "error" ? "amber" : "blue"}>
          {suiteStatus.overallStatus ?? suiteStatus.state}
        </Badge>
      </div>
      <div className="suite-summary">
        <ReportMetric label="Scenarios" value={formatCount(suiteStatus.scenarioCount, "scenario")} detail="Built-in privacy tests" />
        <ReportMetric label="Findings" value={formatCount(suiteStatus.totalFindings, "finding")} detail="Across suite runs" />
        <ReportMetric
          label="Browser payload view"
          value={suiteStatus.safePayloadsOnly ? "Safe metadata only" : "Pending"}
          detail="No plaintext payloads"
        />
      </div>
      {suiteStatus.results?.length ? (
        <div className="suite-results">
          {suiteStatus.results.map((result) => (
            <div key={result.scenario_id} className="suite-result-row">
              <div>
                <strong>{result.scenario_name}</strong>
                <small>{result.expected_result}</small>
              </div>
              <Badge tone={result.status === "passed" ? "green" : "amber"}>{result.status.replace("_", " ")}</Badge>
              <div>
                <strong>{formatCount(result.finding_count, "finding")}</strong>
                <small>{result.run_id}</small>
              </div>
              <div>
                <strong>{formatCount(result.encrypted_payloads, "payload")}</strong>
                <small>{result.safe_payloads_only ? "Safe metadata only" : "Review payload handling"}</small>
              </div>
              <Button variant="outline" onClick={() => onOpenResult(result)}>
                Open result
              </Button>
            </div>
          ))}
        </div>
      ) : null}
      {suiteStatus.nextAction ? <p className="suite-next-action">{suiteStatus.nextAction}</p> : null}
    </section>
  );
}

function AgentStep({
  selectedAgent,
  setSelectedAgentId,
  setActiveStep
}: {
  selectedAgent: AgentRecord;
  setSelectedAgentId: (id: string) => void;
  setActiveStep: (step: StepId) => void;
}) {
  return (
    <div className="stage-content">
      <StageHeader
        title="Choose one agent to inspect"
        body="For the demo, start with Claims Triage because it shows the main privacy review workflow."
      />
      <div className="agent-grid">
        {agents.map((agent) => (
          <button
            key={agent.id}
            className={["agent-card", selectedAgent.id === agent.id ? "agent-card-active" : ""].join(" ")}
            onClick={() => setSelectedAgentId(agent.id)}
            type="button"
          >
            <span className="agent-card-top">
              <span className="agent-name">{agent.name}</span>
              <StatusBadge status={agent.status} />
            </span>
            <span className="agent-work">{agent.work}</span>
            <span className="agent-meta">
              <Badge tone={riskTone(agent.risk)}>{agent.risk} risk</Badge>
              <Badge tone="neutral">{agent.language}</Badge>
            </span>
          </button>
        ))}
      </div>
      <SelectedAgentSummary selectedAgent={selectedAgent} />
      <div className="button-row button-row-between">
        <Button variant="outline" onClick={() => setActiveStep("overview")}>
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back
        </Button>
        <Button onClick={() => setActiveStep("flow")}>
          Review data flow
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

function FlowStep({
  selectedAgent,
  selectedScenario,
  currentRun,
  liveRunStatus,
  safeTrace,
  privacyMap,
  policyDecision,
  setPolicyDecision,
  setActiveStep
}: {
  selectedAgent: AgentRecord;
  selectedScenario: LiveTestScenario;
  currentRun: RunSummary;
  liveRunStatus: LiveRunStatus;
  safeTrace: SafeTrace;
  privacyMap: PrivacyMap;
  policyDecision: PolicyDecisionOption;
  setPolicyDecision: (decisionId: PolicyDecisionId) => void;
  setActiveStep: (step: StepId) => void;
}) {
  const scenarioName = liveRunStatus.scenarioName ?? selectedScenario.title;
  const resultStatus = liveRunStatus.resultStatus ?? (liveRunStatus.state === "ready" ? "needs_review" : "not_run");
  const resultSummary = liveRunStatus.resultSummary ?? "Run the selected scenario to capture a fresh privacy result.";
  const expectedResult = liveRunStatus.expectedResult ?? selectedScenario.expectedResult;
  const safePayloadsOnly = liveRunStatus.safePayloadsOnly ?? liveRunStatus.state !== "idle";
  return (
    <div className="stage-content">
      <StageHeader
        title="Review where data went"
        body="This screen uses safe metadata. It shows data classes and destinations, not private payload text."
      />
      <div className="live-result-strip">
        <div>
          <div className="eyebrow">Test result</div>
          <h3>{liveRunStatus.runId ?? currentRun.run_id}</h3>
        </div>
        <div>
          <span>Trace</span>
          <strong>{liveRunStatus.traceId ?? currentRun.trace_id}</strong>
        </div>
        <div>
          <span>Spans</span>
          <strong>{String(liveRunStatus.spanCount ?? currentRun.span_count)}</strong>
        </div>
        <div>
          <span>Findings</span>
          <strong>{String(liveRunStatus.findings ?? selectedAgent.findings)}</strong>
        </div>
      </div>
      <div className="scenario-result-panel">
        <div>
          <div className="eyebrow">Live test scenario</div>
          <h3>{scenarioName}</h3>
          <p>{resultSummary}</p>
        </div>
        <div className="scenario-result-facts">
          <span>Expected result</span>
          <strong>{expectedResult}</strong>
          <span>Outcome</span>
          <strong>{resultStatus.replace("_", " ")}</strong>
          <span>Encrypted payloads</span>
          <strong>{formatCount(liveRunStatus.encryptedPayloads, "payload")}</strong>
          <span>Browser payload view</span>
          <strong>{safePayloadsOnly ? "Safe metadata only" : "Not run"}</strong>
        </div>
      </div>
      <div className="flow-diagram" aria-label="Data flow diagram">
        <FlowNode tone="blue" label="Selected agent" title={selectedAgent.name} detail={currentRun.run_id} />
        <FlowArrow />
        <FlowNode tone="green" label="Safe trace store" title="Encrypted locally" detail="Payload text not shown" />
        <FlowArrow />
        <FlowNode tone={policyDecision.tone === "red" ? "red" : policyDecision.tone === "green" ? "green" : "amber"} label="Destination" title={selectedAgent.destination} detail={policyDecision.outcome} />
      </div>
      <LiveInspectionPanel safeTrace={safeTrace} privacyMap={privacyMap} />
      <div className="decision-panel">
        <div>
          <div className="eyebrow">Observed data classes</div>
          <div className="pill-row">
            {selectedAgent.dataClasses.map((dataClass) => (
              <Badge key={dataClass} tone="blue">{dataClass}</Badge>
            ))}
          </div>
        </div>
        <div>
          <div className="eyebrow">Policy action</div>
          <h3>{policyDecision.outcome}</h3>
          <p>
            Choose the control that should be stored with the policy and checked in CI.
          </p>
        </div>
      </div>
      <div className="policy-review-panel">
        <div>
          <div className="eyebrow">Choose response</div>
          <h3>Turn review into policy</h3>
          <p>These are the actions a developer or security reviewer can take before the pull request merges.</p>
        </div>
        <div className="policy-action-grid" role="group" aria-label="Policy response options">
          {policyDecisionOptions.map((option) => (
            <button
              key={option.id}
              type="button"
              className={["policy-action-button", policyDecision.id === option.id ? "policy-action-active" : ""].join(" ")}
              onClick={() => setPolicyDecision(option.id)}
            >
              <span>{option.title}</span>
              <small>{option.body}</small>
            </button>
          ))}
        </div>
      </div>
      <div className="policy-result-grid">
        <div className="policy-preview">
          <div className="eyebrow">Policy patch preview</div>
          <pre>{policyDecision.patchLines.join("\n")}</pre>
        </div>
        <div className="ci-gate-card">
          <Badge tone={policyDecision.tone}>{policyDecision.proofStatus}</Badge>
          <h3>{policyDecision.ciStatus}</h3>
          <p>Policy changes are version-controlled, and CI checks that undeclared high-risk egress is gone.</p>
        </div>
      </div>
      <div className="button-row button-row-between">
        <Button variant="outline" onClick={() => setActiveStep("agents")}>
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back
        </Button>
        <Button onClick={() => setActiveStep("proof")}>
          Share safe proof
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

function ProofStep({
  selectedAgent,
  currentRun,
  snapshot,
  policyDecision,
  scenarioSuiteStatus,
  evidencePackageStatus,
  onCreateEvidencePackage,
  onVerifyEvidencePackage,
  onCreateCustomerReport,
  exportState,
  setExportState,
  setActiveStep
}: {
  selectedAgent: AgentRecord;
  currentRun: RunSummary;
  snapshot: ConsoleSnapshot;
  policyDecision: PolicyDecisionOption;
  scenarioSuiteStatus: ScenarioSuiteStatus;
  evidencePackageStatus: EvidencePackageStatus;
  onCreateEvidencePackage: () => void;
  onVerifyEvidencePackage: () => void;
  onCreateCustomerReport: () => void;
  exportState: string;
  setExportState: (state: string) => void;
  setActiveStep: (step: StepId) => void;
}) {
  const releaseGate = buildReleaseGate(policyDecision, scenarioSuiteStatus, evidencePackageStatus);

  return (
    <div className="stage-content">
      <StageHeader
        title="Share proof without private data"
        body="This is the part teams can share with a teammate, security reviewer, or enterprise customer."
      />
      <div className="proof-grid">
        <ProofCard
          icon={Download}
          title="Safe trace"
          body="Workflow, timing, errors, token counts, payload sizes, hashes, redaction markers, and policy decisions."
          status={exportState}
          actionLabel="Prepare safe trace"
          onAction={() => setExportState(`${selectedAgent.id}-safe-trace.json ready`)}
        />
        <ProofCard
          icon={FileJson}
          title="Release evidence"
          body={`Signed manifest, policy version, runtime metadata, and policy response for ${selectedAgent.name}.`}
          status={policyDecision.proofStatus}
        />
        <ProofCard
          icon={ShieldCheck}
          title="Customer demo packet"
          body="Customer verification page, safe vendor telemetry, attestation result, policy decision, and sanitized support bundle."
          status={snapshot.manifest.signature.present ? "Signature present" : "Ready for enterprise POC"}
        />
      </div>
      <div className="evidence-summary">
        <div>
          <div className="eyebrow">Policy response</div>
          <h3>{policyDecision.title}</h3>
          <p>{policyDecision.outcome}</p>
        </div>
        <div>
          <div className="eyebrow">Merge gate</div>
          <h3>{policyDecision.ciStatus}</h3>
          <p>Evidence package includes run ID, trace ID, content hashes, redaction markers, policy decision, and safe trace metadata.</p>
        </div>
      </div>
      <section className="release-gate-panel" aria-label="Release gate">
        <div className="release-gate-header">
          <div>
            <div className="eyebrow">Release gate</div>
            <h3>{releaseGate.label}</h3>
            <p>{releaseGate.summary}</p>
          </div>
          <Badge tone={releaseGate.tone}>{releaseGate.status}</Badge>
        </div>
        <div className="release-gate-facts">
          <ReportMetric
            label="Policy action"
            value={policyDecision.title}
            detail={policyDecision.id === "allow" ? "Full destination allowed" : "Control recorded for CI"}
          />
          <ReportMetric
            label="Scenario suite"
            value={formatCount(scenarioSuiteStatus.scenarioCount, "scenario")}
            detail={`${formatCount(scenarioSuiteStatus.totalFindings, "finding")} reviewed`}
          />
          <ReportMetric
            label="Evidence"
            value={evidencePackageStatus.packageId ? "Generated" : "Pending"}
            detail={evidencePackageStatus.verificationStatus ?? "Hash not verified yet"}
          />
          <ReportMetric
            label="Customer proof"
            value={evidencePackageStatus.customerReport ? "Ready" : "Pending"}
            detail={evidencePackageStatus.customerReportStatus ?? "Report not built yet"}
          />
        </div>
        <div className="release-gate-checks">
          {releaseGate.checks.map((check) => (
            <div key={check.label} className="release-gate-check">
              <Badge tone={releaseGateCheckTone(check.status)}>{check.status}</Badge>
              <div>
                <strong>{check.label}</strong>
                <small>{check.detail}</small>
              </div>
            </div>
          ))}
        </div>
      </section>
      <div className="evidence-package-panel">
        <div>
          <div className="eyebrow">Evidence package</div>
          <h3>{evidencePackageStatus.packageId ?? "Not generated yet"}</h3>
          <p>{evidencePackageStatus.message}</p>
        </div>
        <div className="package-facts">
          <span>Filename</span>
          <strong>{evidencePackageStatus.filename ?? "Pending"}</strong>
          <span>Saved path</span>
          <strong>{evidencePackageStatus.relativePath ?? "Pending"}</strong>
          <span>Verification</span>
          <strong>{evidencePackageStatus.verificationStatus ?? "Pending"}</strong>
          <span>SHA-256</span>
          <strong>{evidencePackageStatus.sha256 ?? "Pending"}</strong>
          <span>Sidecar</span>
          <strong>{evidencePackageStatus.sidecarPath ?? "Pending"}</strong>
          <span>Source</span>
          <strong>{evidencePackageStatus.source === "local-api" ? "Local API bridge" : evidencePackageStatus.source === "fixture" ? "Fixture demo" : "Pending"}</strong>
          <span>CI summary</span>
          <strong>{evidencePackageStatus.ciStatus ?? policyDecision.ciStatus}</strong>
          <span>Customer report</span>
          <strong>{evidencePackageStatus.customerReportStatus ?? "Pending"}</strong>
          <span>Customer finding count</span>
          <strong>{formatCount(evidencePackageStatus.customerReportFindings, "finding")}</strong>
          <span>Customer controls</span>
          <strong>{formatCount(evidencePackageStatus.customerReportControls, "control")}</strong>
        </div>
        {evidencePackageStatus.customerReportHeadline ? (
          <div className="customer-report-summary">
            <span>Customer summary</span>
            <strong>{evidencePackageStatus.customerReportHeadline}</strong>
            <span>Destinations reviewed</span>
            <strong>{formatCount(evidencePackageStatus.customerReportDestinations, "destination")}</strong>
          </div>
        ) : null}
        <div className="package-actions">
          <Button
            onClick={onCreateEvidencePackage}
            disabled={evidencePackageStatus.state === "building" || evidencePackageStatus.state === "verifying"}
          >
            <FileJson className="h-4 w-4" aria-hidden="true" />
            {evidencePackageStatus.state === "building" ? "Generating package" : "Generate evidence package"}
          </Button>
          <Button
            variant="outline"
            onClick={onVerifyEvidencePackage}
            disabled={!evidencePackageStatus.packageId || evidencePackageStatus.state === "building" || evidencePackageStatus.state === "verifying"}
          >
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            {evidencePackageStatus.state === "verifying" ? "Verifying package" : "Verify saved package"}
          </Button>
          <Button
            variant="outline"
            onClick={onCreateCustomerReport}
            disabled={!evidencePackageStatus.packageId || evidencePackageStatus.state === "building" || evidencePackageStatus.state === "verifying"}
          >
            <FileJson className="h-4 w-4" aria-hidden="true" />
            Build customer report
          </Button>
        </div>
      </div>
      {evidencePackageStatus.customerReport ? (
        <CustomerReportPanel report={evidencePackageStatus.customerReport} />
      ) : null}
      <div className="plain-card">
        <div className="card-icon"><Eye className="h-5 w-5" aria-hidden="true" /></div>
        <div>
          <h3>What is not included</h3>
          <p>
            No plaintext prompts, documents, model outputs, tool payloads, secret values, or user identifiers.
            Current run: {currentRun.run_id}.
          </p>
        </div>
      </div>
      <div className="button-row button-row-between">
        <Button variant="outline" onClick={() => setActiveStep("flow")}>
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back
        </Button>
        <Button onClick={() => setActiveStep("overview")}>
          Restart demo
          <RefreshCcw className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

function CustomerReportPanel({ report }: { report: CustomerVerificationReport }) {
  return (
    <section className="customer-report-panel" aria-label="Customer verification report">
      <div className="customer-report-header">
        <div>
          <div className="eyebrow">Customer verification report</div>
          <h3>{report.customer_summary.headline}</h3>
          <p>
            {report.run.agent_name ?? "agent"} · {report.run.run_id ?? "run"} · {report.run.trace_id ?? "trace"}
          </p>
        </div>
        <Badge tone={report.customer_summary.status === "ready" ? "green" : "amber"}>
          {report.customer_summary.status}
        </Badge>
      </div>

      <div className="customer-report-metrics">
        <ReportMetric
          label="Readiness score"
          value={String(report.scorecard.score)}
          detail={report.scorecard.status.replace("_", " ")}
        />
        <ReportMetric label="Verification" value={report.verification.status} detail="Saved package hash" />
        <ReportMetric
          label="Plaintext payloads"
          value={report.privacy_summary.plaintext_payloads_included ? "Included" : "Excluded"}
          detail="Prompts, documents, outputs, tools"
        />
        <ReportMetric
          label="Destinations"
          value={formatNumber(report.privacy_summary.destination_count)}
          detail="Reviewed in privacy map"
        />
        <ReportMetric
          label="Findings"
          value={formatNumber(report.privacy_summary.finding_count)}
          detail="Policy review items"
        />
      </div>

      <div className="scorecard-panel" aria-label="Privacy readiness scorecard">
        <div>
          <div className="eyebrow">Privacy readiness</div>
          <h4>{report.scorecard.summary}</h4>
        </div>
        <div className="scorecard-checks">
          {report.scorecard.checks.map((check) => (
            <div key={check.id} className="scorecard-check">
              <Badge tone={scorecardTone(check.status)}>{check.status}</Badge>
              <div>
                <strong>{check.label}</strong>
                <small>{check.detail}</small>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="customer-report-grid">
        <div className="customer-report-section">
          <div className="eyebrow">Policy and CI</div>
          <h4>{report.policy_response.title}</h4>
          <p>{report.policy_response.outcome}</p>
          <div className="report-facts">
            <span>CI gate</span>
            <strong>{report.ci_gate.status}</strong>
            <span>Open high-risk egress</span>
            <strong>{formatNumber(report.ci_gate.open_high_risk_findings)}</strong>
            <span>Sidecar</span>
            <strong>{report.verification.sidecar}</strong>
          </div>
        </div>

        <div className="customer-report-section">
          <div className="eyebrow">Data excluded</div>
          <div className="control-list">
            {report.controls.map((control) => (
              <span key={control}>{control}</span>
            ))}
          </div>
        </div>
      </div>

      <div className="customer-destination-list">
        {report.destinations.map((destination) => (
          <div key={destination.id} className="customer-destination-row">
            <div>
              <strong>{destination.id}</strong>
              <span>{destination.domain ?? "internal"} · {destination.egress_risk} egress</span>
            </div>
            <Badge tone={destination.declared_in_policy ? "green" : "amber"}>
              {destination.declared_in_policy ? "Declared" : "Undeclared"}
            </Badge>
            <p>{destination.observed_data_classes.join(", ") || "No data classes observed"}</p>
            <small>{destination.findings.join(", ") || "No findings"}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

function ReportMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="report-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function LocalSettings({
  bridgeUrl,
  setBridgeUrl,
  sessionToken,
  setSessionToken,
  revealEnabled,
  setRevealEnabled,
  revealConfirmed,
  setRevealConfirmed
}: {
  bridgeUrl: string;
  setBridgeUrl: (value: string) => void;
  sessionToken: string;
  setSessionToken: (value: string) => void;
  revealEnabled: boolean;
  setRevealEnabled: (value: boolean) => void;
  revealConfirmed: boolean;
  setRevealConfirmed: (value: boolean) => void;
}) {
  return (
    <section className="settings-panel">
      <div>
        <div className="eyebrow">Advanced</div>
        <h2>Local settings</h2>
        <p>These controls are here for testing. The demo flow does not require changing them.</p>
      </div>
      <label className="field">
        <span>Bridge URL</span>
        <input
          value={bridgeUrl}
          onChange={(event) => {
            setBridgeUrl(event.target.value);
            window.localStorage.setItem("agent-capsule-console-bridge-url", event.target.value);
          }}
        />
      </label>
      <div className="settings-grid">
        <div className="key-value">
          <span>Session token</span>
          <strong>{maskToken(sessionToken)}</strong>
        </div>
        <Button variant="outline" onClick={() => setSessionToken(rotateEphemeralSessionToken())}>
          <RefreshCcw className="h-4 w-4" aria-hidden="true" />
          Rotate token
        </Button>
      </div>
      <div className="reveal-card">
        <div>
          <h3>Local payload reveal</h3>
          <p>{revealConfirmed ? "Confirmed locally" : "Disabled unless explicitly confirmed"}</p>
        </div>
        <Switch checked={revealEnabled} onCheckedChange={setRevealEnabled} aria-label="Toggle local payload reveal" />
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" disabled={!revealEnabled}>
              Confirm local reveal
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirm local payload reveal</DialogTitle>
              <DialogDescription>
                This confirmation is local to this console session. The default demo view still hides payload bodies.
              </DialogDescription>
            </DialogHeader>
            <div className="dialog-actions">
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <DialogClose asChild>
                <Button onClick={() => setRevealConfirmed(true)}>Confirm</Button>
              </DialogClose>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </section>
  );
}

function StageHeader({ title, body }: { title: string; body: string }) {
  return (
    <div className="stage-header">
      <div>
        <div className="eyebrow">Demo step</div>
        <h2>{title}</h2>
        <p>{body}</p>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function SelectedAgentSummary({ selectedAgent }: { selectedAgent: AgentRecord }) {
  return (
    <div className="selected-summary">
      <div>
        <div className="eyebrow">Selected agent</div>
        <h3>{selectedAgent.name}</h3>
        <p>{selectedAgent.work}</p>
      </div>
      <div className="summary-facts">
        <span>{selectedAgent.owner}</span>
        <span>{formatNumber(selectedAgent.runsToday)} runs today</span>
        <span>{selectedAgent.findings} open findings</span>
      </div>
    </div>
  );
}

function FlowNode({
  tone,
  label,
  title,
  detail
}: {
  tone: "blue" | "green" | "amber" | "red";
  label: string;
  title: string;
  detail: string;
}) {
  return (
    <div className={`flow-node flow-${tone}`}>
      <Badge tone={tone}>{label}</Badge>
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}

function FlowArrow() {
  return (
    <div className="flow-arrow" aria-hidden="true">
      <ArrowRight className="h-5 w-5" />
    </div>
  );
}

function LiveInspectionPanel({
  safeTrace,
  privacyMap
}: {
  safeTrace: SafeTrace;
  privacyMap: PrivacyMap;
}) {
  const visibleSpans = safeTrace.spans.slice(0, 5);
  const visibleDestinations = privacyMap.destinations.slice(0, 4);
  return (
    <div className="inspection-grid">
      <section className="inspection-panel" aria-label="Safe execution timeline">
        <div className="inspection-header">
          <div>
            <div className="eyebrow">Safe execution timeline</div>
            <h3>{safeTrace.diagnostic_summary.status}</h3>
          </div>
          <Badge tone="green">{safeTrace.redaction_profile}</Badge>
        </div>
        <div className="timeline-list">
          {visibleSpans.map((span) => (
            <div key={span.span_id} className="timeline-row">
              <div>
                <strong>{span.component_name}</strong>
                <span>{span.component_type} · {span.status}</span>
              </div>
              <div className="timeline-metrics">
                <span>{span.duration_ms} ms</span>
                <span>{formatBytes(span.payload_size_bytes)}</span>
                <span>{span.token_count ?? 0} tokens</span>
              </div>
              <div className="timeline-markers">
                <Badge tone={span.policy_decision === "allow" ? "green" : "amber"}>{span.policy_decision}</Badge>
                {span.redaction_markers.slice(0, 2).map((marker) => (
                  <Badge key={marker} tone="blue">{marker}</Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="inspection-panel" aria-label="Destination findings">
        <div className="inspection-header">
          <div>
            <div className="eyebrow">Destination findings</div>
            <h3>{privacyMap.findings.length} findings</h3>
          </div>
          <Badge tone={privacyMap.findings.length ? "amber" : "green"}>
            {privacyMap.findings.length ? "Review needed" : "No findings"}
          </Badge>
        </div>
        <div className="destination-list">
          {visibleDestinations.map((destination) => (
            <div key={destination.id} className="destination-row">
              <div>
                <strong>{destination.id}</strong>
                <span>{destination.domain ?? "internal"} · {destination.egress_risk} egress</span>
              </div>
              <div className="destination-badges">
                <Badge tone={destination.declared_in_policy ? "green" : "amber"}>
                  {destination.declared_in_policy ? "Declared" : "Undeclared"}
                </Badge>
                {destination.actions.slice(0, 2).map((action) => (
                  <Badge key={action} tone={action === "allow" ? "green" : "amber"}>{action}</Badge>
                ))}
              </div>
              <p>{destination.observed_data_classes.join(", ") || "No observed data classes"}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function buildReleaseGate(
  policyDecision: PolicyDecisionOption,
  scenarioSuiteStatus: ScenarioSuiteStatus,
  evidencePackageStatus: EvidencePackageStatus
): ReleaseGate {
  const scenarioSuiteReviewed = Boolean(
    scenarioSuiteStatus.results?.length && (scenarioSuiteStatus.state === "ready" || scenarioSuiteStatus.state === "demo")
  );
  const findingCount = scenarioSuiteStatus.totalFindings ?? 0;
  const evidenceGenerated = Boolean(evidencePackageStatus.packageId);
  const hashVerified =
    evidencePackageStatus.verificationStatus === "verified" ||
    evidencePackageStatus.verificationStatus === "demo";
  const customerReportReady = Boolean(evidencePackageStatus.customerReport);
  const unscopedAllow = policyDecision.id === "allow" && findingCount > 0;

  const checks: ReleaseGateCheck[] = [
    {
      label: "Scenario suite reviewed",
      status: scenarioSuiteReviewed ? "pass" : "review",
      detail: scenarioSuiteReviewed
        ? `${formatCount(scenarioSuiteStatus.scenarioCount, "scenario")} covered ${formatCount(findingCount, "finding")}.`
        : "Run the scenario suite so the ship decision is based on more than one trace."
    },
    {
      label: "Policy control selected",
      status: unscopedAllow ? "fail" : "pass",
      detail: unscopedAllow
        ? "High-risk findings cannot ship with a full allow action."
        : `${policyDecision.title} is recorded for the version-controlled policy patch.`
    },
    {
      label: "Evidence package generated",
      status: evidencePackageStatus.state === "error" ? "fail" : evidenceGenerated ? "pass" : "review",
      detail: evidenceGenerated
        ? `${evidencePackageStatus.packageId} contains safe trace metadata and policy response.`
        : "Generate the evidence package before sharing or merging."
    },
    {
      label: "Package hash verified",
      status: evidencePackageStatus.state === "error" ? "fail" : hashVerified ? "pass" : "review",
      detail: hashVerified
        ? `Verification status: ${evidencePackageStatus.verificationStatus}.`
        : "Verify the saved package hash against its sidecar."
    },
    {
      label: "Customer report ready",
      status: customerReportReady ? "pass" : "review",
      detail: customerReportReady
        ? evidencePackageStatus.customerReportHeadline ?? "Customer-safe report is ready."
        : "Build the report before sending proof to a security buyer."
    }
  ];

  if (checks.some((check) => check.status === "fail")) {
    return {
      status: "blocked",
      label: "Merge blocked",
      summary: "The run has unresolved high-risk egress or an unsafe policy action. Choose a narrower control before this can ship.",
      tone: "red",
      checks
    };
  }

  if (checks.every((check) => check.status === "pass")) {
    return {
      status: "ready",
      label: "Ready for controlled merge",
      summary: "Scenario coverage, policy control, verified evidence, and customer-safe proof are all in place.",
      tone: "green",
      checks
    };
  }

  return {
    status: "review",
    label: "Review before merge",
    summary: "The privacy decision is mostly assembled. Complete the remaining proof steps before using this in a customer or CI review.",
    tone: "amber",
    checks
  };
}

function releaseGateCheckTone(status: ReleaseGateCheckStatus): "green" | "amber" | "red" {
  if (status === "pass") {
    return "green";
  }
  if (status === "fail") {
    return "red";
  }
  return "amber";
}

function ProofCard({
  icon: Icon,
  title,
  body,
  status,
  actionLabel,
  onAction
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  body: string;
  status: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="proof-card">
      <div className="card-icon"><Icon className="h-5 w-5" aria-hidden="true" /></div>
      <h3>{title}</h3>
      <p>{body}</p>
      <Badge tone="green">{status}</Badge>
      {actionLabel && onAction ? (
        <Button className="mt-4 w-full" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}

function StatusBadge({ status }: { status: AgentStatus }) {
  if (status === "Ready") {
    return <Badge tone="green">Ready</Badge>;
  }
  if (status === "Blocked") {
    return <Badge tone="red">Blocked</Badge>;
  }
  return <Badge tone="amber">Needs review</Badge>;
}

function snapshotWithLiveResult(snapshot: ConsoleSnapshot, result: LiveAgentRunResult): ConsoleSnapshot {
  const liveRun: RunSummary = {
    run_id: result.run.run_id,
    trace_id: result.run.trace_id,
    agent_name: result.run.agent.name ?? "agent",
    status: result.safe_trace.diagnostic_summary.status,
    span_count: result.run.span_count ?? result.safe_trace.spans.length,
    created_at: result.run.created_at ?? result.safe_trace.created_at
  };
  return {
    ...snapshot,
    runs: [
      liveRun,
      ...snapshot.runs.filter((run) => run.run_id !== liveRun.run_id)
    ],
    safeTrace: result.safe_trace,
    privacyMap: result.privacy_map,
    source: "local-api"
  };
}

function policyResponsePayload(policyDecision: PolicyDecisionOption): Record<string, unknown> {
  return {
    action: policyDecision.id,
    title: policyDecision.title,
    outcome: policyDecision.outcome,
    ci_status: policyDecision.ciStatus,
    patch_preview: policyDecision.patchLines
  };
}

function fixtureEvidencePackage(
  run: RunSummary,
  policyDecision: PolicyDecisionOption,
  snapshot: ConsoleSnapshot
): EvidencePackageResult {
  const packageId = `evidence_${run.run_id}_demo`;
  return {
    ok: true,
    evidence_package_version: 1,
    package_id: packageId,
    created_at: new Date().toISOString(),
    download_filename: `${packageId}.json`,
    run: {
      run_id: run.run_id,
      trace_id: run.trace_id,
      agent: { name: run.agent_name }
    },
    selected_policy_response: {
      action: policyDecision.id,
      title: policyDecision.title,
      outcome: policyDecision.outcome,
      ci_status: policyDecision.ciStatus,
      patch_preview: policyDecision.patchLines
    },
    ci_gate: {
      status: policyDecision.id === "allow" ? "review_required" : "ready_for_merge",
      summary: policyDecision.ciStatus,
      open_high_risk_findings: snapshot.privacyMap.findings.length,
      requires_policy_commit: true,
      blocks_plaintext_payloads: true
    },
    redaction_attestation: {
      contains_plaintext_payloads: false,
      safe_trace_profile: snapshot.safeTrace.redaction_profile,
      redaction_markers: snapshot.safeTrace.redaction_markers,
      content_hash_count: snapshot.safeTrace.content_hashes.length
    },
    artifact: {
      saved: false,
      relative_path: `.agent-capsule/evidence/${packageId}.json`,
      sha256: "sha256:demo-fixture",
      sidecar_relative_path: `.agent-capsule/evidence/${packageId}.json.sha256`,
      verification_status: "demo"
    },
    contents: {
      safe_trace: snapshot.safeTrace,
      privacy_map: snapshot.privacyMap
    }
  };
}

function fixtureCustomerReport(
  run: RunSummary,
  policyDecision: PolicyDecisionOption,
  snapshot: ConsoleSnapshot,
  packageId = `evidence_${run.run_id}_demo`
): CustomerVerificationReport {
  const controls = [
    "Plaintext prompts excluded",
    "Plaintext documents excluded",
    "Model outputs excluded",
    "Tool payload bodies excluded",
    "Secrets excluded",
    "User identifiers excluded",
    "Content hashes retained",
    "Redaction markers retained"
  ];
  return {
    ok: true,
    report_version: 1,
    package_id: packageId,
    generated_at: new Date().toISOString(),
    title: "Customer verification report",
    verification: {
      status: "demo",
      sha256: "sha256:demo-fixture",
      sidecar: `.agent-capsule/evidence/${packageId}.json.sha256`
    },
    customer_summary: {
      headline: "This package can be reviewed without private payloads.",
      audience: "enterprise customer",
      status: "ready"
    },
    run: {
      run_id: run.run_id,
      trace_id: run.trace_id,
      agent_name: run.agent_name,
      mode: "observe",
      span_count: run.span_count
    },
    policy_response: {
      action: policyDecision.id,
      title: policyDecision.title,
      outcome: policyDecision.outcome,
      ci_status: policyDecision.ciStatus,
      patch_preview: policyDecision.patchLines
    },
    ci_gate: {
      status: policyDecision.id === "allow" ? "review_required" : "ready_for_merge",
      summary: policyDecision.ciStatus,
      open_high_risk_findings: snapshot.privacyMap.findings.filter((finding) => finding.severity === "error").length,
      requires_policy_commit: true,
      blocks_plaintext_payloads: true
    },
    scorecard: fixtureCustomerScorecard(policyDecision, snapshot),
    privacy_summary: {
      destination_count: snapshot.privacyMap.destinations.length,
      finding_count: snapshot.privacyMap.findings.length,
      redaction_marker_count: snapshot.safeTrace.redaction_markers.length,
      content_hash_count: snapshot.safeTrace.content_hashes.length,
      plaintext_payloads_included: false
    },
    controls,
    destinations: snapshot.privacyMap.destinations.map((destination) => ({
      id: destination.id,
      domain: destination.domain,
      egress_risk: destination.egress_risk,
      declared_in_policy: destination.declared_in_policy,
      observed_data_classes: destination.observed_data_classes,
      findings: destination.findings,
      actions: destination.actions
    }))
  };
}

function fixtureCustomerScorecard(policyDecision: PolicyDecisionOption, snapshot: ConsoleSnapshot): CustomerVerificationReport["scorecard"] {
  const reviewPolicy = policyDecision.id === "allow";
  const hasSafeEvidence = snapshot.safeTrace.content_hashes.length > 0 && snapshot.safeTrace.redaction_markers.length > 0;
  const reviewCount = (reviewPolicy ? 1 : 0) + (hasSafeEvidence ? 0 : 1);
  const score = Math.max(0, 100 - reviewCount * 10);
  return {
    score,
    status: score >= 90 ? "ready" : "needs_review",
    summary: score >= 90 ? "Ready for controlled customer review." : "Review remaining controls before customer sharing.",
    checks: [
      {
        id: "artifact_integrity",
        label: "Evidence package hash verified",
        status: "pass",
        detail: "demo"
      },
      {
        id: "plaintext_exclusion",
        label: "Plaintext payloads excluded",
        status: "pass",
        detail: "Prompts, documents, outputs, tool bodies, secrets, and user identifiers are excluded."
      },
      {
        id: "destination_control",
        label: "High-risk egress controlled",
        status: reviewPolicy ? "review" : "pass",
        detail: `${snapshot.privacyMap.findings.length} findings with policy action ${policyDecision.id}.`
      },
      {
        id: "ci_gate",
        label: "CI policy gate ready",
        status: policyDecision.id === "allow" ? "review" : "pass",
        detail: policyDecision.ciStatus
      },
      {
        id: "evidence_completeness",
        label: "Hashes and redaction markers retained",
        status: hasSafeEvidence ? "pass" : "review",
        detail: `${snapshot.safeTrace.content_hashes.length} content hashes and ${snapshot.safeTrace.redaction_markers.length} redaction markers.`
      }
    ]
  };
}

function fixtureScenarioSuite(agent: AgentRecord): ScenarioSuiteRunResult {
  const results: ScenarioSuiteResult[] = liveTestScenarios.map((scenario) => {
    const outcome = scenarioOutcome(agent, scenario);
    const findingCount = outcome.label === "Expected pass" ? 0 : Math.max(1, agent.findings);
    return {
      scenario_id: scenario.id,
      scenario_name: scenario.title,
      expected_result: scenario.expectedResult,
      data_classes: scenario.dataClasses,
      destination_id: agent.destination,
      status: findingCount ? "needs_review" : "passed",
      summary: `${findingCount} policy ${findingCount === 1 ? "finding" : "findings"} across 1 destination.`,
      run_id: `run_suite_${agent.id}_${scenario.id}_demo`,
      trace_id: `trc_suite_${agent.id}_${scenario.id}_demo`,
      finding_count: findingCount,
      encrypted_payloads: 4,
      safe_payloads_only: true
    };
  });
  const totalFindings = results.reduce((sum, result) => sum + result.finding_count, 0);
  return {
    ok: true,
    suite_id: `suite_${agent.id}_demo`,
    agent_id: agent.id,
    agent_name: agent.name,
    created_at: new Date().toISOString(),
    overall_status: totalFindings ? "needs_review" : "passed",
    scenario_count: results.length,
    total_findings: totalFindings,
    safe_payloads_only: true,
    results,
    next_action: "Open the highest-finding scenario, choose a policy control, and export customer evidence."
  };
}

function resolveRun(agent: AgentRecord, runs: RunSummary[], liveRunStatus: LiveRunStatus): RunSummary {
  if (liveRunStatus.agentId === agent.id && liveRunStatus.runId && liveRunStatus.traceId) {
    return {
      run_id: liveRunStatus.runId,
      trace_id: liveRunStatus.traceId,
      agent_name: agent.id,
      status: liveRunStatus.state === "error" ? "error" : agent.status === "Ready" ? "ok" : "needs_review",
      span_count: liveRunStatus.spanCount ?? 4,
      created_at: new Date().toISOString()
    };
  }
  if (agent.id === "claims-triage" && runs[0]) {
    return runs[0];
  }
  return {
    run_id: `run_${agent.id}_demo`,
    trace_id: `trc_${agent.id}_demo`,
    agent_name: agent.id,
    status: agent.status === "Ready" ? "ok" : agent.status.toLowerCase(),
    span_count: 4,
    created_at: "2026-06-23T20:30:00Z"
  };
}

function defaultPolicyDecisionId(agent: AgentRecord): PolicyDecisionId {
  const action = agent.policyAction.toLowerCase();
  if (agent.status === "Blocked" || action.includes("block")) {
    return "block";
  }
  if (action.includes("approval") || action.includes("approve")) {
    return "require_approval";
  }
  if (action.includes("selected") || action.includes("allow selected")) {
    return "allow_fields";
  }
  if (action.includes("redact")) {
    return "redact";
  }
  return "allow";
}

function agentTestScore(agent: AgentRecord, scenario: LiveTestScenario) {
  const risk = { Low: 1, Medium: 2, High: 3, Critical: 4 }[agent.risk];
  const overlap = agent.dataClasses.filter((dataClass) => scenario.dataClasses.includes(dataClass)).length;
  const statusWeight = agent.status === "Blocked" ? 4 : agent.status === "Needs review" ? 2 : 0;
  return risk * 10 + agent.findings * 4 + overlap * 6 + statusWeight;
}

function scenarioOutcome(agent: AgentRecord, scenario: LiveTestScenario) {
  const overlap = agent.dataClasses.some((dataClass) => scenario.dataClasses.includes(dataClass));
  if (agent.status === "Blocked") {
    return {
      label: "Block before release",
      detail: "Unsafe egress is already stopped."
    };
  }
  if (agent.findings > 0 || overlap || agent.risk === "Critical") {
    return {
      label: "Needs privacy review",
      detail: overlap ? "Scenario touches matching data classes." : "Open findings remain."
    };
  }
  return {
    label: "Expected pass",
    detail: "No open findings for this scenario."
  };
}

function liveRunLabel(state: LiveRunStatus["state"]) {
  if (state === "running") {
    return "Running";
  }
  if (state === "ready") {
    return "Captured";
  }
  if (state === "demo") {
    return "Demo mode";
  }
  if (state === "error") {
    return "Bridge offline";
  }
  return "Ready";
}

function liveRunTone(state: LiveRunStatus["state"]): "neutral" | "green" | "amber" | "red" | "blue" {
  if (state === "ready") {
    return "green";
  }
  if (state === "demo" || state === "running") {
    return "blue";
  }
  if (state === "error") {
    return "amber";
  }
  return "neutral";
}

function customerReportStatusLabel(report: CustomerVerificationReport) {
  if (report.customer_summary.status === "ready") {
    return `${report.verification.status} for ${report.customer_summary.audience}`;
  }
  return `${report.customer_summary.status}: ${report.verification.status}`;
}

function scorecardTone(status: string): "neutral" | "green" | "amber" | "red" | "blue" {
  if (status === "pass") {
    return "green";
  }
  if (status === "fail") {
    return "red";
  }
  if (status === "review") {
    return "amber";
  }
  return "blue";
}

function talkTrack(step: StepId, selectedAgent: AgentRecord) {
  if (step === "overview") {
    return "This is a company running AI agents on sensitive workflows. Traceryx shows privacy behavior without exposing private logs.";
  }
  if (step === "agents") {
    return `Pick ${selectedAgent.name}. The point is that every agent has a clear risk, owner, and privacy status.`;
  }
  if (step === "flow") {
    return "Here we show where data went, which data classes moved, and what policy decided. We do not show plaintext payloads.";
  }
  return "Now we export evidence: safe traces for debugging and release proof for enterprise customers.";
}

function riskTone(risk: AgentRisk): "neutral" | "green" | "amber" | "red" | "blue" {
  if (risk === "Critical" || risk === "High") {
    return "red";
  }
  if (risk === "Medium") {
    return "amber";
  }
  return "green";
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatCount(value: number | undefined, singular: string) {
  if (value === undefined) {
    return "Pending";
  }
  return `${formatNumber(value)} ${value === 1 ? singular : `${singular}s`}`;
}

function formatBytes(value: number) {
  if (value >= 1024) {
    return `${Math.round(value / 1024)} KB`;
  }
  return `${value} B`;
}

function maskToken(token: string) {
  if (token.length < 16) {
    return token;
  }
  return `${token.slice(0, 8)}...${token.slice(-6)}`;
}
