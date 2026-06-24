#!/usr/bin/env python3
import argparse
import dataclasses
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

from agent_capsule import Capsule, Destination


SHOWCASE_SOURCE_FILE = "examples/claims-triage-python/claims_triage.py"


@dataclasses.dataclass(frozen=True)
class Claim:
    policy_number: str
    claimant_name: str = dataclasses.field(metadata={"agent_capsule_data_classes": ["claimant_name"]})
    email: str = dataclasses.field(metadata={"agent_capsule_data_classes": ["email"]})
    incident_description: str = dataclasses.field(
        metadata={"agent_capsule_data_classes": ["incident_description"]}
    )
    medical_information: str = dataclasses.field(
        metadata={"agent_capsule_data_classes": ["medical_information"]}
    )


@dataclasses.dataclass(frozen=True)
class MetadataRoute:
    request_id: str = dataclasses.field(metadata={"agent_capsule_data_classes": ["operational_metadata"]})
    queue: str = dataclasses.field(metadata={"agent_capsule_data_classes": ["operational_metadata"]})
    priority: str = dataclasses.field(metadata={"agent_capsule_data_classes": ["operational_metadata"]})


@dataclasses.dataclass(frozen=True)
class Scenario:
    scenario_id: str
    name: str
    description: str
    expected_result: str
    data_classes: Tuple[str, ...]
    input_factory: Callable[[], Any]
    crm_payload_factory: Callable[[Any, Dict[str, Any]], Dict[str, Any]]


def _sensitive_claim() -> Claim:
    return Claim(
        policy_number="POL-2026-001",
        claimant_name="Redacted Name",
        email="claimant@example.com",
        incident_description="Rear-end collision at low speed",
        medical_information="Neck pain reported after accident",
    )


def _approval_claim() -> Claim:
    return Claim(
        policy_number="POL-2026-002",
        claimant_name="Redacted Name",
        email="claimant@example.com",
        incident_description="Claimant reported medical follow-up after collision",
        medical_information="Neck pain reported after accident",
    )


def _metadata_route() -> MetadataRoute:
    return MetadataRoute(request_id="REQ-2026-114", queue="standard_review", priority="normal")


def _sensitive_crm_payload(input_payload: Any, classification: Dict[str, Any]) -> Dict[str, Any]:
    claim = input_payload
    return {
        "policy_number": claim.policy_number,
        "email": claim.email,
        "account_notes": "Claim requires review because medical context is present",
        "route": classification["route"],
        "reason_code": classification["reason_code"],
    }


def _approval_payload(input_payload: Any, classification: Dict[str, Any]) -> Dict[str, Any]:
    claim = input_payload
    return {
        "policy_number": claim.policy_number,
        "email": claim.email,
        "account_notes": "Claim requires review because medical context is present",
        "approval_reason": classification["reason_code"],
    }


def _metadata_payload(input_payload: Any, classification: Dict[str, Any]) -> Dict[str, Any]:
    route = input_payload
    return {
        "request_id": route.request_id,
        "queue": route.queue,
        "priority": route.priority,
        "route": classification["route"],
    }


SCENARIOS: Dict[str, Scenario] = {
    "sensitive-crm-egress": Scenario(
        scenario_id="sensitive-crm-egress",
        name="Sensitive CRM egress",
        description="The agent classifies a claim, then sends email and account notes to an external CRM.",
        expected_result="High-risk destination review",
        data_classes=("email", "account_notes"),
        input_factory=_sensitive_claim,
        crm_payload_factory=_sensitive_crm_payload,
    ),
    "metadata-only-check": Scenario(
        scenario_id="metadata-only-check",
        name="Metadata-only update",
        description="The agent routes operational metadata through the same CRM path without customer text.",
        expected_result="Destination declaration review",
        data_classes=("operational_metadata",),
        input_factory=_metadata_route,
        crm_payload_factory=_metadata_payload,
    ),
    "approval-required": Scenario(
        scenario_id="approval-required",
        name="Approval-required note",
        description="The agent prepares a sensitive CRM update that should require human approval.",
        expected_result="Human approval control",
        data_classes=("email", "account_notes", "medical_information"),
        input_factory=_approval_claim,
        crm_payload_factory=_approval_payload,
    ),
}


def build_agent(
    trace_dir: str,
    policy_path: str = None,
    agent_version: str = "showcase.1",
    model_destination_id: str = "model_provider",
    model_destination_domain: str = "api.model.example",
    crm_destination_id: str = "crm",
    crm_destination_domain: str = "api.crm.example",
):
    resolved_policy = policy_path if policy_path is not None else os.environ.get(
        "AGENT_CAPSULE_POLICY",
        "agent-capsule.policy.json",
    )
    capsule = Capsule.init(
        mode="observe",
        policy=resolved_policy,
        trace_dir=trace_dir,
        agent_name="claims-triage",
        agent_version=agent_version,
    )

    model_destination = Destination(
        id=model_destination_id,
        type="model_provider",
        domain=model_destination_domain,
        provider="Example Model",
        environment="production",
        risk="medium",
    )

    crm_destination = Destination(
        id=crm_destination_id,
        type="external_tool",
        domain=crm_destination_domain,
        provider="Example CRM",
        environment="production",
        risk="high",
    )

    def classify_claim(payload: Any) -> Dict[str, Any]:
        if isinstance(payload, MetadataRoute):
            return {
                "classification": "metadata_update",
                "route": "standard_review",
                "reason": "Metadata-only workflow routed without customer text",
                "reason_code": "metadata_only",
            }

        return {
            "classification": "needs_review",
            "route": "human_review",
            "reason": "Claim requires review because medical context is present",
            "reason_code": "medical_context",
        }

    def update_crm(payload: Dict[str, Any]) -> Dict[str, str]:
        return {
            "status": "queued",
            "destination_record": "crm_case_update",
        }

    return (
        capsule,
        capsule.wrap_model_client(
            classify_claim,
            component_name="classify-claim",
            destination=model_destination,
            token_counter=lambda result: len(json.dumps(result, sort_keys=True).split()),
        ),
        capsule.wrap_tool(
            update_crm,
            component_name="crm.update_account",
            destination=crm_destination,
        ),
    )


def run_claims_triage(
    trace_dir: str,
    scenario_id: str = "sensitive-crm-egress",
    policy_path: str = None,
    run_id: str = None,
    agent_version: str = "showcase.1",
    model_destination_id: str = "model_provider",
    model_destination_domain: str = "api.model.example",
    crm_destination_id: str = "crm",
    crm_destination_domain: str = "api.crm.example",
) -> Dict[str, Any]:
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        raise ValueError("unknown scenario_id: %s" % scenario_id)

    capsule, classify_claim, update_crm = build_agent(
        trace_dir=trace_dir,
        policy_path=policy_path,
        agent_version=agent_version,
        model_destination_id=model_destination_id,
        model_destination_domain=model_destination_domain,
        crm_destination_id=crm_destination_id,
        crm_destination_domain=crm_destination_domain,
    )
    input_payload = scenario.input_factory()

    with capsule.run("claim-triage / %s" % scenario.name, run_id=run_id) as run:
        classification = classify_claim(input_payload)
        update_crm(scenario.crm_payload_factory(input_payload, classification))
        run.record_output(classification)

    return {
        "trace_path": str(run.trace_path),
        "run_id": run.run_id,
        "trace_id": run.trace_id,
        "agent_name": "claims-triage",
        "agent_version": agent_version,
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.name,
        "expected_result": scenario.expected_result,
        "data_classes": list(scenario.data_classes),
        "source_file": SHOWCASE_SOURCE_FILE,
        "entrypoint": "run_claims_triage",
        "instrumentation": ["Capsule.wrap_model_client", "Capsule.wrap_tool"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-dir", default=os.environ.get("AGENT_CAPSULE_TRACE_DIR", ".agent-capsule/traces"))
    parser.add_argument("--policy", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--scenario-id", choices=sorted(SCENARIOS), default="sensitive-crm-egress")
    parser.add_argument("--json", action="store_true", help="Print safe run metadata as JSON.")
    args = parser.parse_args()

    result = run_claims_triage(
        trace_dir=args.trace_dir,
        scenario_id=args.scenario_id,
        policy_path=args.policy,
        run_id=args.run_id,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(Path(result["trace_path"]))


if __name__ == "__main__":
    main()
