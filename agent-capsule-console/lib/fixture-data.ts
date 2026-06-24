import safeTraceJson from "@/fixtures/safe-trace-import.json";
import privacyMapJson from "@/fixtures/privacy-map.json";
import replayComparisonJson from "@/fixtures/replay-comparison.json";
import manifestJson from "@/fixtures/manifest-inspect.json";
import type { ManifestInspection, PrivacyMap, ReplayComparison, RunSummary, SafeTrace } from "@/lib/types";

export const safeTrace = safeTraceJson as SafeTrace;
export const privacyMap = privacyMapJson as PrivacyMap;
export const replayComparison = replayComparisonJson as ReplayComparison;
export const manifestInspection = manifestJson as ManifestInspection;

export const runs: RunSummary[] = [
  {
    run_id: "run_failed_model_001",
    trace_id: safeTrace.source_trace_id,
    agent_name: "claims-triage",
    status: safeTrace.diagnostic_summary.status,
    span_count: safeTrace.spans.length,
    created_at: safeTrace.created_at
  },
  {
    run_id: privacyMap.run_id,
    trace_id: privacyMap.trace_id,
    agent_name: "claims-triage",
    status: "warning",
    span_count: privacyMap.destinations.reduce((total, destination) => total + destination.span_count, 0),
    created_at: "2026-06-23T18:25:00Z"
  }
];
