# Agent Identity Governance: An Accountability Framework for Autonomous AI Agents

**Submission to NIST Request for Information on AI Accountability and Transparency**

---

**Submitted by:** Jun M  
**Date:** February 2026  
**Category:** Technical Framework with Working Implementation  
**Contact:** [LinkedIn] | [GitHub]

---

## Abstract

Autonomous AI agents represent a new class of computational principal that existing accountability frameworks were not designed to handle. Unlike traditional software services, agents spawn dynamically, delegate authority to sub-agents, operate without continuous human oversight, and make decisions across organizational boundaries. Current Identity and Access Management (IAM) systems cannot answer fundamental accountability questions: "Which agent performed this action?" and "Who authorized it?"

This submission proposes **Agent Identity Governance**—a framework providing explicit agent identity, delegation chain tracking, and audit trails that trace all agent actions back to human authority. We demonstrate feasibility with a working proof-of-concept implementation, deployed and publicly accessible.

**Keywords:** AI governance, agent identity, autonomous systems, accountability, delegation, audit trail

---

## 1. Introduction

### 1.1 The Emergence of Autonomous Agents

The deployment of autonomous AI agents in enterprise environments has accelerated dramatically. Organizations now deploy agents for customer service, code generation, data analysis, security monitoring, and operational automation. These agents increasingly operate with minimal human oversight, making decisions and taking actions independently.

A defining characteristic of modern agent architectures is **agent spawning**—the ability of one agent to create sub-agents to accomplish tasks. A data analysis agent might spawn a database query agent, which spawns a visualization agent, creating chains of autonomous actors operating on behalf of a distant human authorizer.

### 1.2 The Accountability Gap

This proliferation creates an accountability gap that existing governance frameworks cannot address:

| Traditional Assumption | Agent Reality |
|------------------------|---------------|
| Principals are static (humans, services) | Agents spawn dynamically, exist temporarily |
| Actions trace to human operators | Agents operate autonomously, decisions may be hours from human involvement |
| API credentials identify actors | Multiple agents share credentials; logs show "key X" not "agent Y" |
| Access control is human-centric | Agents delegate authority to sub-agents without human review |

When a compliance officer asks "Who authorized this database access?", current systems can only answer "API key prod-ai-service." They cannot identify which agent, created by whom, operating under what authority, performed the action.

### 1.3 Regulatory Imperatives

Multiple regulatory frameworks now require accountability mechanisms that assume we can identify AI actors:

- **NIST AI Risk Management Framework (AI RMF):** The Govern function requires mechanisms for accountability, but does not specify identity infrastructure for autonomous agents.
- **EU AI Act (Article 12):** High-risk AI systems must maintain logs sufficient for traceability—impossible without agent identity.
- **APRA CPS 230/234 (Australia):** Operational resilience and information security standards require audit trails that identify principals.
- **ISO/IEC 42001:** AI management systems require documented accountability—again assuming identifiable actors.

The gap is clear: regulations demand "who is accountable?" but provide no technical mechanism to answer it for autonomous agents.

### 1.4 Our Contribution

This submission proposes **Agent Identity Governance**, a framework that provides:

1. **Explicit Agent Identity:** Every agent receives unique, traceable identity—not shared API keys
2. **Delegation Chain Tracking:** When Agent A spawns Agent B, the relationship is recorded
3. **Scope Attenuation:** Child agents cannot exceed parent permissions
4. **Audit Trails:** Every action logs the agent ID and traces to human authority
5. **Lifecycle Management:** Agents have explicit states (active, suspended, terminated)

We provide a **working proof-of-concept** demonstrating these concepts are implementable with existing technology.

---

## 2. Framework Specification

### 2.1 Agent Identity Registry

The core component is a registry that maintains identity records for all agents:

```
Agent Identity Record
├── agent_id          Unique identifier (e.g., "agent_4e5f93b4a829bc4c")
├── agent_name        Human-readable name
├── agent_type        Classification: autonomous | semi-autonomous | tool
├── created_at        Timestamp of creation
├── created_by        Human ID or parent agent ID
├── authority_source  Origin of authority: human | delegated | policy
├── scope             Array of permitted actions
├── lifecycle_state   Current state: active | suspended | terminated
└── credentials       Authentication material (API key, certificate, etc.)
```

**Design Principle:** Agents are first-class principals, not anonymous API consumers. Every agent action is attributable to a specific, traceable identity.

### 2.2 Delegation Model

When an agent creates a sub-agent, the system records an explicit delegation relationship:

```
Delegation Record
├── delegation_id     Unique identifier
├── parent_id         Creating agent's ID
├── child_id          Created agent's ID  
├── delegated_at      Timestamp
└── delegation_depth  Distance from human authority (0 = direct human authorization)
```

**Scope Attenuation Rule:** A child agent's scope must be a subset of its parent's scope. This prevents privilege escalation through delegation chains.

```
Example:
  Human Alice authorizes Agent A with scope: [read:database, write:reports, create:charts]
  
  Agent A spawns Agent B with scope: [write:reports]           ✓ Valid (subset)
  Agent B spawns Agent C with scope: [write:reports]           ✓ Valid (subset of B)
  Agent B spawns Agent D with scope: [read:database]           ✗ Invalid (not in B's scope)
```

**Human Ultimate Authority:** All delegation chains terminate at a human authorizer. Forensic queries can always answer: "Which human authorized this agent?"

### 2.3 Audit Trail

Every agent action generates an audit record:

```
Audit Record
├── log_id            Unique identifier
├── agent_id          Acting agent's ID
├── action            Action performed (e.g., "read:database")
├── resource          Resource accessed (e.g., "customers_table")
├── timestamp         When the action occurred
├── human_authority   Traced human authorizer
├── success           Whether the action succeeded
└── metadata          Additional context (optional)
```

**Key Innovation:** The `human_authority` field is computed by traversing the delegation chain, not stored at action time. This ensures the trail is always accurate even if delegation relationships are later discovered to be compromised.

### 2.4 Lifecycle States

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Provisioned │────▶│   Active    │────▶│  Suspended  │────▶│ Terminated  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       │                   │                   │                   │
    Identity            Normal              Incident           Credentials
    issued            operation            response            revoked,
                                                              audit sealed
```

**Cascade Termination:** When a parent agent is terminated, all child agents are automatically terminated. This prevents orphaned agents with stale authority.

### 2.5 Forensic Queries

The framework enables forensic queries that current systems cannot answer:

| Query | Capability |
|-------|-----------|
| "Who authorized Agent X?" | Traverse delegation chain to human |
| "What has Agent X done?" | Retrieve all audit records for agent |
| "Show all actions by agents created today" | Filter by creation timestamp |
| "Which agents accessed resource Y?" | Filter audit log by resource |
| "Trace this API call to human authority" | Log ID → Agent ID → Delegation chain → Human |

---

## 3. Technical Implementation

### 3.1 Proof-of-Concept Architecture

We provide a working implementation demonstrating these concepts:

```
┌────────────────────────────────────────────────────────────────┐
│                     Agent Identity Registry                    │
│                         (FastAPI + SQLite)                     │
├────────────────────────────────────────────────────────────────┤
│  Endpoints:                                                    │
│  ├── POST /agents/register      Create agent, issue identity   │
│  ├── POST /agents/{id}/spawn    Delegate to sub-agent          │
│  ├── POST /audit/log            Record agent action            │
│  ├── GET  /audit/trace/{id}     Full delegation + audit trail  │
│  └── GET  /audit/query          Forensic log search            │
└────────────────────────────────────────────────────────────────┘
                              │
┌────────────────────────────────────────────────────────────────┐
│                         Database Schema                        │
│  ├── agents        Identity records                            │
│  ├── delegations   Parent-child relationships                  │
│  └── audit_log     Action records with human authority         │
└────────────────────────────────────────────────────────────────┘
```

**Technology Stack:** Python 3.12, FastAPI, SQLite, Pydantic v2

**Repository:** https://github.com/9to5ai/agent-identity-registry

### 3.2 Demonstration Scenario

Our demo script (`demo.py`) executes this scenario:

1. **Human Authorization:** Jun authorizes Agent A ("DataAnalyzer") with scope `[read:database, write:reports, create:charts]`

2. **First Delegation:** Agent A spawns Agent B ("ReportGenerator") with scope `[write:reports]`

3. **Scope Enforcement Test:** Agent B attempts to spawn Agent C with scope `[create:charts]`—**denied** because `create:charts` is not in B's scope

4. **Valid Delegation:** Agent A spawns Agent C ("ChartMaker") with scope `[create:charts]`

5. **Action Logging:** All three agents perform actions, each logged with full traceability

6. **Forensic Query:** Query Agent C's audit trace—returns complete delegation chain back to Jun

**Demo Output Excerpt:**
```
Delegation Chain:
  ├─ 👤 user:jun@apra.gov.au
  ├─ 🤖 DataAnalyzer (agent_4e5f93b4...)
  └─ 🤖 ChartMaker (agent_33f9feb3...)

✓ Every action by ChartMaker traces back to: user:jun@apra.gov.au
```

### 3.3 Implementation Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 1,598 |
| API endpoints | 10 |
| Test coverage | 8 tests, 100% pass |
| Build time | ~13 hours |
| Dependencies | 4 (FastAPI, uvicorn, pydantic, python-multipart) |

---

## 4. Alignment with Existing Standards

### 4.1 NIST AI Risk Management Framework

| RMF Function | Agent Identity Governance Support |
|--------------|-----------------------------------|
| **GOVERN** | Agent registry provides organizational accountability infrastructure; scope policies encode governance rules |
| **MAP** | Delegation chains document agent relationships, data flows, and authority boundaries |
| **MEASURE** | Audit trails enable continuous monitoring of agent behavior against expected scope |
| **MANAGE** | Lifecycle management enables rapid response; cascade termination contains incidents |

### 4.2 EU AI Act

**Article 12 (Record-keeping):** "High-risk AI systems shall be designed and developed with capabilities enabling the automatic recording of events ('logs')..."

Agent Identity Governance provides:
- Structured logs identifying specific agents (not anonymous API calls)
- Delegation chains documenting authority flows
- Lifecycle records (creation, modification, termination)
- Forensic query capability for regulatory investigation

### 4.3 Zero Trust Architecture

Agent Identity Governance extends Zero Trust principles to autonomous agents:

| Zero Trust Principle | Agent Implementation |
|---------------------|---------------------|
| Never trust, always verify | Verify agent identity at every API boundary |
| Least privilege | Scope attenuation ensures minimal necessary permissions |
| Assume breach | Audit trails enable rapid forensic investigation |
| Verify explicitly | Every action checks agent scope before execution |

### 4.4 Existing IAM Integration

The framework is designed to complement, not replace, existing IAM:

- **Okta/Auth0:** Human identity federation; agents inherit from authenticated humans
- **OAuth 2.0:** Agent credentials can be OAuth tokens with custom claims
- **RBAC/ABAC:** Scope definitions map to existing role/attribute schemas
- **SIEM Integration:** Audit logs export in standard formats (CEF, JSON)

---

## 5. Open Research Questions

This framework is intentionally v0.1. We invite community input on:

### 5.1 Granularity

**Question:** Should ephemeral sub-agents (created for a single API call) receive full identity registration?

**Tradeoffs:** Full registration provides complete traceability but adds overhead. Lightweight "anonymous child" patterns might be appropriate for high-frequency, low-risk operations.

### 5.2 Cross-Organization Agents

**Question:** How should identity and delegation work when agents operate across organizational boundaries?

**Considerations:** 
- Federated identity (like SAML for humans)?
- Certificate-based mutual authentication?
- Blockchain-anchored identity claims?

### 5.3 Revocation Latency

**Question:** What's acceptable latency to revoke a compromised agent across distributed systems?

**Context:** In Zero Trust, revocation should be immediate. Distributed systems have inherent propagation delays. What SLA is appropriate?

### 5.4 Privacy vs. Auditability

**Question:** Should audit logs include action payloads, or only metadata?

**Tradeoffs:** Full payloads enable forensic reconstruction but may contain sensitive data. Metadata-only logs may be insufficient for incident response.

---

## 6. Conclusion and Call for Collaboration

### 6.1 Summary

Autonomous AI agents create an accountability gap that existing governance frameworks cannot address. Agent Identity Governance provides the missing infrastructure layer:

- **Explicit identity** makes agents traceable principals
- **Delegation tracking** documents authority chains
- **Scope attenuation** prevents privilege escalation
- **Audit trails** enable forensic investigation
- **Lifecycle management** enables incident response

### 6.2 Demonstrated Feasibility

This is not theoretical. We provide:
- ✅ Working code (1,598 lines, 8 tests passing)
- ✅ Public repository (GitHub)
- ✅ Live demo (publicly accessible)
- ✅ Full documentation

The concepts are implementable with existing technology, today.

### 6.3 Seeking Feedback

We invite engagement from:

- **NIST and regulatory bodies:** Does this address accountability gaps you observe?
- **Standards organizations (ISO, IEEE):** Should this become a formal standard?
- **Enterprise practitioners:** Would you pilot this approach?
- **Researchers:** What extensions or alternatives should we explore?

### 6.4 Path Forward

Based on community feedback, we propose:

**Near-term (3-6 months):**
- Integrate with major IAM providers (Okta, Azure AD)
- Develop policy DSL for complex delegation rules
- Build real-time monitoring dashboard

**Medium-term (6-12 months):**
- Pilot with enterprise partners
- Develop cross-organization federation protocol
- Submit for ISO/IEEE standardization consideration

**Long-term:**
- Establish "Agent Identity Governance" as standard vocabulary
- Community-maintained reference implementation
- Integration into AI platform SDKs (LangChain, AutoGPT, etc.)

---

## Appendix A: API Reference

### A.1 Register Agent
```http
POST /agents/register
Content-Type: application/json

{
  "agent_name": "CustomerServiceBot",
  "agent_type": "autonomous",
  "created_by": "user:alice@example.com",
  "authority_source": "human",
  "scope": ["read:tickets", "write:responses"]
}
```

**Response:**
```json
{
  "agent_id": "agent_4e5f93b4a829bc4c",
  "credentials": {
    "api_key": "air_xxxxx...",
    "expires_at": 1740000000
  }
}
```

### A.2 Spawn Sub-Agent
```http
POST /agents/{agent_id}/spawn
Content-Type: application/json

{
  "agent_name": "TicketAnalyzer",
  "agent_type": "tool",
  "scope": ["read:tickets"]
}
```

**Response:**
```json
{
  "agent_id": "agent_xyz789...",
  "credentials": {...},
  "delegation_chain": [
    {"type": "human", "id": "user:alice@example.com"},
    {"type": "agent", "id": "agent_4e5f93b4...", "name": "CustomerServiceBot"},
    {"type": "agent", "id": "agent_xyz789...", "name": "TicketAnalyzer"}
  ],
  "delegation_depth": 2
}
```

### A.3 Log Action
```http
POST /audit/log
Content-Type: application/json

{
  "agent_id": "agent_4e5f93b4a829bc4c",
  "action": "read:ticket",
  "resource": "ticket_12345",
  "success": true
}
```

**Response:**
```json
{
  "log_id": "log_abc123...",
  "human_authority": "user:alice@example.com",
  "recorded_at": 1708048800
}
```

### A.4 Audit Trace
```http
GET /audit/trace/{agent_id}
```

**Response:**
```json
{
  "agent_id": "agent_xyz789...",
  "agent_name": "TicketAnalyzer",
  "delegation_chain": [...],
  "delegation_depth": 2,
  "scope": ["read:tickets"],
  "audit_trail": [
    {
      "log_id": "log_001...",
      "action": "read:ticket",
      "resource": "ticket_12345",
      "timestamp": 1708048800,
      "success": true
    }
  ]
}
```

---

## Appendix B: Database Schema

```sql
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    agent_type TEXT CHECK(agent_type IN ('autonomous', 'semi-autonomous', 'tool')),
    created_at INTEGER NOT NULL,
    created_by TEXT,
    authority_source TEXT CHECK(authority_source IN ('human', 'delegated', 'policy')),
    scope_json TEXT,
    lifecycle_state TEXT CHECK(lifecycle_state IN ('active', 'suspended', 'terminated')),
    terminated_at INTEGER,
    api_key TEXT,
    api_key_expires_at INTEGER
);

CREATE TABLE delegations (
    delegation_id TEXT PRIMARY KEY,
    parent_id TEXT NOT NULL REFERENCES agents(agent_id),
    child_id TEXT NOT NULL REFERENCES agents(agent_id),
    delegated_at INTEGER NOT NULL,
    delegation_depth INTEGER
);

CREATE TABLE audit_log (
    log_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(agent_id),
    action TEXT NOT NULL,
    resource TEXT,
    timestamp INTEGER NOT NULL,
    human_authority TEXT,
    success INTEGER,
    metadata_json TEXT
);

CREATE INDEX idx_delegations_parent ON delegations(parent_id);
CREATE INDEX idx_delegations_child ON delegations(child_id);
CREATE INDEX idx_audit_agent ON audit_log(agent_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
```

---

## Appendix C: Links

- **GitHub Repository:** https://github.com/9to5ai/agent-identity-registry
- **Live Demo:** [Deployment URL]
- **API Documentation:** [Deployment URL]/docs
- **Video Walkthrough:** [YouTube/Vimeo URL]

---

*This submission represents personal views and does not represent any organizational position.*

**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)

---

**Word Count:** ~3,200 words (~8 pages formatted)  
**Version:** 1.0  
**Last Updated:** February 2026
