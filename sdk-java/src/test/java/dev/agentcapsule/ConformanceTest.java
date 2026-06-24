package dev.agentcapsule;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public final class ConformanceTest {
    public static void main(String[] args) throws Exception {
        policyDecisionFixturesMatch();
        annotationClassificationWorks();
        builderAndInterceptorsPropagateContext();
        guardModeBlocksHighRiskEgress();
    }

    private static void policyDecisionFixturesMatch() {
        List<Case> cases = List.of(
                new Case(Policy.claimsTriagePolicy(), "crm", "high", List.of("email", "account_notes"), List.of("email", "account_notes"), "redact", List.of("account_notes", "email"), "destination redaction rule matched"),
                new Case(Policy.claimsTriagePolicy(), "crm", "high", List.of("account_id", "support_tier"), List.of("account_id", "support_tier"), "allow", List.of("account_id", "support_tier"), "destination declared and data allowed"),
                new Case(Policy.claimsTriagePolicy(), "crm", "high", List.of("medical_information"), List.of("medical_information"), "require_approval", List.of("medical_information"), "destination approval rule matched"),
                new Case(Policy.claimsTriagePolicy(), "crm", "high", List.of("account_id", "support_tier", "customer_identifier"), List.of("account_id", "support_tier", "customer_identifier"), "allow_fields", List.of("account_id", "support_tier"), "destination allowlist excluded fields"),
                new Case(Policy.restrictivePolicy(), "external_ocr", "high", List.of("medical_information", "document_text"), List.of("medical_information", "document_text"), "block", List.of("document_text", "medical_information"), "undeclared high-risk egress"),
                new Case(Policy.restrictivePolicy(), "analytics", "medium", List.of("support_tier"), List.of("support_tier"), "warn", List.of("support_tier"), "undeclared destination"),
                new Case(Policy.claimsTriagePolicy(), "crm", "high", List.of("secrets"), List.of("api_key"), "block", List.of("api_key"), "secrets default rule matched")
        );

        for (Case item : cases) {
            PolicyDecision decision = PolicyEngine.evaluate(item.policy, item.destinationId, item.destinationRisk, item.dataClasses, item.fields, "guard");
            require(decision.action().equals(item.action), "action mismatch for " + item.destinationId);
            require(decision.fields().equals(item.expectedFields), "fields mismatch for " + item.destinationId + ": " + decision.fields());
            require(decision.reason().equals(item.reason), "reason mismatch for " + item.destinationId);
        }
    }

    private static void annotationClassificationWorks() {
        ClaimPayload payload = new ClaimPayload("claimant@example.com", "Sensitive account note", "gold");
        require(FieldClassifier.classify(payload).equals(List.of("account_notes", "email", "support_tier")), "annotation classifier drifted");
    }

    private static void builderAndInterceptorsPropagateContext() throws Exception {
        Capsule capsule = Capsule.builder()
                .mode("guard")
                .policy(Policy.claimsTriagePolicy())
                .agentName("claims-triage")
                .build();
        Destination crm = new Destination("crm", "external_tool", "api.crm.example", "Example CRM", "high");
        Capsule.ThrowingFunction<ClaimPayload, Map<String, Object>> tool = capsule.interceptHttp(
                "crm.upsert_account",
                crm,
                payload -> Map.of("ok", true)
        );

        capsule.run("phase13-java", () -> {
            Capsule.ThrowingSupplier<Map<String, Object>> propagated = capsule.propagate(() ->
                    tool.apply(new ClaimPayload("claimant@example.com", "Sensitive note", "gold"))
            );
            CompletableFuture<Map<String, Object>> result = CompletableFuture.supplyAsync(() -> {
                try {
                    return propagated.get();
                } catch (Exception exc) {
                    throw new RuntimeException(exc);
                }
            });
            return result.join();
        });

        Capsule.Trace trace = capsule.trace();
        require(trace.language().equals("java"), "trace language mismatch");
        require(trace.spans().size() == 1, "span count mismatch");
        require(trace.spans().get(0).policyDecision().action().equals("redact"), "interceptor did not redact");
    }

    private static void guardModeBlocksHighRiskEgress() throws Exception {
        Capsule capsule = Capsule.builder()
                .mode("guard")
                .policy(Policy.restrictivePolicy())
                .agentName("claims-triage")
                .build();
        Capsule.ThrowingFunction<Map<String, Object>, Map<String, Object>> tool = capsule.wrapTool(
                "external_ocr.extract",
                new Destination("external_ocr", "external_tool", "api.ocr.example", "Example OCR", "high"),
                payload -> Map.of("ok", true)
        );

        boolean blocked = false;
        try {
            capsule.run("blocked-java", () -> tool.apply(Map.of(
                    "document", "private document",
                    "medical_information", "private diagnosis"
            )));
        } catch (Capsule.CapsuleGuardException exc) {
            blocked = true;
        }
        require(blocked, "guard mode did not block undeclared high-risk egress");
        require(capsule.trace().spans().get(0).status().equals("blocked"), "blocked span not recorded");
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private record Case(
            Policy policy,
            String destinationId,
            String destinationRisk,
            List<String> dataClasses,
            List<String> fields,
            String action,
            List<String> expectedFields,
            String reason
    ) {
    }

    private record ClaimPayload(
            @DataClass("email") String email,
            @DataClass("account_notes") String notes,
            @DataClass("support_tier") String supportTier
    ) {
    }
}
