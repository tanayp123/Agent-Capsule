import { expect, test } from "@playwright/test";
import manifest from "../fixtures/manifest-inspect.json";
import privacyMap from "../fixtures/privacy-map.json";
import replayComparison from "../fixtures/replay-comparison.json";
import safeTrace from "../fixtures/safe-trace-import.json";

const rawValues = [
  "claimant@example.com",
  "person@example.com",
  "Neck pain reported after accident",
  "Rear-end collision at low speed",
  "Claim requires review because medical context is present",
  "sig_test_value"
];

const primarySteps = [
  "Start here",
  "Pick an agent",
  "See where data went",
  "Export safe evidence"
];

async function expectNoRawValues(page: import("@playwright/test").Page) {
  const bodyText = await page.locator("body").innerText();
  for (const rawValue of rawValues) {
    expect(bodyText).not.toContain(rawValue);
  }
}

test("first render is a guided demo with four clear steps", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Private AI agent debugging, without private logs" })).toBeVisible();
  await expect(page.getByText("Fixture workspace", { exact: true })).toBeVisible();
  await expect(page.getByText("Northstar Claims Group", { exact: true })).toBeVisible();
  await expect(page.getByText("Ops workflow", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Workspace release verdict")).toBeVisible();
  await expect(page.getByLabel("Workspace release verdict").getByText("Review before merge", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Workspace release verdict").getByRole("button", { name: "Run suite now" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Investigate highest-risk agent" })).toBeVisible();
  await expect(page.getByRole("group", { name: "Live test scenarios" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Sensitive CRM egress/ })).toBeVisible();
  await expect(page.getByLabel("Company test matrix")).toBeVisible();
  await expect(page.getByLabel("Scenario suite results")).toBeVisible();
  await expect(page.getByRole("button", { name: "Run scenario suite" })).toBeVisible();
  await expect(page.getByText("Benefits Eligibility", { exact: true })).toBeVisible();
  await expect(page.getByText("Block before release", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Contract Review/ }).click();
  await expect(page.getByRole("heading", { name: "Run a privacy test on Contract Review" })).toBeVisible();

  for (const step of primarySteps) {
    await expect(page.getByRole("button", { name: step })).toBeVisible();
  }
  await expect(page.getByRole("button", { name: "Run live agent test" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start with an agent" })).toBeVisible();
  await expectNoRawValues(page);
});

test("guided workflow moves through agent, data sharing, and evidence steps", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Start with an agent" }).click();
  await expect(page.getByRole("heading", { name: "Choose one agent to inspect" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Claims Triage Needs review" })).toBeVisible();

  await page.getByRole("button", { name: "Review data flow" }).click();
  await expect(page.getByRole("heading", { name: "Review where data went" })).toBeVisible();
  await expect(page.getByLabel("Data flow diagram")).toBeVisible();
  await expect(page.getByLabel("Safe execution timeline")).toBeVisible();
  await expect(page.getByLabel("Destination findings")).toBeVisible();
  await expect(page.getByText("classify-claim", { exact: true })).toBeVisible();
  await expect(page.getByText("api.crm.example", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Email and account notes are redacted before CRM egress." })).toBeVisible();
  await expect(page.getByRole("group", { name: "Policy response options" })).toBeVisible();
  await page.getByRole("button", { name: /^Require human approval/ }).click();
  await expect(page.getByRole("heading", { name: "Human approval is required before CRM update." })).toBeVisible();
  await expect(page.getByText("CI gate: passes with approval control recorded.", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Share safe proof" }).click();
  await expect(page.getByRole("heading", { name: "Share proof without private data" })).toBeVisible();
  await expect(page.getByText("Safe trace", { exact: true })).toBeVisible();
  await expect(page.getByText("Release evidence", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Require human approval" })).toBeVisible();
  await expect(page.getByText("Approval control ready", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Prepare safe trace" }).click();
  await expect(page.getByText("claims-triage-safe-trace.json ready", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Generate evidence package" }).click();
  const evidencePackage = page.locator(".evidence-package-panel");
  await expect(evidencePackage.getByText("evidence_run_failed_model_001_demo.json", { exact: true })).toBeVisible();
  await expect(evidencePackage.getByText(".agent-capsule/evidence/evidence_run_failed_model_001_demo.json", { exact: true })).toBeVisible();
  await expect(evidencePackage.getByText("demo", { exact: true })).toBeVisible();
  await expectNoRawValues(page);
});

test("primary labels stay plain and old dense navigation is removed", async ({ page }) => {
  await page.goto("/");
  const bodyText = await page.locator("body").innerText();
  expect(bodyText).toContain("See where data went");
  expect(bodyText).toContain("Export safe evidence");
  expect(bodyText).not.toContain("Run timeline");
  expect(bodyText).not.toContain("Privacy map");
  expect(bodyText).not.toContain("Release evidence");
});

test("highest-risk CTA opens the data-flow review", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Investigate highest-risk agent" }).click();
  await expect(page.getByRole("heading", { name: "Review where data went" })).toBeVisible();
  await expect(page.getByLabel("Workspace release verdict")).toContainText("Benefits Eligibility");
  await expect(page.getByRole("heading", { name: "Benefits Eligibility", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "CRM tool is blocked for this data class." })).toBeVisible();
  await expectNoRawValues(page);
});

test("local API bridge response renders through session token", async ({ page }) => {
  const bridgeUrl = "http://127.0.0.1:39291";
  await page.route(`${bridgeUrl}/**`, async (route) => {
    expect(route.request().headers().authorization).toBe("Bearer test-token");
    const url = new URL(route.request().url());
    const runId = "run_failed_model_001";
    const responses: Record<string, unknown> = {
      "/runs": {
        ok: true,
        runs: [{
          run_id: runId,
          trace_id: "trc_failed_model_001",
          agent_name: "claims-triage",
          status: "error",
          span_count: 2,
          created_at: "2026-06-23T00:00:00Z"
        }]
      },
      [`/runs/${runId}/timeline`]: safeTrace,
      [`/runs/${runId}/privacy-map`]: privacyMap,
      [`/runs/${runId}/replay`]: replayComparison,
      "/manifests/claims-triage": manifest,
      "/session/end": { ok: true }
    };
    const response = responses[url.pathname] ?? { ok: false };
    await route.fulfill({
      status: response === responses[url.pathname] ? 200 : 404,
      contentType: "application/json",
      body: JSON.stringify(response)
    });
  });

  await page.goto(`/?bridge=${encodeURIComponent(bridgeUrl)}&session=test-token`);
  await expect(page.getByText("Local API connected", { exact: true })).toBeVisible();
  await expect(page.locator(".run-id-strip").getByText("run_failed_model_001", { exact: true })).toBeVisible();
  await expectNoRawValues(page);
});

test("live agent test calls bridge and renders safe evidence", async ({ page }) => {
  const bridgeUrl = "http://127.0.0.1:39292";
  const liveRunId = "run_live_claims_triage_001";
  const liveTraceId = "trc_live_claims_triage_001";
  let liveRunCalled = false;
  let suiteCalled = false;
  let evidencePackageCalled = false;
  let verificationCalled = false;
  let customerReportCalled = false;

  await page.route(`${bridgeUrl}/**`, async (route) => {
    expect(route.request().headers().authorization).toBe("Bearer live-token");
    const url = new URL(route.request().url());
    const runId = "run_failed_model_001";
    const liveSafeTrace = {
      ...safeTrace,
      source_trace_id: liveTraceId,
      diagnostic_summary: {
        ...safeTrace.diagnostic_summary,
        status: "prepared"
      }
    };
    const livePrivacyMap = {
      ...privacyMap,
      run_id: liveRunId,
      trace_id: liveTraceId
    };
    const suiteApprovalRun = {
      run_id: "run_suite_approval_001",
      trace_id: "trc_suite_approval_001",
      agent: { name: "claims-triage", version: "demo.1" },
      mode: "observe",
      created_at: "2026-06-23T00:01:40Z",
      span_count: 4
    };
    const suiteApprovalTrace = {
      ...safeTrace,
      source_trace_id: "trc_suite_approval_001",
      diagnostic_summary: {
        ...safeTrace.diagnostic_summary,
        status: "prepared"
      }
    };
    const suiteApprovalPrivacyMap = {
      ...privacyMap,
      run_id: "run_suite_approval_001",
      trace_id: "trc_suite_approval_001"
    };
    const responses: Record<string, unknown> = {
      "/runs": {
        ok: true,
        runs: [{
          run_id: runId,
          trace_id: "trc_failed_model_001",
          agent_name: "claims-triage",
          status: "error",
          span_count: 2,
          created_at: "2026-06-23T00:00:00Z"
        }]
      },
      [`/runs/${runId}/timeline`]: safeTrace,
      [`/runs/${runId}/privacy-map`]: privacyMap,
      [`/runs/${runId}/replay`]: replayComparison,
      "/runs/run_suite_approval_001": suiteApprovalRun,
      "/runs/run_suite_approval_001/timeline": suiteApprovalTrace,
      "/runs/run_suite_approval_001/privacy-map": suiteApprovalPrivacyMap,
      "/runs/run_suite_approval_001/replay": replayComparison,
      "/manifests/claims-triage": manifest,
      "/session/end": { ok: true },
      "/live-agents/claims-triage/run": {
        ok: true,
        message: "Live agent test captured as an encrypted trace.",
        run: {
          run_id: liveRunId,
          trace_id: liveTraceId,
          agent: { name: "claims-triage", version: "demo.1" },
          mode: "observe",
          created_at: "2026-06-23T00:01:00Z",
          span_count: 4,
          destinations: []
        },
        safe_trace: liveSafeTrace,
        privacy_map: livePrivacyMap,
        test_scenario: {
          id: "sensitive-crm-egress",
          name: "Sensitive CRM egress",
          description: "Agent updates an external CRM with customer contact and account notes.",
          expected_result: "High-risk destination review",
          data_classes: ["email", "account_notes"],
          destination_id: "crm_tool"
        },
        test_result: {
          status: "needs_review",
          summary: "2 policy findings across 1 destination.",
          expected_result: "High-risk destination review",
          safe_payloads_only: true,
          encrypted_payloads: 4
        },
        proof: {
          safe_trace_ready: true,
          encrypted_payloads: 4,
          redaction_markers: ["hashed:email"],
          policy_findings: 2
        },
        next_actions: ["Review destinations and data classes."]
      },
      "/live-agents/claims-triage/scenario-suite": {
        ok: true,
        suite_id: "suite_claims_triage_001",
        agent_id: "claims-triage",
        agent_name: "claims-triage",
        created_at: "2026-06-23T00:01:30Z",
        overall_status: "needs_review",
        scenario_count: 3,
        total_findings: 6,
        safe_payloads_only: true,
        next_action: "Open the highest-finding scenario, choose a policy control, and export customer evidence.",
        results: [
          {
            scenario_id: "sensitive-crm-egress",
            scenario_name: "Sensitive CRM egress",
            expected_result: "High-risk destination review",
            data_classes: ["email", "account_notes"],
            destination_id: "crm_tool",
            status: "needs_review",
            summary: "2 policy findings across 1 destination.",
            run_id: "run_suite_sensitive_crm_001",
            trace_id: "trc_suite_sensitive_crm_001",
            finding_count: 2,
            encrypted_payloads: 4,
            safe_payloads_only: true
          },
          {
            scenario_id: "metadata-only-check",
            scenario_name: "Metadata-only update",
            expected_result: "Destination declaration review",
            data_classes: ["operational_metadata"],
            destination_id: "crm_tool",
            status: "needs_review",
            summary: "1 policy finding across 1 destination.",
            run_id: "run_suite_metadata_001",
            trace_id: "trc_suite_metadata_001",
            finding_count: 1,
            encrypted_payloads: 4,
            safe_payloads_only: true
          },
          {
            scenario_id: "approval-required",
            scenario_name: "Approval-required note",
            expected_result: "Human approval control",
            data_classes: ["email", "account_notes", "medical_context"],
            destination_id: "crm_tool",
            status: "needs_review",
            summary: "3 policy findings across 1 destination.",
            run_id: "run_suite_approval_001",
            trace_id: "trc_suite_approval_001",
            finding_count: 3,
            encrypted_payloads: 4,
            safe_payloads_only: true
          }
        ]
      },
      [`/runs/${liveRunId}/evidence-package`]: {
        ok: true,
        evidence_package_version: 1,
        package_id: "evidence_run_live_claims_triage_001",
        created_at: "2026-06-23T00:02:00Z",
        download_filename: "evidence_run_live_claims_triage_001.json",
        run: {
          run_id: liveRunId,
          trace_id: liveTraceId,
          agent: { name: "claims-triage", version: "demo.1" }
        },
        selected_policy_response: {
          action: "redact",
          title: "Redact fields",
          outcome: "Email and account notes are redacted before CRM egress.",
          ci_status: "CI gate: passes when redaction markers are present.",
          patch_preview: ["crm_tool:", "  redact: [email, account_notes]"]
        },
        ci_gate: {
          status: "ready_for_merge",
          summary: "CI gate: passes when redaction markers are present.",
          open_high_risk_findings: 2,
          requires_policy_commit: true,
          blocks_plaintext_payloads: true
        },
        redaction_attestation: {
          contains_plaintext_payloads: false,
          safe_trace_profile: "team_debug",
          redaction_markers: ["hashed:email"],
          content_hash_count: 4
        },
        artifact: {
          saved: true,
          path: "/tmp/.agent-capsule/evidence/evidence_run_live_claims_triage_001.json",
          relative_path: ".agent-capsule/evidence/evidence_run_live_claims_triage_001.json",
          sha256: "sha256:111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000",
          sidecar_relative_path: ".agent-capsule/evidence/evidence_run_live_claims_triage_001.json.sha256",
          verification_status: "verified"
        },
        contents: {
          safe_trace: liveSafeTrace,
          privacy_map: livePrivacyMap
        }
      },
      "/evidence-packages/evidence_run_live_claims_triage_001/verify": {
        ok: true,
        package_id: "evidence_run_live_claims_triage_001",
        checked_at: "2026-06-23T00:03:00Z",
        verification_status: "verified",
        sha256: "sha256:111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000",
        expected_sha256: "sha256:111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000",
        artifact: {
          path: "/tmp/.agent-capsule/evidence/evidence_run_live_claims_triage_001.json",
          relative_path: ".agent-capsule/evidence/evidence_run_live_claims_triage_001.json",
          sidecar_path: "/tmp/.agent-capsule/evidence/evidence_run_live_claims_triage_001.json.sha256",
          sidecar_relative_path: ".agent-capsule/evidence/evidence_run_live_claims_triage_001.json.sha256"
        }
      },
      "/evidence-packages/evidence_run_live_claims_triage_001/customer-report": {
        ok: true,
        report_version: 1,
        package_id: "evidence_run_live_claims_triage_001",
        generated_at: "2026-06-23T00:04:00Z",
        title: "Customer verification report",
        verification: {
          status: "verified",
          sha256: "sha256:111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000",
          sidecar: ".agent-capsule/evidence/evidence_run_live_claims_triage_001.json.sha256"
        },
        customer_summary: {
          headline: "This package can be reviewed without private payloads.",
          audience: "enterprise customer",
          status: "ready"
        },
        run: {
          run_id: liveRunId,
          trace_id: liveTraceId,
          agent_name: "claims-triage",
          agent_version: "demo.1",
          mode: "observe",
          span_count: 4
        },
        policy_response: {
          action: "redact",
          title: "Redact fields",
          outcome: "Email and account notes are redacted before CRM egress.",
          ci_status: "CI gate: passes when redaction markers are present.",
          patch_preview: ["crm_tool:", "  redact: [email, account_notes]"]
        },
        ci_gate: {
          status: "ready_for_merge",
          summary: "CI gate: passes when redaction markers are present.",
          open_high_risk_findings: 2,
          requires_policy_commit: true,
          blocks_plaintext_payloads: true
        },
        scorecard: {
          score: 100,
          status: "ready",
          summary: "Ready for controlled customer review.",
          checks: [
            {
              id: "artifact_integrity",
              label: "Evidence package hash verified",
              status: "pass",
              detail: "verified"
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
              status: "pass",
              detail: "2 high-risk findings with policy action redact."
            },
            {
              id: "ci_gate",
              label: "CI policy gate ready",
              status: "pass",
              detail: "CI gate: passes when redaction markers are present."
            },
            {
              id: "evidence_completeness",
              label: "Hashes and redaction markers retained",
              status: "pass",
              detail: "4 content hashes and 1 redaction markers."
            }
          ]
        },
        privacy_summary: {
          destination_count: 1,
          finding_count: 2,
          redaction_marker_count: 1,
          content_hash_count: 4,
          plaintext_payloads_included: false
        },
        controls: [
          "Plaintext prompts excluded",
          "Plaintext documents excluded",
          "Model outputs excluded",
          "Tool payload bodies excluded",
          "Secrets excluded",
          "User identifiers excluded",
          "Content hashes retained",
          "Redaction markers retained"
        ],
        destinations: [{
          id: "crm_tool",
          domain: "crm.example.com",
          egress_risk: "high",
          declared_in_policy: false,
          observed_data_classes: ["account_notes", "email"],
          findings: ["undeclared_destination", "undeclared_high_risk_egress"],
          actions: ["warn"]
        }]
      }
    };
    if (url.pathname === "/live-agents/claims-triage/run") {
      liveRunCalled = true;
      expect(route.request().method()).toBe("POST");
      const body = route.request().postDataJSON();
      expect(body.scenario_id).toBe("sensitive-crm-egress");
    }
    if (url.pathname === "/live-agents/claims-triage/scenario-suite") {
      suiteCalled = true;
      expect(route.request().method()).toBe("POST");
    }
    if (url.pathname === `/runs/${liveRunId}/evidence-package`) {
      evidencePackageCalled = true;
      expect(route.request().method()).toBe("POST");
      const body = route.request().postDataJSON();
      expect(body.policy_response.action).toBe("redact");
    }
    if (url.pathname === "/evidence-packages/evidence_run_live_claims_triage_001/verify") {
      verificationCalled = true;
      expect(route.request().method()).toBe("GET");
    }
    if (url.pathname === "/evidence-packages/evidence_run_live_claims_triage_001/customer-report") {
      customerReportCalled = true;
      expect(route.request().method()).toBe("GET");
    }
    const response = responses[url.pathname] ?? { ok: false };
    await route.fulfill({
      status: response === responses[url.pathname] ? 200 : 404,
      contentType: "application/json",
      body: JSON.stringify(response)
    });
  });

  await page.goto(`/?bridge=${encodeURIComponent(bridgeUrl)}&session=live-token`);
  await page.getByRole("button", { name: "Run scenario suite" }).click();
  const suitePanel = page.getByLabel("Scenario suite results");
  await expect(page.getByText("suite_claims_triage_001", { exact: true })).toBeVisible();
  await expect(suitePanel.getByText("3 scenarios", { exact: true })).toBeVisible();
  await expect(suitePanel.getByText("6 findings", { exact: true })).toBeVisible();
  await expect(suitePanel.getByText("Metadata-only update", { exact: true })).toBeVisible();
  await expect(suitePanel.getByText("run_suite_approval_001", { exact: true })).toBeVisible();
  expect(suiteCalled).toBe(true);
  await suitePanel
    .locator(".suite-result-row")
    .filter({ hasText: "Approval-required note" })
    .getByRole("button", { name: "Open result" })
    .click();
  await expect(page.getByRole("heading", { name: "Review where data went" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "run_suite_approval_001" })).toBeVisible();
  await expect(page.locator(".live-result-strip").getByText("trc_suite_approval_001", { exact: true })).toBeVisible();
  await expect(page.getByText("Approval-required note", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Start here" }).click();
  await page.getByRole("button", { name: "Run live agent test" }).click();
  await expect(page.getByRole("heading", { name: "Review where data went" })).toBeVisible();
  expect(liveRunCalled).toBe(true);
  await expect(page.getByRole("heading", { name: liveRunId })).toBeVisible();
  await expect(page.locator(".live-result-strip").getByText(liveTraceId, { exact: true })).toBeVisible();
  await expect(page.locator(".live-result-strip").getByText("2", { exact: true })).toBeVisible();
  await expect(page.getByText("Sensitive CRM egress", { exact: true })).toBeVisible();
  await expect(page.getByText("2 policy findings across 1 destination.", { exact: true })).toBeVisible();
  await expect(page.getByText("High-risk destination review", { exact: true })).toBeVisible();
  await expect(page.getByText("needs review", { exact: true })).toBeVisible();
  await expect(page.getByText("Safe metadata only", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Safe execution timeline")).toBeVisible();
  await expect(page.getByLabel("Destination findings")).toBeVisible();
  await page.getByRole("button", { name: "Share safe proof" }).click();
  const releaseGate = page.getByLabel("Release gate");
  await expect(releaseGate.getByRole("heading", { name: "Review before merge" })).toBeVisible();
  await expect(releaseGate.getByText("Scenario suite reviewed", { exact: true })).toBeVisible();
  await expect(releaseGate.getByText("Customer report ready", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Generate evidence package" }).click();
  const evidencePackage = page.locator(".evidence-package-panel");
  await expect(evidencePackage.getByText("evidence_run_live_claims_triage_001.json", { exact: true })).toBeVisible();
  await expect(evidencePackage.getByText(".agent-capsule/evidence/evidence_run_live_claims_triage_001.json", { exact: true })).toBeVisible();
  await expect(evidencePackage.getByText("verified", { exact: true })).toBeVisible();
  await expect(evidencePackage.getByText("sha256:111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Verify saved package" }).click();
  await expect(page.getByText("Saved package hash matches the sidecar.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Build customer report" }).click();
  await expect(page.getByText("Customer verification report generated from saved evidence package.", { exact: true })).toBeVisible();
  await expect(releaseGate.getByRole("heading", { name: "Ready for controlled merge" })).toBeVisible();
  await expect(releaseGate.getByText("Scenario coverage, policy control, verified evidence, and customer-safe proof are all in place.", { exact: true })).toBeVisible();
  await expect(evidencePackage.getByText("verified for enterprise customer", { exact: true })).toBeVisible();
  await expect(evidencePackage.getByText("2 findings", { exact: true })).toBeVisible();
  const customerReport = page.getByLabel("Customer verification report");
  await expect(customerReport.getByRole("heading", { name: "This package can be reviewed without private payloads." })).toBeVisible();
  await expect(customerReport.getByText("claims-triage", { exact: false })).toBeVisible();
  await expect(customerReport.getByText("Readiness score", { exact: true })).toBeVisible();
  await expect(customerReport.getByText("Ready for controlled customer review.", { exact: true })).toBeVisible();
  await expect(customerReport.getByText("Evidence package hash verified", { exact: true })).toBeVisible();
  await expect(customerReport.getByText("High-risk egress controlled", { exact: true })).toBeVisible();
  await expect(customerReport.getByText("Plaintext payloads", { exact: true })).toBeVisible();
  await expect(customerReport.getByText("Excluded", { exact: true })).toBeVisible();
  await expect(customerReport.getByText("ready_for_merge", { exact: true })).toBeVisible();
  await expect(customerReport.getByText("Plaintext prompts excluded", { exact: true })).toBeVisible();
  await expect(customerReport.getByText("crm_tool", { exact: true })).toBeVisible();
  await expect(customerReport.getByText("crm.example.com · high egress", { exact: true })).toBeVisible();
  await expect(customerReport.getByText("undeclared_destination, undeclared_high_risk_egress", { exact: true })).toBeVisible();
  expect(evidencePackageCalled).toBe(true);
  expect(verificationCalled).toBe(true);
  expect(customerReportCalled).toBe(true);
  await expectNoRawValues(page);
});

test("settings is available but not part of the primary demo path", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Local settings" })).toBeVisible();
  await page.getByRole("button", { name: "Local settings" }).click();
  await expect(page.getByRole("heading", { name: "Local settings" })).toBeVisible();
  await page.getByLabel("Toggle local payload reveal").click();
  await page.getByRole("button", { name: "Confirm local reveal" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText("Confirmed locally")).toBeVisible();
  await expectNoRawValues(page);
});

test("responsive layout avoids horizontal page overflow", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Start with an agent" }).click();
  await page.getByRole("button", { name: "Review data flow" }).click();
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth
  }));
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 2);
});
