import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const problems = [
  {
    title: "Private agent runs are hard to inspect",
    body: "Teams need timing, errors, policy decisions, and dependency evidence without copying private prompts or payloads into a third-party tool."
  },
  {
    title: "Privacy review often happens too late",
    body: "New tools and model providers can be added quickly, while policy review still depends on manual notes and screenshots."
  },
  {
    title: "Enterprise demos need proof",
    body: "Prospects want to see what runs, where data can leave, how secrets are handled, and what evidence exists before they share private evaluation data."
  }
];

const workflows = [
  {
    label: "Observe",
    title: "Capture safe metadata",
    body: "Run agents with encrypted local payloads and safe trace metadata for workflow structure, timing, token counts, destinations, and policy decisions."
  },
  {
    label: "Guard",
    title: "Enforce egress policy",
    body: "Block, redact, allow selected fields, or require approval before supported model and tool calls leave the agent boundary."
  },
  {
    label: "Confidential",
    title: "Prepare private demos",
    body: "Use signed manifests, runtime verification, attestation evidence, and secret release receipts for customer proof-of-concept flows."
  }
];

const languages = [
  ["Python", "Observe and Guard Mode SDK"],
  ["TypeScript", "Async context and Zod annotations"],
  ["Java", "Builder configuration and annotations"],
  ["Go", "Context propagation and struct tags"],
  ["Rust", "Tracing integration and serde classification"]
];

const hardware = [
  {
    title: "Local development",
    body: "No specialized local hardware is required for Observe mode, Guard Mode, local encrypted traces, replay, safe trace export, CI checks, or the local confidential-like demo path."
  },
  {
    title: "Hosted confidential demos",
    body: "A supported cloud confidential-computing environment, attestation service, and integrated secrets provider or key-management service are required for a hosted private demonstration."
  },
  {
    title: "Agent workload sizing",
    body: "Agent Capsule overhead is intended to be small relative to model and tool latency. Local model, OCR, retrieval, and data-processing workloads define their own hardware needs."
  },
  {
    title: "Enterprise runtime evidence",
    body: "Release-style workflows require signed manifests, concrete runtime versions, declared destinations, and policy evidence that can be reviewed in version control."
  }
];

const evidence = [
  {
    title: "Signed manifest",
    body: "Agent identity, runtime version, dependency hashes, prompt hashes, tool schema hashes, model configuration, required secret names, and usage meters."
  },
  {
    title: "Policy file",
    body: "Approved destinations, allowed data classes, redaction rules, approval rules, and defaults for undeclared high-risk egress."
  },
  {
    title: "Attestation result",
    body: "Provider status, evidence hash, manifest hash, runtime language, runtime version, and verification reasons."
  },
  {
    title: "Safe telemetry",
    body: "Health, timing, error class, token counts, payload sizes, policy decisions, and usage metadata without plaintext sensitive payloads."
  }
];

export default function Home() {
  return (
    <main className="site-shell">
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="#top" aria-label="Agent Capsule home">
            Agent Capsule
          </a>
          <nav className="nav-list" aria-label="Primary navigation">
            <a href="#workflows">Workflows</a>
            <a href="#privacy-review">Privacy review</a>
            <a href="#demo">Confidential demo</a>
            <a href="#evidence">Evidence</a>
          </nav>
          <div className="header-action">
            <Button asChild variant="outline">
              <a href="#hardware">Runtime requirements</a>
            </Button>
          </div>
        </div>
      </header>

      <section id="top" className="hero-band">
        <div className="hero-inner">
          <div className="hero-copy">
            <p className="eyebrow">Private agent SDK and evidence workflow</p>
            <h1>Agent Capsule</h1>
            <p>
              Debug, review, and demonstrate AI agents with encrypted traces, explicit egress policy,
              safe collaboration artifacts, and signed runtime evidence.
            </p>
            <div className="hero-actions">
              <Button asChild>
                <a href="#evidence">Review evidence</a>
              </Button>
              <Button asChild variant="outline">
                <a href="#privacy-review">Policy workflow</a>
              </Button>
            </div>
          </div>
          <ProductEvidence />
        </div>
      </section>

      <section className="section-band alt" aria-labelledby="problem-heading">
        <div className="section-inner">
          <div className="section-heading">
            <p className="section-label">Problem</p>
            <h2 id="problem-heading">Agent teams need operational visibility without creating another data exposure path.</h2>
            <p>
              Agent Capsule treats privacy behavior as engineering evidence: traces stay private by default,
              policy changes are reviewable, and customer demos can be prepared from signed artifacts.
            </p>
          </div>
          <div className="problem-grid">
            {problems.map((item) => (
              <section className="info-panel" key={item.title}>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </section>
            ))}
          </div>
        </div>
      </section>

      <section id="workflows" className="section-band" aria-labelledby="workflow-heading">
        <div className="section-inner">
          <div className="section-heading">
            <p className="section-label">Observe, Guard, Confidential</p>
            <h2 id="workflow-heading">A staged workflow for development, policy enforcement, and customer proof of concept.</h2>
            <p>
              Start by observing safe metadata, move to policy enforcement when behavior is understood,
              then prepare signed evidence for a private enterprise evaluation.
            </p>
          </div>
          <div className="workflow-grid">
            {workflows.map((item) => (
              <section className="workflow-step" key={item.title}>
                <span>{item.label}</span>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </section>
            ))}
          </div>
        </div>
      </section>

      <section id="privacy-review" className="section-band alt" aria-labelledby="privacy-heading">
        <div className="section-inner">
          <div className="section-heading">
            <p className="section-label">Privacy review</p>
            <h2 id="privacy-heading">Data-flow visibility that fits pull request review.</h2>
            <p>
              Observe mode detects destinations and data classes. CI checks block undeclared high-risk egress
              before the change can merge.
            </p>
          </div>
          <div className="review-table" role="table" aria-label="Privacy review example">
            <div className="review-table-row" role="row">
              <div role="columnheader">Destination</div>
              <div role="columnheader">Observed data</div>
              <div role="columnheader">Policy status</div>
              <div role="columnheader">Developer action</div>
            </div>
            <div className="review-table-row" role="row">
              <div role="cell">api.crm.example</div>
              <div role="cell">email, account notes</div>
              <div role="cell">Not declared</div>
              <div role="cell">Redact fields or require approval</div>
            </div>
            <div className="review-table-row" role="row">
              <div role="cell">api.model.example</div>
              <div role="cell">prompt content, document text</div>
              <div role="cell">Declared</div>
              <div role="cell">Allow under model provider rule</div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-band" aria-labelledby="safe-trace-heading">
        <div className="section-inner">
          <div className="section-heading">
            <p className="section-label">Safe trace collaboration</p>
            <h2 id="safe-trace-heading">Share enough context to diagnose a run without exposing the run payloads.</h2>
            <p>
              Safe traces retain workflow structure, timings, component versions, token counts, payload sizes,
              error summaries, policy decisions, hashes, and redaction markers.
            </p>
          </div>
          <div className="trace-visual">
            <div className="trace-summary">
              <div className="metric-row">
                <span>Failure class</span>
                <p>ModelTimeout</p>
              </div>
              <div className="metric-row">
                <span>Payload handling</span>
                <p>Hashed and redacted</p>
              </div>
              <div className="metric-row">
                <span>Support view</span>
                <p>Safe metadata only</p>
              </div>
            </div>
            <div className="evidence-surface">
              <div className="evidence-header">
                <div className="evidence-title">
                  <span>Safe trace</span>
                  <p>run_failed_model_001</p>
                </div>
                <Badge>team_debug profile</Badge>
              </div>
              <div className="evidence-column">
                <div className="trace-row">
                  <span>Workflow node</span>
                  <p>claim-triage</p>
                </div>
                <div className="trace-row">
                  <span>Model call</span>
                  <p>classify-claim, 1024 tokens</p>
                </div>
                <div className="trace-row">
                  <span>Content evidence</span>
                  <p>sha256 hash, redaction markers</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="demo" className="section-band alt" aria-labelledby="demo-heading">
        <div className="section-inner">
          <div className="section-heading">
            <p className="section-label">Confidential customer demonstration</p>
            <h2 id="demo-heading">Prepare a private proof of concept from signed evidence.</h2>
            <p>
              Demo creation checks the signed manifest, policy, traces, runtime, attestation evidence, and
              required secret names before producing customer and vendor artifacts.
            </p>
          </div>
          <div className="demo-panel">
            <section className="demo-artifact">
              <h3>Customer verification page</h3>
              <p>
                Shows capsule identity, attestation status, approved model providers, approved tools,
                destinations, policy version, and data classes that may leave the environment.
              </p>
            </section>
            <section className="demo-artifact">
              <h3>Vendor telemetry</h3>
              <p>
                Shows health, timing, error class, token count, payload size, policy decision, and usage
                metadata without plaintext prompts, documents, tool payloads, outputs, secrets, or identifiers.
              </p>
            </section>
          </div>
        </div>
      </section>

      <section className="section-band" aria-labelledby="language-heading">
        <div className="section-inner">
          <div className="section-heading">
            <p className="section-label">Multi-language SDK support</p>
            <h2 id="language-heading">Shared semantics across the agent runtime stack.</h2>
            <p>
              The SDK beta keeps policy decisions and safe trace shapes aligned across the languages
              most often used in enterprise agent services.
            </p>
          </div>
          <div className="language-grid">
            {languages.map(([name, body]) => (
              <section className="language-item" key={name}>
                <h3>{name}</h3>
                <p>{body}</p>
              </section>
            ))}
          </div>
        </div>
      </section>

      <section id="hardware" className="section-band alt" aria-labelledby="hardware-heading">
        <div className="section-inner">
          <div className="section-heading">
            <p className="section-label">Hardware requirements</p>
            <h2 id="hardware-heading">Local development does not require specialized hardware.</h2>
            <p>
              Agent Capsule itself does not require a GPU, TPM, Secure Enclave, or local HSM for the
              MVP developer workflow. Hosted confidential demos have separate cloud requirements.
            </p>
          </div>
          <div className="hardware-grid">
            {hardware.map((item) => (
              <section className="hardware-item" key={item.title}>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </section>
            ))}
          </div>
        </div>
      </section>

      <section id="evidence" className="section-band" aria-labelledby="evidence-heading">
        <div className="section-inner">
          <div className="section-heading">
            <p className="section-label">Enterprise evidence</p>
            <h2 id="evidence-heading">Artifacts an enterprise reviewer can inspect before private evaluation data is used.</h2>
            <p>
              Agent Capsule packages runtime, policy, destination, attestation, and telemetry evidence into
              artifacts designed for engineering and security review.
            </p>
          </div>
          <div className="evidence-grid-section">
            {evidence.map((item) => (
              <section className="evidence-item" key={item.title}>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </section>
            ))}
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="section-inner">
          <p>Agent Capsule</p>
          <p>Private debugging, policy review, safe traces, and confidential demonstration workflows.</p>
        </div>
      </footer>
    </main>
  );
}

function ProductEvidence() {
  return (
    <section className="evidence-surface" aria-label="Agent Capsule product evidence visual">
      <div className="evidence-header">
        <div className="evidence-title">
          <span>Capsule evidence</span>
          <p>claims-triage 0.1.0</p>
        </div>
        <div className="status-line" aria-label="Evidence status">
          <Badge>policy version 1</Badge>
          <Badge>signature present</Badge>
          <Badge>attestation verified</Badge>
        </div>
      </div>
      <div className="evidence-grid">
        <div className="evidence-column">
          <div className="trace-row">
            <span>Trace</span>
            <p>run_failed_model_001</p>
          </div>
          <div className="trace-row">
            <span>Model call</span>
            <p>classify-claim, timeout after 30 seconds</p>
          </div>
          <div className="trace-row">
            <span>Payload policy</span>
            <p>hashes retained, plaintext excluded</p>
          </div>
        </div>
        <div className="evidence-column">
          <div className="policy-row">
            <span>Policy decision</span>
            <p>crm.upsert_account redacts email and account notes</p>
          </div>
          <div className="policy-row">
            <span>Pull request gate</span>
            <p>undeclared high-risk egress blocks merge</p>
          </div>
          <div className="policy-row">
            <span>Safe trace</span>
            <p>workflow, timing, versions, errors, tokens, sizes</p>
          </div>
        </div>
        <div className="evidence-column">
          <div className="destination-row">
            <span>Destination</span>
            <p>api.model.example, declared</p>
          </div>
          <div className="destination-row">
            <span>Destination</span>
            <p>api.crm.example, redaction required</p>
          </div>
          <div className="destination-row">
            <span>Secret release</span>
            <p>receipt hash after runtime verification</p>
          </div>
        </div>
      </div>
    </section>
  );
}
