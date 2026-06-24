package dev.agentcapsule;

public record Destination(
        String id,
        String type,
        String domain,
        String provider,
        String environment,
        String risk
) {
    public Destination(String id, String type, String domain, String provider, String risk) {
        this(id, type, domain, provider, "production", risk);
    }
}
