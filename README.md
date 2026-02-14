# Agent Identity Registry

> **Proof-of-concept implementation of Agent Identity Governance**

As AI agents become autonomous actors in enterprise systems—spawning sub-agents, crossing API boundaries, making decisions without human-in-the-loop—existing identity and access management breaks down. This project demonstrates a solution.

**Live Demo:** [https://agent-identity-registry.railway.app](https://agent-identity-registry.railway.app) *(link TBD)*  
**API Docs:** [/docs](https://agent-identity-registry.railway.app/docs)

## The Problem

```
❌ Traditional IAM assumes:
   • Static principals (humans, services)
   • Direct human oversight
   • Shared credentials = identity
   
❌ Autonomous agents break this:
   • Dynamic creation (agents spawn agents)
   • No human in the loop
   • Shared API key ≠ knowing who did what
```

**When Agent A spawns Agent B spawns Agent C... who's responsible?**

## The Solution

```
✅ Agent Identity Governance:
   • Every agent gets explicit identity (not just API keys)
   • Delegation chains are tracked (parent → child)
   • All actions trace back to human authority
   • Scope enforcement (children can't exceed parents)
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    AGENT IDENTITY REGISTRY                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  Register   │    │   Spawn     │    │    Audit    │      │
│  │   Agent     │    │  Sub-Agent  │    │   Actions   │      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
│  ┌─────────────────────────▼─────────────────────────────┐  │
│  │                    CORE ENGINE                         │  │
│  │  • Identity issuance    • Delegation chain tracking    │  │
│  │  • Scope enforcement    • Audit trail generation       │  │
│  │  • Lifecycle management • Forensic queries             │  │
│  └─────────────────────────┬─────────────────────────────┘  │
│                            │                                 │
│  ┌─────────────────────────▼─────────────────────────────┐  │
│  │                    DATABASE (SQLite)                   │  │
│  │  agents | delegations | audit_log                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Demo Scenario

```
DELEGATION CHAIN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

     👤 Jun (user:jun@apra.gov.au)
      │
      │ authorizes with scope:
      │ [read:database, write:reports, create:charts]
      │
      ▼
     🤖 Agent A "DataAnalyzer"
      │
      ├──spawns───▶ 🤖 Agent B "ReportGenerator"
      │             scope: [write:reports]
      │
      └──spawns───▶ 🤖 Agent C "ChartMaker"
                    scope: [create:charts]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCOPE ATTENUATION:
• Agent B cannot have [create:charts] - not in its parent's delegated scope
• Agent C cannot have [read:database] - not delegated by A
• Every action traces back to Jun as human authority
```

## Quick Start

### Option 1: Run Locally

```bash
# Clone the repo
git clone https://github.com/[username]/agent-identity-registry.git
cd agent-identity-registry

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e .

# Run the server
uvicorn src.agent_registry.main:app --reload

# Open http://localhost:8000/docs for Swagger UI
```

### Option 2: Docker

```bash
docker build -t agent-identity-registry .
docker run -p 8000:8000 agent-identity-registry
```

### Option 3: Run Demo Script

```bash
# Start server first, then in another terminal:
pip install requests
python demo.py

# Or against live deployment:
python demo.py --base-url https://agent-identity-registry.railway.app
```

## API Reference

### Register Agent

```bash
POST /agents/register
```

Create a new agent with explicit identity.

```json
{
  "agent_name": "CustomerServiceBot",
  "agent_type": "autonomous",
  "created_by": "user:jun@apra.gov.au",
  "authority_source": "human",
  "scope": ["read:tickets", "write:responses"]
}
```

**Response:**
```json
{
  "agent_id": "agent_abc123def456",
  "credentials": {
    "api_key": "air_xxxxx...",
    "expires_at": 1740000000
  }
}
```

### Spawn Sub-Agent (Delegation)

```bash
POST /agents/{agent_id}/spawn
```

Create a sub-agent with delegated authority. Scope must be **subset** of parent.

```json
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
    {"type": "human", "id": "user:jun@apra.gov.au"},
    {"type": "agent", "id": "agent_abc123...", "name": "CustomerServiceBot"},
    {"type": "agent", "id": "agent_xyz789...", "name": "TicketAnalyzer"}
  ],
  "delegation_depth": 2
}
```

### Log Action

```bash
POST /audit/log
```

Log an agent action with automatic human authority tracing.

```json
{
  "agent_id": "agent_abc123...",
  "action": "read:ticket",
  "resource": "ticket_12345",
  "success": true
}
```

**Response:**
```json
{
  "log_id": "log_000...",
  "human_authority": "user:jun@apra.gov.au",
  "recorded_at": 1708048800
}
```

### Audit Trace (Forensic Query)

```bash
GET /audit/trace/{agent_id}
```

Get full delegation chain and audit trail for any agent.

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

### Query Audit Logs

```bash
GET /audit/query?human_authority=user:jun@apra.gov.au&since=1708000000
```

Filter audit logs by human authority, agent, action type, time range.

## Database Schema

```sql
-- Every agent gets explicit identity
CREATE TABLE agents (
  agent_id TEXT PRIMARY KEY,
  agent_name TEXT NOT NULL,
  agent_type TEXT,  -- autonomous, semi-autonomous, tool
  created_at INTEGER,
  created_by TEXT,  -- human_id or parent_agent_id
  authority_source TEXT,  -- human, delegated, policy
  scope_json TEXT,
  lifecycle_state TEXT  -- active, suspended, terminated
);

-- Delegation relationships tracked
CREATE TABLE delegations (
  delegation_id TEXT PRIMARY KEY,
  parent_id TEXT,
  child_id TEXT,
  delegated_at INTEGER,
  delegation_depth INTEGER
);

-- Every action logged with traceability
CREATE TABLE audit_log (
  log_id TEXT PRIMARY KEY,
  agent_id TEXT,
  action TEXT,
  resource TEXT,
  timestamp INTEGER,
  human_authority TEXT,  -- traced through chain
  success INTEGER
);
```

## Key Concepts

### 1. Agent Identity (Not Just API Keys)

Traditional systems use shared API keys. Agent Identity Registry gives each agent a unique, traceable identity.

### 2. Delegation Chain

When Agent A spawns Agent B, the relationship is explicitly tracked. Every action by B traces back to A's human authority.

### 3. Scope Attenuation

Children can only have **subset** of parent's scope. No privilege escalation through delegation.

### 4. Human Ultimate Authority

Every delegation chain terminates at a human. Forensic queries answer: "Who authorized this agent?"

### 5. Audit Trail

All actions logged with:
- What was done
- By which agent
- At what time
- Authorized by which human

## Regulatory Alignment

| Regulation | How This Helps |
|------------|----------------|
| **NIST AI RMF** (Govern) | Provides accountability infrastructure for AI systems |
| **EU AI Act** (Article 12) | Record-keeping for high-risk AI systems |
| **APRA CPS 230/234** | Operational resilience audit trails |
| **ISO 27001** | Access control for AI principals |

## Limitations (v0.1)

This is a proof-of-concept, not production-ready:

- ❌ No real authentication (API keys are demo-only)
- ❌ SQLite (not horizontally scalable)
- ❌ No encryption at rest
- ❌ Single-node deployment

**Purpose:** Demonstrate the concept is implementable, not provide enterprise solution.

## What's Next

See [NIST Submission](./docs/nist-submission.md) for the formal framework proposal.

Future extensions:
- Integration with Okta, Auth0, Azure AD
- Policy DSL for complex delegation rules
- Real-time monitoring dashboard
- Multi-org federation

## Contributing

This is v0.1 — intentionally incomplete. We're seeking:

- **Regulatory feedback** (especially APRA, EU AI Office, NIST)
- **Enterprise pilots** (who wants to test this?)
- **Technical contributions** (PRs welcome)

## License

MIT — fork it, improve it, deploy it.

## Author

Jun M • [LinkedIn](https://linkedin.com/in/junm) • [Twitter](https://twitter.com/junm)

---

*"You can't have accountability without identity."*
