use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::future::Future;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use tracing::info_span;

pub const SDK_VERSION: &str = "0.1.0-beta.1";

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Policy {
    pub version: i32,
    pub agent: BTreeMap<String, String>,
    pub destinations: BTreeMap<String, DestinationRule>,
    pub defaults: Defaults,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct DestinationRule {
    #[serde(rename = "type")]
    pub destination_type: String,
    pub domain: Option<String>,
    pub risk: String,
    pub allowed_data: Vec<String>,
    pub redact: Vec<String>,
    pub require_approval: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Defaults {
    pub undeclared_high_risk_egress: String,
    pub undeclared_destination: String,
    pub secrets: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
pub struct PolicyDecision {
    pub action: String,
    pub reason: String,
    pub policy_version: Option<i32>,
    pub fields: Vec<String>,
}

#[derive(Clone, Debug)]
pub struct Destination {
    pub id: String,
    pub destination_type: String,
    pub domain: Option<String>,
    pub provider: String,
    pub environment: String,
    pub risk: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct Trace {
    pub trace_schema_version: i32,
    pub trace_id: String,
    pub run_id: String,
    pub agent: Agent,
    pub mode: String,
    pub language: String,
    pub runtime_version: String,
    pub sdk_version: String,
    pub created_at: String,
    pub spans: Vec<Span>,
    pub destinations: Vec<DestinationTrace>,
}

#[derive(Clone, Debug, Serialize)]
pub struct Agent {
    pub name: String,
    pub version: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct Span {
    pub span_id: String,
    pub parent_span_id: Option<String>,
    pub component_type: String,
    pub component_name: String,
    pub start_time: String,
    pub end_time: String,
    pub status: String,
    pub payload_size_bytes: usize,
    pub token_count: Option<i32>,
    pub content_hash: Option<String>,
    pub data_classes: Vec<String>,
    pub destination_id: Option<String>,
    pub policy_decision: PolicyDecision,
    pub error_summary: Option<Value>,
    pub redaction_markers: Vec<String>,
}

#[derive(Clone, Debug, Serialize)]
pub struct DestinationTrace {
    pub id: String,
    #[serde(rename = "type")]
    pub destination_type: String,
    pub domain: Option<String>,
    pub provider: String,
    pub environment: String,
    pub risk: String,
    pub declared_in_policy: bool,
    pub allowed_data_classes: Vec<String>,
    pub observed_data_classes: Vec<String>,
}

#[derive(Clone)]
pub struct Capsule {
    mode: String,
    policy: Policy,
    agent_name: String,
    agent_version: String,
    run: Arc<Mutex<Option<RunContext>>>,
}

#[derive(Clone, Debug)]
struct RunContext {
    run_id: String,
    trace_id: String,
    created_at: String,
    spans: Vec<Span>,
    destinations: BTreeMap<String, DestinationTrace>,
}

#[derive(Debug)]
pub struct CapsuleGuardError {
    pub message: String,
}

impl std::fmt::Display for CapsuleGuardError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl std::error::Error for CapsuleGuardError {}

pub fn evaluate_policy(
    policy: &Policy,
    destination_id: Option<&str>,
    destination_risk: &str,
    data_classes: &[String],
    fields: &[String],
    mode: &str,
) -> PolicyDecision {
    let data = sorted_unique(data_classes);
    let observed_fields = if fields.is_empty() { data.clone() } else { sorted_unique(fields) };
    let observed_tokens: BTreeSet<String> = data.iter().chain(observed_fields.iter()).cloned().collect();

    let Some(destination_id) = destination_id else {
        return PolicyDecision {
            action: "not_evaluated".to_string(),
            reason: "no destination".to_string(),
            policy_version: Some(policy.version),
            fields: vec![],
        };
    };

    if observed_tokens.contains("secrets") {
        return apply_mode(
            PolicyDecision {
                action: policy.defaults.secrets.clone(),
                reason: "secrets default rule matched".to_string(),
                policy_version: Some(policy.version),
                fields: observed_fields,
            },
            mode,
        );
    }

    let destination = policy.destinations.get(destination_id);
    let egress_risk = classify_egress_risk(destination_risk, &data);
    if destination.is_none() {
        if is_high_or_critical(&egress_risk) {
            return apply_mode(
                PolicyDecision {
                    action: policy.defaults.undeclared_high_risk_egress.clone(),
                    reason: "undeclared high-risk egress".to_string(),
                    policy_version: Some(policy.version),
                    fields: observed_fields,
                },
                mode,
            );
        }
        return apply_mode(
            PolicyDecision {
                action: policy.defaults.undeclared_destination.clone(),
                reason: "undeclared destination".to_string(),
                policy_version: Some(policy.version),
                fields: observed_fields,
            },
            mode,
        );
    }

    let destination = destination.expect("destination checked above");
    let approval_fields = matched_fields(&observed_fields, &data, &destination.require_approval);
    if !approval_fields.is_empty() {
        return PolicyDecision {
            action: "require_approval".to_string(),
            reason: "destination approval rule matched".to_string(),
            policy_version: Some(policy.version),
            fields: approval_fields,
        };
    }

    let redaction_fields = matched_fields(&observed_fields, &data, &destination.redact);
    if !redaction_fields.is_empty() {
        return PolicyDecision {
            action: "redact".to_string(),
            reason: "destination redaction rule matched".to_string(),
            policy_version: Some(policy.version),
            fields: redaction_fields,
        };
    }

    let allowed: BTreeSet<String> = destination.allowed_data.iter().cloned().collect();
    if !allowed.is_empty() && observed_tokens.iter().any(|token| !allowed.contains(token)) {
        let mut allowed_fields: Vec<String> = observed_fields.iter().filter(|field| allowed.contains(*field)).cloned().collect();
        if allowed_fields.is_empty() {
            allowed_fields = data.iter().filter(|field| allowed.contains(*field)).cloned().collect();
        }
        return PolicyDecision {
            action: "allow_fields".to_string(),
            reason: "destination allowlist excluded fields".to_string(),
            policy_version: Some(policy.version),
            fields: sorted_unique(&allowed_fields),
        };
    }

    PolicyDecision {
        action: "allow".to_string(),
        reason: "destination declared and data allowed".to_string(),
        policy_version: Some(policy.version),
        fields: observed_fields,
    }
}

pub fn classify_json(value: &Value) -> Vec<String> {
    let mut classes = BTreeSet::new();
    classify_json_inner(value, "", &mut classes);
    classes.into_iter().collect()
}

impl Capsule {
    pub fn new(mode: impl Into<String>, policy: Policy, agent_name: impl Into<String>) -> Self {
        Self {
            mode: mode.into(),
            policy,
            agent_name: agent_name.into(),
            agent_version: "0.1.0".to_string(),
            run: Arc::new(Mutex::new(None)),
        }
    }

    pub async fn run<F, Fut, T>(&self, name: &str, body: F) -> T
    where
        F: FnOnce() -> Fut,
        Fut: Future<Output = T>,
    {
        let context = RunContext {
            run_id: format!("run_{}", safe_id(name)),
            trace_id: format!("trc_{}", safe_id(name)),
            created_at: now_string(),
            spans: vec![],
            destinations: BTreeMap::new(),
        };
        *self.run.lock().expect("run lock poisoned") = Some(context);
        body().await
    }

    pub async fn wrap_tool<F, Fut, T>(
        &self,
        component_name: &str,
        destination: Destination,
        payload: Value,
        call: F,
    ) -> Result<T, CapsuleGuardError>
    where
        F: FnOnce(Value) -> Fut,
        Fut: Future<Output = T>,
    {
        self.wrap("tool_call", component_name, destination, payload, call).await
    }

    pub async fn wrap_model<F, Fut, T>(
        &self,
        component_name: &str,
        destination: Destination,
        payload: Value,
        call: F,
    ) -> Result<T, CapsuleGuardError>
    where
        F: FnOnce(Value) -> Fut,
        Fut: Future<Output = T>,
    {
        self.wrap("model_call", component_name, destination, payload, call).await
    }

    pub fn trace(&self) -> Option<Trace> {
        let run = self.run.lock().expect("run lock poisoned").clone()?;
        Some(Trace {
            trace_schema_version: 1,
            trace_id: run.trace_id,
            run_id: run.run_id,
            agent: Agent { name: self.agent_name.clone(), version: self.agent_version.clone() },
            mode: self.mode.clone(),
            language: "rust".to_string(),
            runtime_version: "rust-stable".to_string(),
            sdk_version: SDK_VERSION.to_string(),
            created_at: run.created_at,
            spans: run.spans,
            destinations: run.destinations.into_values().collect(),
        })
    }

    async fn wrap<F, Fut, T>(
        &self,
        component_type: &str,
        component_name: &str,
        destination: Destination,
        payload: Value,
        call: F,
    ) -> Result<T, CapsuleGuardError>
    where
        F: FnOnce(Value) -> Fut,
        Fut: Future<Output = T>,
    {
        let _entered = info_span!("agent_capsule.span", component_name = component_name).entered();
        let data_classes = classify_json(&payload);
        let decision = evaluate_policy(
            &self.policy,
            Some(&destination.id),
            &destination.risk,
            &data_classes,
            &data_classes,
            &self.mode,
        );
        let start = now_string();
        let mut status = "ok".to_string();
        let mut markers = vec![];
        let result = if self.mode != "observe" && decision.action == "block" {
            status = "blocked".to_string();
            Err(CapsuleGuardError { message: decision.reason.clone() })
        } else if self.mode != "observe" && decision.action == "require_approval" {
            status = "approval_required".to_string();
            Err(CapsuleGuardError { message: decision.reason.clone() })
        } else {
            if self.mode != "observe" && decision.action == "redact" {
                status = "redacted".to_string();
                markers = decision.fields.iter().map(|field| format!("redact:{field}")).collect();
            }
            Ok(call(payload.clone()).await)
        };

        self.record(component_type, component_name, destination, payload, data_classes, decision, start, status, markers);
        result
    }

    fn record(
        &self,
        component_type: &str,
        component_name: &str,
        destination: Destination,
        payload: Value,
        data_classes: Vec<String>,
        decision: PolicyDecision,
        start: String,
        status: String,
        markers: Vec<String>,
    ) {
        let mut lock = self.run.lock().expect("run lock poisoned");
        let run = lock.as_mut().expect("Agent Capsule operation requires an active run context");
        let rule = self.policy.destinations.get(&destination.id);
        run.destinations.insert(destination.id.clone(), DestinationTrace {
            id: destination.id.clone(),
            destination_type: destination.destination_type,
            domain: destination.domain,
            provider: destination.provider,
            environment: destination.environment,
            risk: destination.risk,
            declared_in_policy: rule.is_some(),
            allowed_data_classes: rule.map(|item| item.allowed_data.clone()).unwrap_or_default(),
            observed_data_classes: data_classes.clone(),
        });
        run.spans.push(Span {
            span_id: format!("spn_{}", monotonic_id()),
            parent_span_id: None,
            component_type: component_type.to_string(),
            component_name: component_name.to_string(),
            start_time: start,
            end_time: now_string(),
            status,
            payload_size_bytes: serde_json::to_vec(&payload).map(|raw| raw.len()).unwrap_or_default(),
            token_count: None,
            content_hash: Some(content_hash(&payload)),
            data_classes,
            destination_id: Some(destination.id),
            policy_decision: decision,
            error_summary: None,
            redaction_markers: markers,
        });
    }
}

fn classify_json_inner(value: &Value, field_name: &str, classes: &mut BTreeSet<String>) {
    if let Some(data_class) = field_name_data_class(field_name) {
        classes.insert(data_class.to_string());
    }
    match value {
        Value::Array(items) => {
            for item in items {
                classify_json_inner(item, "", classes);
            }
        }
        Value::Object(map) => {
            for (key, value) in map {
                classify_json_inner(value, key, classes);
            }
        }
        _ => {}
    }
}

fn field_name_data_class(name: &str) -> Option<&'static str> {
    match name {
        "account_id" => Some("account_id"),
        "account_notes" | "claim_notes" | "notes" => Some("account_notes"),
        "api_key" => Some("secrets"),
        "customer_id" => Some("customer_identifier"),
        "document" => Some("document_text"),
        "email" => Some("email"),
        "medical_information" => Some("medical_information"),
        "policy_number" => Some("policy_number"),
        "prompt" => Some("prompt_content"),
        "support_tier" => Some("support_tier"),
        "user_id" => Some("user_identifier"),
        _ => None,
    }
}

fn classify_data_risk(data_classes: &[String]) -> &'static str {
    let mut risk = "low";
    for data_class in data_classes {
        risk = max_risk(risk, data_class_risk(data_class));
    }
    risk
}

fn classify_egress_risk(destination_risk: &str, data_classes: &[String]) -> String {
    max_risk(destination_risk, classify_data_risk(data_classes)).to_string()
}

fn data_class_risk(data_class: &str) -> &'static str {
    match data_class {
        "account_id" | "policy_number" | "incident_description" => "medium",
        "support_tier" => "low",
        "secrets" => "critical",
        "account_notes" | "address" | "claimant_name" | "customer_identifier" | "document_text" | "email" | "medical_information" | "model_output" | "prompt_content" | "tool_payload" | "user_identifier" => "high",
        _ => "medium",
    }
}

fn matched_fields(fields: &[String], data_classes: &[String], rules: &[String]) -> Vec<String> {
    let rule_set: BTreeSet<&String> = rules.iter().collect();
    sorted_unique(&fields.iter().chain(data_classes.iter()).filter(|field| rule_set.contains(*field)).cloned().collect::<Vec<_>>())
}

fn sorted_unique(values: &[String]) -> Vec<String> {
    values.iter().cloned().collect::<BTreeSet<_>>().into_iter().collect()
}

fn apply_mode(mut decision: PolicyDecision, mode: &str) -> PolicyDecision {
    if mode == "observe" && decision.action == "block" {
        decision.action = "warn".to_string();
        decision.reason = format!("observe_only: {}", decision.reason);
    }
    decision
}

fn is_high_or_critical(risk: &str) -> bool {
    risk == "high" || risk == "critical"
}

fn max_risk<'a>(a: &'a str, b: &'a str) -> &'a str {
    if risk_rank(b) > risk_rank(a) { b } else { a }
}

fn risk_rank(risk: &str) -> i32 {
    match risk {
        "low" => 0,
        "medium" => 1,
        "high" => 2,
        "critical" => 3,
        _ => 1,
    }
}

fn now_string() -> String {
    format!("{}Z", SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs())
}

fn monotonic_id() -> u128 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_nanos()
}

fn safe_id(value: &str) -> String {
    let mut output = String::new();
    let mut previous_underscore = false;
    for ch in value.to_lowercase().chars() {
        if ch.is_ascii_alphanumeric() || ch == '-' || ch == '_' {
            output.push(ch);
            previous_underscore = false;
        } else if !previous_underscore {
            output.push('_');
            previous_underscore = true;
        }
    }
    output.trim_matches('_').to_string()
}

fn content_hash(value: &Value) -> String {
    let raw = serde_json::to_vec(value).unwrap_or_default();
    format!("sha256:{:x}", Sha256::digest(raw))
}
