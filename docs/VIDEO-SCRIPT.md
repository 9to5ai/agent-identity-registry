# Video Walkthrough Script
## Agent Identity Registry - 3 Minute Demo

**Target length:** 3 minutes  
**Format:** Screen recording with voiceover  
**Audience:** NIST reviewers, regulators, enterprise architects

---

## Script

### 0:00 - 0:15 — Opening

**[Show: Title card "Agent Identity Governance - Proof of Concept"]**

> "As autonomous AI agents become common in enterprise systems, we face a new accountability challenge: when Agent A spawns Agent B spawns Agent C, who's actually responsible?"

> "This is Agent Identity Governance—a framework that answers that question. Let me show you a working implementation."

### 0:15 - 0:45 — The Problem

**[Show: Diagram of traditional IAM vs agent delegation]**

> "Traditional identity systems assume static principals—humans and services with fixed identities. But autonomous agents are dynamic. They spawn sub-agents on demand. They operate without human-in-the-loop."

**[Show: Example audit log with just API key]**

> "When we look at logs, we see 'API key X called service Y'—but we can't answer 'which agent did this?' or 'who authorized it?'"

> "Agent Identity Governance fixes this."

### 0:45 - 1:30 — Live Demo: Registration & Delegation

**[Show: Swagger UI at /docs]**

> "Let's walk through the demo. First, a human—Jun—registers an agent called DataAnalyzer with full scope: read database, write reports, create charts."

**[Execute: POST /agents/register]**

> "The agent gets a unique ID—not a shared API key, but its own identity."

**[Show: Response with agent_id]**

> "Now DataAnalyzer needs help. It spawns a sub-agent called ReportGenerator—but with limited scope, just write:reports."

**[Execute: POST /agents/{id}/spawn]**

> "Notice the response shows the delegation chain: Jun authorized DataAnalyzer, which spawned ReportGenerator. Depth is 1."

**[Show: delegation_chain in response]**

> "Now here's the key: what if ReportGenerator tries to spawn an agent with create:charts scope—which it doesn't have?"

**[Execute: spawn with invalid scope]**

> "Denied. Scope attenuation is enforced. Children can't have more permissions than parents."

### 1:30 - 2:15 — Live Demo: Audit Trail

**[Show: Multiple agents performing actions]**

> "Let's log some actions. DataAnalyzer reads the database. ReportGenerator creates a report. ChartMaker creates a chart."

**[Execute: POST /audit/log for each]**

> "Every action is logged with the agent's identity. But here's the magic—watch the human_authority field."

**[Highlight: human_authority = user:jun@apra.gov.au]**

> "No matter which agent took the action, we trace back to Jun as the ultimate human authority."

### 2:15 - 2:45 — Forensic Query

**[Execute: GET /audit/trace/{agent_id}]**

> "Let's do a forensic query on ChartMaker. Who authorized this agent?"

**[Show: Full response with delegation_chain and audit_trail]**

> "The delegation chain shows: Jun authorized DataAnalyzer, which spawned ChartMaker. Every action ChartMaker took is in the audit trail. We can answer 'who authorized this?' for any agent, any action."

**[Execute: GET /audit/query?human_authority=user:jun@apra.gov.au]**

> "Or we can ask: 'show me everything authorized by Jun'—and we get all five logged actions across all three agents."

### 2:45 - 3:00 — Closing

**[Show: GitHub repo and documentation]**

> "This is a proof-of-concept—13 hours of development. The concepts are implementable with existing technology."

> "Agent Identity Governance provides the missing accountability layer for autonomous AI. The code is open source. The framework is open for feedback."

**[Show: NIST submission document]**

> "We've submitted this to the NIST AI Accountability consultation. We're seeking feedback from regulators, standards bodies, and enterprises."

> "Because you can't have accountability without identity."

**[End card: GitHub URL, Live Demo URL, Contact]**

---

## Production Notes

### Visuals Needed
1. Title card with logo
2. Diagram: Traditional IAM (humans → services) vs Agent delegation (human → agent → agent → agent)
3. Screen recording of Swagger UI
4. Highlight animations for key fields (agent_id, delegation_chain, human_authority)
5. End card with links

### Recording Tips
- Use light theme in browser (better for video)
- Zoom in on relevant parts of JSON responses
- Pause briefly after each key concept
- Keep mouse movements smooth

### Post-Production
- Add subtle background music (royalty-free, low volume)
- Add chapter markers: Problem, Demo, Query, Closing
- Add captions (accessibility)
- Export at 1080p

---

## Alternative: Narrated Demo Script (No Video)

If video isn't possible, the demo.py script output can serve as narrated demo:

```bash
python demo.py | tee demo-output.txt
```

The colorized output with step-by-step explanations is designed to be screenshot-friendly and self-explanatory.
