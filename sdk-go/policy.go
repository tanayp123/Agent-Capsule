package agentcapsule

import (
	"encoding/json"
	"os"
	"sort"
)

type Policy struct {
	Version      int                        `json:"version"`
	Agent        map[string]string          `json:"agent"`
	Destinations map[string]DestinationRule `json:"destinations"`
	Defaults     Defaults                   `json:"defaults"`
}

type DestinationRule struct {
	Type            string   `json:"type"`
	Domain          *string  `json:"domain"`
	Risk            string   `json:"risk"`
	AllowedData     []string `json:"allowed_data"`
	Redact          []string `json:"redact"`
	RequireApproval []string `json:"require_approval"`
}

type Defaults struct {
	UndeclaredHighRiskEgress string `json:"undeclared_high_risk_egress"`
	UndeclaredDestination    string `json:"undeclared_destination"`
	Secrets                  string `json:"secrets"`
}

type PolicyDecision struct {
	Action        string   `json:"action"`
	Reason        string   `json:"reason"`
	PolicyVersion *int     `json:"policy_version"`
	Fields        []string `json:"fields"`
}

func LoadPolicyFile(path string) (Policy, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return Policy{}, err
	}
	var policy Policy
	if err := json.Unmarshal(raw, &policy); err != nil {
		return Policy{}, err
	}
	return policy, nil
}

func EvaluatePolicy(policy Policy, destinationID string, destinationRisk string, dataClasses []string, fields []string, mode string) PolicyDecision {
	data := sortedUnique(dataClasses)
	observedFields := sortedUnique(fields)
	if len(observedFields) == 0 {
		observedFields = data
	}
	observedTokens := map[string]bool{}
	for _, item := range data {
		observedTokens[item] = true
	}
	for _, item := range observedFields {
		observedTokens[item] = true
	}
	version := policy.Version

	if destinationID == "" {
		return PolicyDecision{Action: "not_evaluated", Reason: "no destination", PolicyVersion: &version, Fields: []string{}}
	}
	if observedTokens["secrets"] {
		return applyMode(PolicyDecision{Action: policy.Defaults.Secrets, Reason: "secrets default rule matched", PolicyVersion: &version, Fields: observedFields}, mode)
	}

	destination, declared := policy.Destinations[destinationID]
	egressRisk := ClassifyEgressRisk(destinationRisk, data)
	if !declared {
		if isHighOrCritical(egressRisk) {
			return applyMode(PolicyDecision{Action: policy.Defaults.UndeclaredHighRiskEgress, Reason: "undeclared high-risk egress", PolicyVersion: &version, Fields: observedFields}, mode)
		}
		return applyMode(PolicyDecision{Action: policy.Defaults.UndeclaredDestination, Reason: "undeclared destination", PolicyVersion: &version, Fields: observedFields}, mode)
	}

	if approvalFields := matchedFields(observedFields, data, destination.RequireApproval); len(approvalFields) > 0 {
		return PolicyDecision{Action: "require_approval", Reason: "destination approval rule matched", PolicyVersion: &version, Fields: approvalFields}
	}
	if redactionFields := matchedFields(observedFields, data, destination.Redact); len(redactionFields) > 0 {
		return PolicyDecision{Action: "redact", Reason: "destination redaction rule matched", PolicyVersion: &version, Fields: redactionFields}
	}

	allowed := set(destination.AllowedData)
	if len(allowed) > 0 {
		for token := range observedTokens {
			if !allowed[token] {
				allowedFields := []string{}
				for _, field := range observedFields {
					if allowed[field] {
						allowedFields = append(allowedFields, field)
					}
				}
				if len(allowedFields) == 0 {
					for _, dataClass := range data {
						if allowed[dataClass] {
							allowedFields = append(allowedFields, dataClass)
						}
					}
				}
				return PolicyDecision{Action: "allow_fields", Reason: "destination allowlist excluded fields", PolicyVersion: &version, Fields: sortedUnique(allowedFields)}
			}
		}
	}

	return PolicyDecision{Action: "allow", Reason: "destination declared and data allowed", PolicyVersion: &version, Fields: observedFields}
}

func ClassifyDataRisk(dataClasses []string) string {
	risk := "low"
	for _, dataClass := range dataClasses {
		candidate := dataClassRisk[dataClass]
		if candidate == "" {
			candidate = "medium"
		}
		risk = maxRisk(risk, candidate)
	}
	return risk
}

func ClassifyEgressRisk(destinationRisk string, dataClasses []string) string {
	if destinationRisk == "" {
		destinationRisk = "medium"
	}
	return maxRisk(destinationRisk, ClassifyDataRisk(dataClasses))
}

func applyMode(decision PolicyDecision, mode string) PolicyDecision {
	if mode == "observe" && decision.Action == "block" {
		decision.Action = "warn"
		decision.Reason = "observe_only: " + decision.Reason
	}
	return decision
}

func matchedFields(fields []string, dataClasses []string, rules []string) []string {
	ruleSet := set(rules)
	matched := []string{}
	for _, field := range fields {
		if ruleSet[field] {
			matched = append(matched, field)
		}
	}
	for _, dataClass := range dataClasses {
		if ruleSet[dataClass] {
			matched = append(matched, dataClass)
		}
	}
	return sortedUnique(matched)
}

func sortedUnique(values []string) []string {
	seen := map[string]bool{}
	output := []string{}
	for _, value := range values {
		if !seen[value] {
			seen[value] = true
			output = append(output, value)
		}
	}
	sort.Strings(output)
	return output
}

func set(values []string) map[string]bool {
	output := map[string]bool{}
	for _, value := range values {
		output[value] = true
	}
	return output
}

func isHighOrCritical(risk string) bool {
	return risk == "high" || risk == "critical"
}

func maxRisk(a string, b string) string {
	ai := riskRank[a]
	bi := riskRank[b]
	if bi > ai {
		return b
	}
	return a
}

var riskRank = map[string]int{"low": 0, "medium": 1, "high": 2, "critical": 3}
var dataClassRisk = map[string]string{
	"account_id":          "medium",
	"account_notes":       "high",
	"address":             "high",
	"claimant_name":       "high",
	"customer_identifier": "high",
	"document_text":       "high",
	"email":               "high",
	"incident_description": "medium",
	"medical_information": "high",
	"model_output":        "high",
	"policy_number":       "medium",
	"prompt_content":      "high",
	"secrets":             "critical",
	"support_tier":        "low",
	"tool_payload":        "high",
	"user_identifier":     "high",
}
