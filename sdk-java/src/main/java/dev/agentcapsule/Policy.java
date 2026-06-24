package dev.agentcapsule;

import java.util.List;
import java.util.Map;

public record Policy(
        int version,
        Map<String, DestinationRule> destinations,
        Defaults defaults
) {
    public record DestinationRule(
            String type,
            String domain,
            String risk,
            List<String> allowedData,
            List<String> redact,
            List<String> requireApproval
    ) {
    }

    public record Defaults(
            String undeclaredHighRiskEgress,
            String undeclaredDestination,
            String secrets
    ) {
    }

    public static Policy claimsTriagePolicy() {
        return new Policy(
                1,
                Map.of(
                        "crm",
                        new DestinationRule(
                                "external_tool",
                                "api.crm.example",
                                "high",
                                List.of("account_id", "support_tier"),
                                List.of("email", "account_notes"),
                                List.of("medical_information")
                        ),
                        "model_provider",
                        new DestinationRule(
                                "model_provider",
                                "api.model.example",
                                "medium",
                                List.of("prompt_content", "document_text", "policy_number", "incident_description"),
                                List.of("secrets"),
                                List.of("medical_information")
                        )
                ),
                new Defaults("block", "warn", "block")
        );
    }

    public static Policy restrictivePolicy() {
        return new Policy(1, Map.of(), new Defaults("block", "warn", "block"));
    }
}
