package agentcapsule

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

type conformanceFixture struct {
	Cases []struct {
		Name            string   `json:"name"`
		Policy          string   `json:"policy"`
		DestinationID   string   `json:"destination_id"`
		DestinationRisk string   `json:"destination_risk"`
		DataClasses     []string `json:"data_classes"`
		Fields          []string `json:"fields"`
		Expected        struct {
			Action string   `json:"action"`
			Fields []string `json:"fields"`
			Reason string   `json:"reason"`
		} `json:"expected"`
	} `json:"cases"`
}

type claimPayload struct {
	AccountID    string `json:"account_id" capsule:"account_id"`
	Email        string `json:"email" capsule:"email"`
	AccountNotes string `json:"account_notes" capsule:"account_notes"`
}

func TestSharedPolicyDecisionFixtures(t *testing.T) {
	root := filepath.Join("..")
	raw, err := os.ReadFile(filepath.Join(root, "fixtures", "conformance", "policy-decisions.json"))
	if err != nil {
		t.Fatal(err)
	}
	var fixture conformanceFixture
	if err := json.Unmarshal(raw, &fixture); err != nil {
		t.Fatal(err)
	}
	for _, item := range fixture.Cases {
		policy, err := LoadPolicyFile(filepath.Join(root, item.Policy))
		if err != nil {
			t.Fatal(err)
		}
		decision := EvaluatePolicy(policy, item.DestinationID, item.DestinationRisk, item.DataClasses, item.Fields, "guard")
		if decision.Action != item.Expected.Action {
			t.Fatalf("%s action = %s", item.Name, decision.Action)
		}
		if got := join(decision.Fields); got != join(item.Expected.Fields) {
			t.Fatalf("%s fields = %s", item.Name, got)
		}
		if decision.Reason != item.Expected.Reason {
			t.Fatalf("%s reason = %s", item.Name, decision.Reason)
		}
	}
}

func TestContextPropagationAndWrappers(t *testing.T) {
	policy, err := LoadPolicyFile(filepath.Join("..", "fixtures", "policies", "crm-policy.json"))
	if err != nil {
		t.Fatal(err)
	}
	domain := "api.crm.example"
	capsule := NewCapsule("guard", policy, "claims-triage")
	tool := capsule.WrapTool("crm.upsert_account", Destination{
		ID:       "crm",
		Type:     "external_tool",
		Domain:   &domain,
		Provider: "Example CRM",
		Risk:     "high",
	}, func(ctx context.Context, payload any) (any, error) {
		return map[string]bool{"ok": true}, nil
	})
	err = capsule.Run(context.Background(), "phase13-go", func(ctx context.Context) error {
		_, err := tool(ctx, claimPayload{AccountID: "acct_123", Email: "claimant@example.com", AccountNotes: "Sensitive note"})
		return err
	})
	if err != nil {
		t.Fatal(err)
	}
	trace, err := capsule.Trace()
	if err != nil {
		t.Fatal(err)
	}
	if trace.Language != "go" || len(trace.Spans) != 1 {
		t.Fatalf("unexpected trace shape: %#v", trace)
	}
	if trace.Spans[0].PolicyDecision.Action != "redact" || trace.Spans[0].Status != "redacted" {
		t.Fatalf("unexpected policy decision: %#v", trace.Spans[0].PolicyDecision)
	}
}

func TestGuardBlocksUndeclaredHighRiskEgress(t *testing.T) {
	policy, err := LoadPolicyFile(filepath.Join("..", "fixtures", "policies", "restrictive-policy.json"))
	if err != nil {
		t.Fatal(err)
	}
	domain := "api.ocr.example"
	capsule := NewCapsule("guard", policy, "claims-triage")
	tool := capsule.WrapTool("external_ocr.extract", Destination{
		ID:       "external_ocr",
		Type:     "external_tool",
		Domain:   &domain,
		Provider: "Example OCR",
		Risk:     "high",
	}, func(ctx context.Context, payload any) (any, error) {
		return map[string]bool{"ok": true}, nil
	})
	err = capsule.Run(context.Background(), "blocked-go", func(ctx context.Context) error {
		_, err := tool(ctx, map[string]string{
			"document":            "private document",
			"medical_information": "private diagnosis",
		})
		return err
	})
	if !errors.Is(err, ErrPolicyViolation) {
		t.Fatalf("expected policy violation, got %v", err)
	}
	trace, err := capsule.Trace()
	if err != nil {
		t.Fatal(err)
	}
	if trace.Spans[0].Status != "blocked" {
		t.Fatalf("expected blocked span, got %s", trace.Spans[0].Status)
	}
}

func join(values []string) string {
	raw, _ := json.Marshal(values)
	return string(raw)
}
