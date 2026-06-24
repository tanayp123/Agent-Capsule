package dev.agentcapsule;

import java.util.List;

public record PolicyDecision(
        String action,
        String reason,
        Integer policyVersion,
        List<String> fields
) {
}
