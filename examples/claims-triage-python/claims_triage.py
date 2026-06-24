#!/usr/bin/env python3
import argparse
import dataclasses
import json
import os
from pathlib import Path

from agent_capsule import Capsule, Destination


@dataclasses.dataclass
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


def build_agent(trace_dir):
    capsule = Capsule.init(
        mode="observe",
        policy=os.environ.get("AGENT_CAPSULE_POLICY", "agent-capsule.policy.json"),
        trace_dir=trace_dir,
        agent_name="claims-triage",
        agent_version="0.1.0",
    )

    model_destination = Destination(
        id="model_provider",
        type="model_provider",
        domain="api.model.example",
        provider="Example Model",
        environment="production",
        risk="medium",
    )

    crm_destination = Destination(
        id="crm",
        type="external_tool",
        domain="api.crm.example",
        provider="Example CRM",
        environment="production",
        risk="high",
    )

    def classify_claim(claim):
        return {
            "classification": "needs_review",
            "reason": "claim includes medical context and requires adjuster review",
        }

    def update_crm(payload):
        return {"status": "queued"}

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


def run_claims_triage(trace_dir):
    capsule, classify_claim, update_crm = build_agent(trace_dir)
    claim = Claim(
        policy_number="POL-2026-001",
        claimant_name="Redacted Name",
        email="claimant@example.com",
        incident_description="Rear-end collision at low speed",
        medical_information="Neck pain reported after accident",
    )

    with capsule.run("claim-triage") as run:
        classification = classify_claim(claim)
        update_crm(
            {
                "policy_number": claim.policy_number,
                "email": claim.email,
                "account_notes": "Claim requires review because medical context is present",
            }
        )
        run.record_output(classification)

    return run.trace_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-dir", default=os.environ.get("AGENT_CAPSULE_TRACE_DIR", ".agent-capsule/traces"))
    args = parser.parse_args()

    trace_path = run_claims_triage(args.trace_dir)
    print(Path(trace_path))


if __name__ == "__main__":
    main()
