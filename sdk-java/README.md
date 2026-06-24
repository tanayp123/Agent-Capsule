# Java SDK

Purpose: JVM instrumentation for enterprise agent services.

Phase 13 status: beta implementation.

Tooling:

- Java 17+
- Plain `javac` and `java` for the beta conformance test

Implemented beta features:

- Builder-style configuration
- Annotation-based field classification
- HTTP and model client interceptors
- Shared schema conformance tests

## Run Tests

```bash
mkdir -p build/classes
find src/main/java src/test/java -name '*.java' | sort > build/sources.txt
javac -d build/classes @build/sources.txt
java -cp build/classes dev.agentcapsule.ConformanceTest
```

The Java SDK uses explicit propagation helpers for asynchronous boundaries so developers can carry the active run context into executor or `CompletableFuture` work.
