# Agent Identity Governance Framework
## A Submission to NIST AI Accountability and Transparency Consultation

**Submission Date:** March 2026  
**Author:** Jun M  
**Affiliation:** Independent (views are personal, not organizational)

---

## Executive Summary

As autonomous AI agents proliferate in enterprise environments—spawning sub-agents, crossing API boundaries, and operating without human-in-the-loop—existing accountability frameworks face a fundamental gap: **they assume we know who or what took an action.** Current Identity and Access Management (IAM) systems were designed for humans and static services, not for dynamic, self-replicating autonomous systems.

This submission proposes **Agent Identity Governance**, a framework that provides:
1. **Explicit agent identity** (not shared API keys)
2. **Delegation chain tracking** (who authorized this agent?)
3. **Audit trails** that trace actions to human authority
4. **Scope enforcement** preventing privilege escalation through delegation

We demonstrate feasibility with a **working proof-of-concept implementation** available at [GitHub link] and a live demo at [deployment URL].

---

## 1. Problem Statement

### 1.1 The Accountability Gap

Current AI governance frameworks assume:
- **Static principals**: Identity systems manage humans and services with known, fixed identities
- **Direct human oversight**: Actions trace directly to human operators
- **Shared credentials = identity**: API keys represent the entity using them

Autonomous agents violate all three assumptions:

| Assumption | Reality with Autonomous Agents |
|------------|-------------------------------|
| Static principals | Agents spawn dynamically; an AI assistant might create 10 sub-agents in a single task |
| Human oversight | Agents operate independently; "human-in-the-loop" may be hours or days delayed |
| Credentials = identity | Multiple agents share API keys; logs show "key X called API" not "Agent Y doing task Z" |

### 1.2 Regulatory Requirements Without Technical Solutions

Multiple regulatory frameworks demand accountability:

- **NIST AI RMF** calls for governance mechanisms but doesn't specify identity infrastructure
- **EU AI Act (Article 12)** requires record-keeping for high-risk systems but doesn't define agent identity
- **APRA CPS 230/234** (Australia) demands operational resilience audit trails but assumes human-centric access control

**The gap:** Regulations require accountability, but no standard technical mechanism exists to provide it for autonomous agents.

### 1.3 A Concrete Example

Consider a typical enterprise AI deployment:

```
1. Human analyst (Alice) launches AI agent "DataProcessor"
2. DataProcessor spawns "DataExtractor" to pull from databases
3. DataExtractor spawns "ReportGenerator" to create outputs
4. ReportGenerator accesses sensitive customer data
5. An audit question arises: "Who authorized access to customer data?"
```

**Current systems answer:** "API key 'prod-ai-key' accessed the database"  
**Required answer:** "ReportGenerator, delegated from DataExtractor, delegated from DataProcessor, authorized by Alice"

Without agent identity infrastructure, the required answer is impossible.

---

## 2. Proposed Framework: Agent Identity Governance

### 2.1 Core Concept: Agent Identity Registry

Every agent in an organization receives explicit identity registration:

```
Agent Identity Record:
├── agent_id: Unique identifier
├── agent_name: Human-readable name
├── agent_type: autonomous | semi-autonomous | tool
├── created_at: Timestamp
├── created_by: Human ID or parent agent ID
├── authority_source: human | delegated | policy
├── scope: [list of allowed actions]
└── lifecycle_state: active | suspended | terminated
```

**Key innovation:** Agents are first-class principals, not anonymous API consumers.

### 2.2 Delegation & Authority Model

When Agent A spawns Agent B:

1. **Explicit delegation** is recorded: `A → B`
2. **Scope attenuation** is enforced: B cannot have more permissions than A
3. **Human authority** is traced: all delegation chains terminate at a human
4. **Time bounds** are optional: authority can expire

```
Delegation Chain Example:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     👤 Alice (human)
      │
      │ authorizes
      │
      ▼
     🤖 DataProcessor
      │  scope: [read:database, write:reports]
      │
      │ spawns (inherits subset)
      │
      ▼
     🤖 DataExtractor
      │  scope: [read:database]
      │
      │ spawns (inherits subset)
      │
      ▼
     🤖 ReportGenerator
         scope: [read:database]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Forensic query: "Who authorized ReportGenerator?"
Answer: Alice, via DataProcessor → DataExtractor delegation chain
```

### 2.3 Audit & Accountability

Every agent action is logged with:
- **What:** Action performed, resource accessed
- **Who:** Agent ID (not just API key)
- **When:** Timestamp
- **Authority:** Human traced through delegation chain
- **Outcome:** Success/failure

This enables forensic queries:
- "Show all actions by agents created in the last hour"
- "Which human authorized this specific database access?"
- "Trace this API call back to its originating delegation"

### 2.4 Lifecycle Management

```
Provisioning → Active → Suspension → Termination
      ↓           ↓          ↓             ↓
   Identity   Operations  Incident      Cleanup
   issued     in scope    response      & audit
```

**Cascade termination:** When a parent agent is terminated, all child agents are automatically revoked.

---

## 3. Technical Implementation

### 3.1 Proof-of-Concept Architecture

We provide a working implementation demonstrating these concepts:

```
┌──────────────────────────────────────────────────┐
│           Agent Identity Registry API            │
├──────────────────────────────────────────────────┤
│  POST /agents/register    - Create agent         │
│  POST /agents/{id}/spawn  - Delegate authority   │
│  POST /audit/log          - Log action           │
│  GET  /audit/trace/{id}   - Forensic query       │
└──────────────────────────────────────────────────┘
                      │
┌──────────────────────────────────────────────────┐
│              SQLite Database                     │
│  agents | delegations | audit_log                │
└──────────────────────────────────────────────────┘
```

**Technology stack:** Python, FastAPI, SQLite (chosen for simplicity; production would use PostgreSQL or similar)

### 3.2 Demo Scenario

Our demo script (`demo.py`) demonstrates:

1. Human (Jun) authorizes Agent A ("DataAnalyzer")
2. Agent A spawns Agent B ("ReportGenerator") with subset scope
3. Agent A spawns Agent C ("ChartMaker") with different subset scope
4. **Scope attenuation tested:** Agent B tries to spawn with excess scope → denied
5. All agents perform actions → logged with delegation chain
6. Forensic query traces any action back to Jun

**Live demo:** [URL]  
**GitHub repository:** [URL]

### 3.3 Key Code Example

Scope attenuation enforcement:

```python
def spawn_agent(parent_id, child_scope):
    parent_scope = get_agent_scope(parent_id)
    
    # Enforce attenuation - child can't exceed parent
    invalid = [s for s in child_scope if s not in parent_scope]
    if invalid:
        raise Error(f"Scope attenuation violation: {invalid}")
    
    # Create child with delegated authority
    child = create_agent(
        created_by=parent_id,
        authority_source="delegated",
        scope=child_scope
    )
    
    # Record delegation chain
    record_delegation(parent_id, child.id)
    
    return child
```

---

## 4. Regulatory Alignment

### 4.1 NIST AI RMF Mapping

| RMF Function | Agent Identity Governance Support |
|--------------|----------------------------------|
| **GOVERN** | Agent registry provides accountability infrastructure; policies enforce scope limits |
| **MAP** | Delegation chains document agent relationships and authority flows |
| **MEASURE** | Audit trails enable monitoring agent behavior against expected scope |
| **MANAGE** | Lifecycle management enables response to incidents; cascade termination |

### 4.2 EU AI Act (Article 12)

Article 12 requires "automatic recording of events" for high-risk AI systems. Agent Identity Governance provides:
- Structured logs with agent identity (not anonymous API calls)
- Delegation chain enabling "who authorized this" queries
- Lifecycle records (creation, activity, termination)

### 4.3 APRA CPS 230/234

Australian prudential standards require operational resilience and information security controls. Agent Identity Governance enables:
- **CPS 230:** Agent audit trails support incident response and recovery
- **CPS 234:** Agent identity as access control mechanism; scope enforcement as security control

### 4.4 Zero Trust Architecture

Zero Trust principles ("never trust, always verify") extend naturally:
- Agent identity verified at every API boundary crossing
- Scope checked for every action (not just at creation)
- Delegation depth limits prevent unbounded authority chains

---

## 5. Open Questions

This is v0.1—intentionally incomplete. We seek community input on:

1. **Granularity:** Should sub-agents created dynamically (e.g., for a single API call) get full identity registration, or inherit parent identity?

2. **Cross-organization agents:** How should identity and delegation work when agents operate across organizational boundaries?

3. **Revocation latency:** What's acceptable time to revoke a compromised agent's access across distributed systems?

4. **Privacy:** Should audit logs include action payloads, or only metadata?

5. **Federation:** How should agent identities be recognized across organizations? Is a certificate authority model appropriate?

---

## 6. Path Forward

### 6.1 This Submission

We provide:
- ✅ Working proof-of-concept (code, tests, documentation)
- ✅ Live demo (publicly accessible)
- ✅ Framework document (this submission)

### 6.2 Seeking Feedback

We invite:
- **Regulators:** Does this address accountability gaps you're seeing?
- **Standards bodies:** Should this become a formal standard (ISO, IEEE)?
- **Enterprises:** Would you pilot this approach?
- **Researchers:** What extensions or alternatives should we consider?

### 6.3 Next Steps

Based on feedback:
- Integrate with existing IAM systems (Okta, Auth0, Azure AD)
- Develop policy DSL for complex delegation rules
- Build real-time monitoring dashboard
- Explore multi-organization federation

---

## 7. Conclusion

Autonomous AI agents represent a new class of principal that existing identity systems weren't designed for. As agents become more capable and prevalent, the accountability gap will widen.

**Agent Identity Governance provides the missing layer:** explicit identity, delegation tracking, and audit trails that answer "who authorized this agent?"

This isn't theoretical—we've built a working implementation. The concepts are implementable with existing technology. What's needed is adoption and refinement.

We invite the NIST community to review this framework, test the implementation, and help shape the standard for agent accountability.

---

## Appendix A: Technical Specification

**Repository:** [GitHub URL]  
**API Documentation:** [Swagger URL]/docs  
**Demo Script:** `python demo.py --base-url [deployment URL]`

### Database Schema

```sql
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    agent_type TEXT CHECK(agent_type IN ('autonomous', 'semi-autonomous', 'tool')),
    created_at INTEGER NOT NULL,
    created_by TEXT,
    authority_source TEXT CHECK(authority_source IN ('human', 'delegated', 'policy')),
    scope_json TEXT,
    lifecycle_state TEXT CHECK(lifecycle_state IN ('active', 'suspended', 'terminated'))
);

CREATE TABLE delegations (
    delegation_id TEXT PRIMARY KEY,
    parent_id TEXT REFERENCES agents(agent_id),
    child_id TEXT REFERENCES agents(agent_id),
    delegated_at INTEGER NOT NULL,
    delegation_depth INTEGER
);

CREATE TABLE audit_log (
    log_id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(agent_id),
    action TEXT NOT NULL,
    resource TEXT,
    timestamp INTEGER NOT NULL,
    human_authority TEXT,
    success INTEGER
);
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agents/register` | POST | Register new agent |
| `/agents/{id}/spawn` | POST | Create sub-agent with delegation |
| `/agents/{id}/terminate` | POST | Terminate agent (optional cascade) |
| `/audit/log` | POST | Log agent action |
| `/audit/trace/{id}` | GET | Get delegation chain + audit trail |
| `/audit/query` | GET | Query logs with filters |

---

## Appendix B: Contact

**Author:** Jun M  
**LinkedIn:** [link]  
**GitHub:** [link]  
**Email:** [email]

*This submission represents personal views and does not represent any organizational position.*

---

**License:** Creative Commons BY 4.0  
**Version:** 0.1.0  
**Date:** February 2026
