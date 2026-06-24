import assert from "node:assert/strict";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { z } from "zod";
import {
  Capsule,
  CapsuleGuardError,
  Destination,
  Policy,
  classified,
  classifyPayload,
  evaluatePolicy,
  zodClassified
} from "../src/index.ts";

const root = resolve("..");
const crmPolicy = JSON.parse(readFileSync(resolve(root, "fixtures/policies/crm-policy.json"), "utf8")) as Policy;
const conformance = JSON.parse(readFileSync(resolve(root, "fixtures/conformance/policy-decisions.json"), "utf8")) as {
  cases: Array<{
    name: string;
    policy: string;
    destination_id: string;
    destination_risk: "low" | "medium" | "high" | "critical";
    data_classes: string[];
    fields: string[];
    expected: { action: string; fields: string[]; reason: string };
  }>;
};

test("shared policy decision fixtures match TypeScript evaluator", () => {
  for (const item of conformance.cases) {
    const policy = JSON.parse(readFileSync(resolve(root, item.policy), "utf8")) as Policy;
    const decision = evaluatePolicy(
      policy,
      item.destination_id,
      item.destination_risk,
      item.data_classes,
      item.fields,
      "guard"
    );
    assert.equal(decision.action, item.expected.action, item.name);
    assert.deepEqual(decision.fields, item.expected.fields, item.name);
    assert.equal(decision.reason, item.expected.reason, item.name);
  }
});

test("zod field annotations participate in classification", () => {
  const emailSchema = zodClassified(z.string().email(), ["email"]);
  const parsed = emailSchema.parse("claimant@example.com");
  assert.deepEqual(classifyPayload({ email: parsed, support_tier: "gold" }), ["email", "support_tier"]);
});

test("async context propagates through wrapped tool calls", async () => {
  const destination: Destination = {
    id: "crm",
    type: "external_tool",
    domain: "api.crm.example",
    provider: "Example CRM",
    risk: "high"
  };
  const received: unknown[] = [];
  const capsule = new Capsule({ mode: "guard", policy: crmPolicy, agentName: "claims-triage" });
  const tool = capsule.wrapTool("crm.upsert_account", destination, async (payload: unknown) => {
    await Promise.resolve();
    received.push(payload);
    return { ok: true };
  });

  await capsule.run("phase13-typescript", async () => {
    await Promise.all([
      tool({
        account_id: classified("acct_123", ["account_id"]),
        email: classified("claimant@example.com", ["email"]),
        account_notes: classified("Sensitive account note", ["account_notes"])
      }),
      tool({
        account_id: classified("acct_456", ["account_id"]),
        email: classified("second@example.com", ["email"]),
        account_notes: classified("Second sensitive note", ["account_notes"])
      })
    ]);
  });

  assert.equal(received.length, 2);
  assert.match(JSON.stringify(received), /\[redacted:email\]/);
  const trace = capsule.trace();
  assert.equal(trace.language, "typescript");
  assert.equal(trace.spans.length, 2);
  assert.deepEqual(new Set(trace.spans.map((span) => span.policy_decision.action)), new Set(["redact"]));
  assert.equal(trace.destinations[0]?.declared_in_policy, true);

  const output = resolve("build/conformance/typescript-trace.json");
  mkdirSync(dirname(output), { recursive: true });
  writeFileSync(output, `${JSON.stringify(trace, null, 2)}\n`, "utf8");
  assert.doesNotMatch(JSON.stringify(trace), /claimant@example.com|Sensitive account note/);
});

test("guard mode blocks undeclared high-risk egress", async () => {
  const restrictive = JSON.parse(readFileSync(resolve(root, "fixtures/policies/restrictive-policy.json"), "utf8")) as Policy;
  const capsule = new Capsule({ mode: "guard", policy: restrictive, agentName: "claims-triage" });
  const tool = capsule.wrapTool("external_ocr.extract", {
    id: "external_ocr",
    type: "external_tool",
    domain: "api.ocr.example",
    provider: "Example OCR",
    risk: "high"
  }, async (_payload: unknown) => ({ ok: true }));

  await assert.rejects(
    () => capsule.run("blocked-typescript", () => tool({
      document: classified("private document", ["document_text"]),
      medical_information: classified("private diagnosis", ["medical_information"])
    })),
    CapsuleGuardError
  );
  assert.equal(capsule.trace().spans[0]?.status, "blocked");
});
