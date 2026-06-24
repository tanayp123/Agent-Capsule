package dev.agentcapsule;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class Capsule {
    private static final ThreadLocal<RunContext> CURRENT_RUN = new ThreadLocal<>();

    private final String mode;
    private final Policy policy;
    private final String agentName;
    private final String agentVersion;
    private RunContext lastRun;

    private Capsule(Builder builder) {
        this.mode = builder.mode;
        this.policy = builder.policy;
        this.agentName = builder.agentName;
        this.agentVersion = builder.agentVersion;
    }

    public static Builder builder() {
        return new Builder();
    }

    public <T> T run(String name, ThrowingSupplier<T> body) throws Exception {
        RunContext context = new RunContext("run_" + safeId(name), "trc_" + safeId(name), Instant.now().toString());
        lastRun = context;
        CURRENT_RUN.set(context);
        try {
            return body.get();
        } finally {
            CURRENT_RUN.remove();
        }
    }

    public <T> ThrowingSupplier<T> propagate(ThrowingSupplier<T> body) {
        RunContext captured = CURRENT_RUN.get();
        return () -> {
            RunContext previous = CURRENT_RUN.get();
            if (captured != null) {
                CURRENT_RUN.set(captured);
            }
            try {
                return body.get();
            } finally {
                if (previous == null) {
                    CURRENT_RUN.remove();
                } else {
                    CURRENT_RUN.set(previous);
                }
            }
        };
    }

    public <T, R> ThrowingFunction<T, R> interceptModel(String componentName, Destination destination, ThrowingFunction<T, R> call) {
        return intercept("model_call", componentName, destination, call);
    }

    public <T, R> ThrowingFunction<T, R> interceptHttp(String componentName, Destination destination, ThrowingFunction<T, R> call) {
        return intercept("tool_call", componentName, destination, call);
    }

    public <T, R> ThrowingFunction<T, R> wrapTool(String componentName, Destination destination, ThrowingFunction<T, R> call) {
        return intercept("tool_call", componentName, destination, call);
    }

    public Trace trace() {
        if (lastRun == null) {
            throw new IllegalStateException("no run has completed");
        }
        return new Trace(
                1,
                lastRun.traceId,
                lastRun.runId,
                agentName,
                agentVersion,
                mode,
                "java",
                Runtime.version().toString(),
                "0.1.0-beta.1",
                lastRun.createdAt,
                List.copyOf(lastRun.spans),
                new ArrayList<>(lastRun.destinations.values())
        );
    }

    private <T, R> ThrowingFunction<T, R> intercept(String componentType, String componentName, Destination destination, ThrowingFunction<T, R> call) {
        return payload -> {
            RunContext context = CURRENT_RUN.get();
            if (context == null) {
                throw new IllegalStateException("Agent Capsule operation requires an active run context");
            }
            List<String> dataClasses = FieldClassifier.classify(payload);
            PolicyDecision decision = PolicyEngine.evaluate(policy, destination.id(), destination.risk(), dataClasses, dataClasses, mode);
            String status = "ok";
            Object guardedPayload = payload;
            List<String> markers = new ArrayList<>();
            String start = Instant.now().toString();
            try {
                if (!"observe".equals(mode) && "block".equals(decision.action())) {
                    status = "blocked";
                    throw new CapsuleGuardException(decision.reason());
                }
                if (!"observe".equals(mode) && "require_approval".equals(decision.action())) {
                    status = "approval_required";
                    throw new CapsuleGuardException(decision.reason());
                }
                if (!"observe".equals(mode) && "redact".equals(decision.action())) {
                    status = "redacted";
                    markers.addAll(decision.fields().stream().map(field -> "redact:" + field).toList());
                }
                return call.apply((T) guardedPayload);
            } catch (Exception ex) {
                if ("ok".equals(status) || "redacted".equals(status)) {
                    status = "error";
                }
                throw ex;
            } finally {
                boolean declared = policy.destinations().containsKey(destination.id());
                Policy.DestinationRule rule = policy.destinations().get(destination.id());
                context.destinations.put(destination.id(), new DestinationTrace(
                        destination.id(),
                        destination.type(),
                        destination.domain(),
                        destination.provider(),
                        destination.environment(),
                        destination.risk(),
                        declared,
                        rule == null ? List.of() : rule.allowedData(),
                        dataClasses
                ));
                context.spans.add(new Span(
                        "spn_" + UUID.randomUUID().toString().replace("-", ""),
                        null,
                        componentType,
                        componentName,
                        start,
                        Instant.now().toString(),
                        status,
                        String.valueOf(payload).getBytes(StandardCharsets.UTF_8).length,
                        null,
                        sha256(String.valueOf(payload)),
                        dataClasses,
                        destination.id(),
                        decision,
                        null,
                        markers
                ));
            }
        };
    }

    public static final class Builder {
        private String mode = "observe";
        private Policy policy = Policy.restrictivePolicy();
        private String agentName = "agent";
        private String agentVersion = "0.1.0";

        public Builder mode(String mode) {
            this.mode = mode;
            return this;
        }

        public Builder policy(Policy policy) {
            this.policy = policy;
            return this;
        }

        public Builder agentName(String agentName) {
            this.agentName = agentName;
            return this;
        }

        public Builder agentVersion(String agentVersion) {
            this.agentVersion = agentVersion;
            return this;
        }

        public Capsule build() {
            return new Capsule(this);
        }
    }

    private record RunContext(String runId, String traceId, String createdAt, List<Span> spans, Map<String, DestinationTrace> destinations) {
        private RunContext(String runId, String traceId, String createdAt) {
            this(runId, traceId, createdAt, new ArrayList<>(), new LinkedHashMap<>());
        }
    }

    public record Span(
            String spanId,
            String parentSpanId,
            String componentType,
            String componentName,
            String startTime,
            String endTime,
            String status,
            int payloadSizeBytes,
            Integer tokenCount,
            String contentHash,
            List<String> dataClasses,
            String destinationId,
            PolicyDecision policyDecision,
            Object errorSummary,
            List<String> redactionMarkers
    ) {
    }

    public record DestinationTrace(
            String id,
            String type,
            String domain,
            String provider,
            String environment,
            String risk,
            boolean declaredInPolicy,
            List<String> allowedDataClasses,
            List<String> observedDataClasses
    ) {
    }

    public record Trace(
            int traceSchemaVersion,
            String traceId,
            String runId,
            String agentName,
            String agentVersion,
            String mode,
            String language,
            String runtimeVersion,
            String sdkVersion,
            String createdAt,
            List<Span> spans,
            List<DestinationTrace> destinations
    ) {
    }

    public interface ThrowingFunction<T, R> {
        R apply(T value) throws Exception;
    }

    public interface ThrowingSupplier<T> {
        T get() throws Exception;
    }

    public static final class CapsuleGuardException extends RuntimeException {
        public CapsuleGuardException(String message) {
            super(message);
        }
    }

    private static String safeId(String value) {
        String slug = value.toLowerCase().replaceAll("[^a-z0-9_-]+", "_").replaceAll("^_+|_+$", "");
        return slug.isBlank() ? UUID.randomUUID().toString().replace("-", "") : slug;
    }

    private static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder("sha256:");
            for (byte b : digest) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException exc) {
            throw new IllegalStateException("SHA-256 is unavailable", exc);
        }
    }
}
