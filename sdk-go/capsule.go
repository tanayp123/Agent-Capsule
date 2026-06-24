package agentcapsule

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"runtime"
	"strings"
	"time"
)

const SDKVersion = "0.1.0-beta.1"

type Capsule struct {
	Mode         string
	Policy       Policy
	AgentName    string
	AgentVersion string
	lastRun       *runContext
}

type Destination struct {
	ID          string
	Type        string
	Domain      *string
	Provider    string
	Environment string
	Risk        string
}

type ToolFunc func(context.Context, any) (any, error)

type contextKey struct{}

type runContext struct {
	runID        string
	traceID      string
	createdAt    string
	spans        []Span
	destinations map[string]DestinationTrace
}

type Trace struct {
	TraceSchemaVersion int                `json:"trace_schema_version"`
	TraceID            string             `json:"trace_id"`
	RunID              string             `json:"run_id"`
	Agent              Agent              `json:"agent"`
	Mode               string             `json:"mode"`
	Language           string             `json:"language"`
	RuntimeVersion     string             `json:"runtime_version"`
	SDKVersion         string             `json:"sdk_version"`
	CreatedAt          string             `json:"created_at"`
	Spans              []Span             `json:"spans"`
	Destinations       []DestinationTrace `json:"destinations"`
}

type Agent struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

type Span struct {
	SpanID           string         `json:"span_id"`
	ParentSpanID     *string        `json:"parent_span_id"`
	ComponentType    string         `json:"component_type"`
	ComponentName    string         `json:"component_name"`
	StartTime        string         `json:"start_time"`
	EndTime          string         `json:"end_time"`
	Status           string         `json:"status"`
	PayloadSizeBytes int            `json:"payload_size_bytes"`
	TokenCount       *int           `json:"token_count"`
	ContentHash      string         `json:"content_hash"`
	DataClasses      []string       `json:"data_classes"`
	DestinationID    *string        `json:"destination_id"`
	PolicyDecision   PolicyDecision `json:"policy_decision"`
	ErrorSummary     any            `json:"error_summary"`
	RedactionMarkers []string       `json:"redaction_markers"`
}

type DestinationTrace struct {
	ID                  string   `json:"id"`
	Type                string   `json:"type"`
	Domain              *string  `json:"domain"`
	Provider            string   `json:"provider"`
	Environment         string   `json:"environment"`
	Risk                string   `json:"risk"`
	DeclaredInPolicy    bool     `json:"declared_in_policy"`
	AllowedDataClasses  []string `json:"allowed_data_classes"`
	ObservedDataClasses []string `json:"observed_data_classes"`
}

var ErrPolicyViolation = errors.New("agent capsule policy violation")

func NewCapsule(mode string, policy Policy, agentName string) *Capsule {
	return &Capsule{Mode: mode, Policy: policy, AgentName: agentName, AgentVersion: "0.1.0"}
}

func (c *Capsule) Run(ctx context.Context, name string, body func(context.Context) error) error {
	run := &runContext{
		runID:        "run_" + safeID(name),
		traceID:      "trc_" + safeID(name),
		createdAt:    time.Now().UTC().Format(time.RFC3339),
		destinations: map[string]DestinationTrace{},
	}
	c.lastRun = run
	ctx = context.WithValue(ctx, contextKey{}, run)
	return body(ctx)
}

func (c *Capsule) WrapTool(componentName string, destination Destination, call ToolFunc) ToolFunc {
	return c.wrap("tool_call", componentName, destination, call)
}

func (c *Capsule) WrapModel(componentName string, destination Destination, call ToolFunc) ToolFunc {
	return c.wrap("model_call", componentName, destination, call)
}

func (c *Capsule) Trace() (Trace, error) {
	if c.lastRun == nil {
		return Trace{}, errors.New("no run has completed")
	}
	destinations := []DestinationTrace{}
	for _, destination := range c.lastRun.destinations {
		destinations = append(destinations, destination)
	}
	return Trace{
		TraceSchemaVersion: 1,
		TraceID:            c.lastRun.traceID,
		RunID:              c.lastRun.runID,
		Agent:              Agent{Name: c.AgentName, Version: c.AgentVersion},
		Mode:               c.Mode,
		Language:           "go",
		RuntimeVersion:     runtime.Version(),
		SDKVersion:         SDKVersion,
		CreatedAt:          c.lastRun.createdAt,
		Spans:              c.lastRun.spans,
		Destinations:       destinations,
	}, nil
}

func (c *Capsule) wrap(componentType string, componentName string, destination Destination, call ToolFunc) ToolFunc {
	return func(ctx context.Context, payload any) (any, error) {
		run, ok := ctx.Value(contextKey{}).(*runContext)
		if !ok || run == nil {
			return nil, errors.New("Agent Capsule operation requires an active run context")
		}
		dataClasses := ClassifyPayload(payload)
		decision := EvaluatePolicy(c.Policy, destination.ID, destination.Risk, dataClasses, dataClasses, c.Mode)
		start := time.Now().UTC().Format(time.RFC3339)
		status := "ok"
		markers := []string{}
		var result any
		var err error

		if c.Mode != "observe" && decision.Action == "block" {
			status = "blocked"
			err = fmt.Errorf("%w: %s", ErrPolicyViolation, decision.Reason)
		} else if c.Mode != "observe" && decision.Action == "require_approval" {
			status = "approval_required"
			err = fmt.Errorf("%w: %s", ErrPolicyViolation, decision.Reason)
		} else {
			if c.Mode != "observe" && decision.Action == "redact" {
				status = "redacted"
				for _, field := range decision.Fields {
					markers = append(markers, "redact:"+field)
				}
			}
			result, err = call(ctx, payload)
			if err != nil && status == "ok" {
				status = "error"
			}
		}

		c.recordDestination(run, destination, dataClasses)
		c.recordSpan(run, componentType, componentName, start, status, payload, dataClasses, destination.ID, decision, markers)
		return result, err
	}
}

func (c *Capsule) recordDestination(run *runContext, destination Destination, observed []string) {
	rule, declared := c.Policy.Destinations[destination.ID]
	environment := destination.Environment
	if environment == "" {
		environment = "production"
	}
	run.destinations[destination.ID] = DestinationTrace{
		ID:                  destination.ID,
		Type:                destination.Type,
		Domain:              destination.Domain,
		Provider:            destination.Provider,
		Environment:         environment,
		Risk:                destination.Risk,
		DeclaredInPolicy:    declared,
		AllowedDataClasses:  append([]string{}, rule.AllowedData...),
		ObservedDataClasses: observed,
	}
}

func (c *Capsule) recordSpan(run *runContext, componentType string, componentName string, start string, status string, payload any, dataClasses []string, destinationID string, decision PolicyDecision, markers []string) {
	run.spans = append(run.spans, Span{
		SpanID:           "spn_" + strings.ReplaceAll(fmt.Sprintf("%d", time.Now().UnixNano()), "-", ""),
		ParentSpanID:     nil,
		ComponentType:    componentType,
		ComponentName:    componentName,
		StartTime:        start,
		EndTime:          time.Now().UTC().Format(time.RFC3339),
		Status:           status,
		PayloadSizeBytes: payloadSize(payload),
		TokenCount:       nil,
		ContentHash:      contentHash(payload),
		DataClasses:      dataClasses,
		DestinationID:    &destinationID,
		PolicyDecision:   decision,
		ErrorSummary:     nil,
		RedactionMarkers: markers,
	})
}

func contentHash(value any) string {
	raw, _ := json.Marshal(value)
	sum := sha256.Sum256(raw)
	return "sha256:" + hex.EncodeToString(sum[:])
}

func payloadSize(value any) int {
	raw, _ := json.Marshal(value)
	return len(raw)
}

func safeID(value string) string {
	lower := strings.ToLower(value)
	builder := strings.Builder{}
	previousUnderscore := false
	for _, char := range lower {
		ok := (char >= 'a' && char <= 'z') || (char >= '0' && char <= '9') || char == '-' || char == '_'
		if ok {
			builder.WriteRune(char)
			previousUnderscore = false
		} else if !previousUnderscore {
			builder.WriteRune('_')
			previousUnderscore = true
		}
	}
	return strings.Trim(builder.String(), "_")
}
