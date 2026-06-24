use agent_capsule::{
    classify_json, evaluate_policy, Capsule, CapsuleGuardError, Destination, Policy,
};
use serde::Deserialize;
use serde_json::json;
use std::fs;
use std::path::PathBuf;

#[derive(Deserialize)]
struct Conformance {
    cases: Vec<Case>,
}

#[derive(Deserialize)]
struct Case {
    name: String,
    policy: String,
    destination_id: String,
    destination_risk: String,
    data_classes: Vec<String>,
    fields: Vec<String>,
    expected: Expected,
}

#[derive(Deserialize)]
struct Expected {
    action: String,
    fields: Vec<String>,
    reason: String,
}

#[test]
fn shared_policy_decision_fixtures_match() {
    let root = PathBuf::from("..");
    let fixture: Conformance = serde_json::from_str(
        &fs::read_to_string(root.join("fixtures/conformance/policy-decisions.json")).unwrap(),
    )
    .unwrap();
    for item in fixture.cases {
        let policy: Policy = serde_json::from_str(&fs::read_to_string(root.join(item.policy)).unwrap()).unwrap();
        let decision = evaluate_policy(
            &policy,
            Some(&item.destination_id),
            &item.destination_risk,
            &item.data_classes,
            &item.fields,
            "guard",
        );
        assert_eq!(decision.action, item.expected.action, "{}", item.name);
        assert_eq!(decision.fields, item.expected.fields, "{}", item.name);
        assert_eq!(decision.reason, item.expected.reason, "{}", item.name);
    }
}

#[test]
fn serde_classification_reads_field_names() {
    let payload = json!({
        "email": "claimant@example.com",
        "account_notes": "Sensitive account note",
        "support_tier": "gold"
    });
    assert_eq!(classify_json(&payload), vec!["account_notes", "email", "support_tier"]);
}

#[tokio::test]
async fn tokio_wrapper_records_redacted_trace() {
    let root = PathBuf::from("..");
    let policy: Policy = serde_json::from_str(&fs::read_to_string(root.join("fixtures/policies/crm-policy.json")).unwrap()).unwrap();
    let capsule = Capsule::new("guard", policy, "claims-triage");
    capsule
        .run("phase13-rust", || async {
            capsule
                .wrap_tool(
                    "crm.upsert_account",
                    Destination {
                        id: "crm".to_string(),
                        destination_type: "external_tool".to_string(),
                        domain: Some("api.crm.example".to_string()),
                        provider: "Example CRM".to_string(),
                        environment: "production".to_string(),
                        risk: "high".to_string(),
                    },
                    json!({
                        "account_id": "acct_123",
                        "email": "claimant@example.com",
                        "account_notes": "Sensitive note"
                    }),
                    |_payload| async { json!({"ok": true}) },
                )
                .await
                .unwrap();
        })
        .await;

    let trace = capsule.trace().unwrap();
    assert_eq!(trace.language, "rust");
    assert_eq!(trace.spans.len(), 1);
    assert_eq!(trace.spans[0].status.as_str(), "redacted");
    assert_eq!(trace.spans[0].policy_decision.action.as_str(), "redact");
}

#[tokio::test]
async fn guard_blocks_undeclared_high_risk_egress() {
    let root = PathBuf::from("..");
    let policy: Policy = serde_json::from_str(&fs::read_to_string(root.join("fixtures/policies/restrictive-policy.json")).unwrap()).unwrap();
    let capsule = Capsule::new("guard", policy, "claims-triage");
    let result = capsule
        .run("blocked-rust", || async {
            capsule
                .wrap_tool(
                    "external_ocr.extract",
                    Destination {
                        id: "external_ocr".to_string(),
                        destination_type: "external_tool".to_string(),
                        domain: Some("api.ocr.example".to_string()),
                        provider: "Example OCR".to_string(),
                        environment: "production".to_string(),
                        risk: "high".to_string(),
                    },
                    json!({
                        "document": "private document",
                        "medical_information": "private diagnosis"
                    }),
                    |_payload| async { json!({"ok": true}) },
                )
                .await
        })
        .await;

    assert!(matches!(result, Err(CapsuleGuardError { .. })));
    assert_eq!(capsule.trace().unwrap().spans[0].status.as_str(), "blocked");
}
