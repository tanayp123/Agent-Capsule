package dev.agentcapsule;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

public final class PolicyEngine {
    private static final List<String> RISK_ORDER = List.of("low", "medium", "high", "critical");
    private static final Map<String, String> DATA_CLASS_RISK = Map.ofEntries(
            Map.entry("account_id", "medium"),
            Map.entry("account_notes", "high"),
            Map.entry("address", "high"),
            Map.entry("claimant_name", "high"),
            Map.entry("customer_identifier", "high"),
            Map.entry("document_text", "high"),
            Map.entry("email", "high"),
            Map.entry("incident_description", "medium"),
            Map.entry("medical_information", "high"),
            Map.entry("model_output", "high"),
            Map.entry("policy_number", "medium"),
            Map.entry("prompt_content", "high"),
            Map.entry("secrets", "critical"),
            Map.entry("support_tier", "low"),
            Map.entry("tool_payload", "high"),
            Map.entry("user_identifier", "high")
    );

    private PolicyEngine() {
    }

    public static PolicyDecision evaluate(
            Policy policy,
            String destinationId,
            String destinationRisk,
            Collection<String> dataClasses,
            Collection<String> fields,
            String mode
    ) {
        List<String> data = sorted(dataClasses);
        List<String> observedFields = sorted(fields == null || fields.isEmpty() ? data : fields);
        Set<String> observedTokens = new HashSet<>(data);
        observedTokens.addAll(observedFields);

        if (destinationId == null || destinationId.isBlank()) {
            return new PolicyDecision("not_evaluated", "no destination", policy.version(), List.of());
        }

        if (observedTokens.contains("secrets")) {
            return applyMode(new PolicyDecision(
                    policy.defaults().secrets(),
                    "secrets default rule matched",
                    policy.version(),
                    observedFields
            ), mode);
        }

        Policy.DestinationRule destination = policy.destinations().get(destinationId);
        String egressRisk = classifyEgressRisk(destinationRisk, data);
        if (destination == null) {
            if (isHighOrCritical(egressRisk)) {
                return applyMode(new PolicyDecision(
                        policy.defaults().undeclaredHighRiskEgress(),
                        "undeclared high-risk egress",
                        policy.version(),
                        observedFields
                ), mode);
            }
            return applyMode(new PolicyDecision(
                    policy.defaults().undeclaredDestination(),
                    "undeclared destination",
                    policy.version(),
                    observedFields
            ), mode);
        }

        List<String> approvalFields = matchedFields(observedFields, data, destination.requireApproval());
        if (!approvalFields.isEmpty()) {
            return new PolicyDecision("require_approval", "destination approval rule matched", policy.version(), approvalFields);
        }

        List<String> redactionFields = matchedFields(observedFields, data, destination.redact());
        if (!redactionFields.isEmpty()) {
            return new PolicyDecision("redact", "destination redaction rule matched", policy.version(), redactionFields);
        }

        Set<String> allowed = new HashSet<>(destination.allowedData());
        if (!allowed.isEmpty() && !allowed.containsAll(observedTokens)) {
            List<String> allowedFields = observedFields.stream().filter(allowed::contains).sorted().toList();
            if (allowedFields.isEmpty()) {
                allowedFields = data.stream().filter(allowed::contains).sorted().toList();
            }
            return new PolicyDecision("allow_fields", "destination allowlist excluded fields", policy.version(), allowedFields);
        }

        return new PolicyDecision("allow", "destination declared and data allowed", policy.version(), observedFields);
    }

    public static String classifyDataRisk(Collection<String> dataClasses) {
        String risk = "low";
        for (String dataClass : dataClasses) {
            risk = maxRisk(risk, DATA_CLASS_RISK.getOrDefault(dataClass, "medium"));
        }
        return risk;
    }

    public static String classifyEgressRisk(String destinationRisk, Collection<String> dataClasses) {
        return maxRisk(destinationRisk == null ? "medium" : destinationRisk, classifyDataRisk(dataClasses));
    }

    private static List<String> matchedFields(Collection<String> fields, Collection<String> dataClasses, Collection<String> rules) {
        Set<String> ruleSet = new HashSet<>(rules);
        List<String> result = new ArrayList<>();
        fields.stream().filter(ruleSet::contains).forEach(result::add);
        dataClasses.stream().filter(ruleSet::contains).forEach(result::add);
        return sorted(result);
    }

    private static PolicyDecision applyMode(PolicyDecision decision, String mode) {
        if ("observe".equals(mode) && "block".equals(decision.action())) {
            return new PolicyDecision("warn", "observe_only: " + decision.reason(), decision.policyVersion(), decision.fields());
        }
        return decision;
    }

    private static boolean isHighOrCritical(String risk) {
        return "high".equals(risk) || "critical".equals(risk);
    }

    private static String maxRisk(String a, String b) {
        return RISK_ORDER.get(Math.max(RISK_ORDER.indexOf(a), RISK_ORDER.indexOf(b)));
    }

    static List<String> sorted(Collection<String> values) {
        return new ArrayList<>(new TreeSet<>(values));
    }
}
