"""Agent Identity Registry - FastAPI Application."""
import time
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from . import __version__
from .database import (
    init_db,
    register_agent,
    get_agent,
    spawn_agent,
    log_action,
    get_audit_trace,
    check_scope,
    query_audit_logs,
    terminate_agent,
    get_all_agents,
    get_agent_scope,
    reset_database,
)
from .models import (
    RegisterAgentRequest,
    RegisterAgentResponse,
    SpawnAgentRequest,
    SpawnAgentResponse,
    LogActionRequest,
    LogActionResponse,
    AuditTraceResponse,
    AuditLogEntry,
    TerminateAgentRequest,
    TerminateAgentResponse,
    AgentInfo,
    ScopeCheckResponse,
    HealthResponse,
    ErrorResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title="Agent Identity Registry",
    description="""
## Agent Identity Governance Proof-of-Concept

This API demonstrates key concepts of Agent Identity Governance:

- **Agent Registration**: Create agents with explicit identity and scope
- **Delegation**: Spawn sub-agents with inherited (attenuated) authority
- **Audit Logging**: Track all agent actions with human authority tracing
- **Forensic Queries**: Answer "who authorized this?" for any action

### Key Concepts

1. **Agent Identity**: Every agent gets a unique ID, not just shared API keys
2. **Delegation Chain**: Sub-agents inherit bounded authority from parents
3. **Scope Attenuation**: Child agents can't have MORE permissions than parents
4. **Human Authority**: All delegation chains trace back to a human authorizer
5. **Audit Trail**: Every action logged with full traceability

### Demo Scenario

1. Human (Jun) authorizes Agent A ("DataAnalyzer")
2. Agent A spawns Agent B ("ReportGenerator") 
3. Agent B spawns Agent C ("ChartMaker")
4. All actions are logged with delegation chain tracking
5. Forensic queries can trace any action back to Jun

---

**Version**: 0.1.0  
**License**: MIT  
**Author**: Jun M  
""",
    version=__version__,
    lifespan=lifespan,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
    },
)

# CORS for demo purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health & Info

@app.get("/", tags=["Info"])
async def root():
    """API root - basic info."""
    return {
        "name": "Agent Identity Registry",
        "version": __version__,
        "docs": "/docs",
        "description": "Agent Identity Governance Proof-of-Concept"
    }


@app.get("/health", response_model=HealthResponse, tags=["Info"])
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        database="sqlite"
    )


# Agent Management

@app.post(
    "/agents/register",
    response_model=RegisterAgentResponse,
    tags=["Agents"],
    summary="Register a new agent",
    description="""
Register a new agent in the identity registry.

The agent receives:
- Unique agent ID
- API credentials (for authentication)
- Defined scope (allowed actions)

**Note**: For human-authorized agents, set `created_by` to a human identifier
(e.g., `user:jun@apra.gov.au`).
"""
)
async def api_register_agent(request: RegisterAgentRequest):
    """Register a new agent and issue credentials."""
    try:
        result = register_agent(
            agent_name=request.agent_name,
            agent_type=request.agent_type.value,
            created_by=request.created_by,
            authority_source=request.authority_source.value,
            scope=request.scope
        )
        return RegisterAgentResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/agents",
    response_model=list[AgentInfo],
    tags=["Agents"],
    summary="List all agents"
)
async def api_list_agents(include_terminated: bool = Query(False)):
    """List all registered agents."""
    agents = get_all_agents(include_terminated=include_terminated)
    return [
        AgentInfo(
            agent_id=a["agent_id"],
            agent_name=a["agent_name"],
            agent_type=a["agent_type"],
            created_at=a["created_at"],
            created_by=a.get("created_by"),
            authority_source=a["authority_source"],
            scope=a["scope"],
            lifecycle_state=a["lifecycle_state"]
        )
        for a in agents
    ]


@app.get(
    "/agents/{agent_id}",
    response_model=AgentInfo,
    tags=["Agents"],
    summary="Get agent details"
)
async def api_get_agent(agent_id: str):
    """Get details for a specific agent."""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    import json
    return AgentInfo(
        agent_id=agent["agent_id"],
        agent_name=agent["agent_name"],
        agent_type=agent["agent_type"],
        created_at=agent["created_at"],
        created_by=agent.get("created_by"),
        authority_source=agent["authority_source"],
        scope=json.loads(agent["scope_json"]) if agent["scope_json"] else [],
        lifecycle_state=agent["lifecycle_state"]
    )


@app.post(
    "/agents/{agent_id}/spawn",
    response_model=SpawnAgentResponse,
    tags=["Delegation"],
    summary="Spawn a sub-agent",
    description="""
Create a sub-agent with delegated authority from a parent agent.

**Key rules:**
- Child scope must be a **subset** of parent scope (attenuation only)
- Delegation chain is automatically tracked
- Child inherits authority traced to human source
"""
)
async def api_spawn_agent(agent_id: str, request: SpawnAgentRequest):
    """Spawn a sub-agent with delegated authority."""
    try:
        result = spawn_agent(
            parent_id=agent_id,
            agent_name=request.agent_name,
            agent_type=request.agent_type.value,
            scope=request.scope
        )
        return SpawnAgentResponse(
            agent_id=result["agent_id"],
            credentials=result["credentials"],
            delegation_chain=result["delegation_chain"],
            delegation_depth=result["delegation_depth"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/agents/{agent_id}/scope/check",
    response_model=ScopeCheckResponse,
    tags=["Agents"],
    summary="Check if action is in scope"
)
async def api_check_scope(agent_id: str, action: str = Query(...)):
    """Check if an agent has permission for an action."""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    allowed = check_scope(agent_id, action)
    scope = get_agent_scope(agent_id)
    
    return ScopeCheckResponse(
        agent_id=agent_id,
        action=action,
        allowed=allowed,
        agent_scope=scope
    )


@app.post(
    "/agents/{agent_id}/terminate",
    response_model=TerminateAgentResponse,
    tags=["Agents"],
    summary="Terminate an agent"
)
async def api_terminate_agent(agent_id: str, request: TerminateAgentRequest = None):
    """Terminate an agent and optionally its children."""
    if request is None:
        request = TerminateAgentRequest()
    
    try:
        result = terminate_agent(agent_id, cascade=request.cascade)
        return TerminateAgentResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Audit Logging

@app.post(
    "/audit/log",
    response_model=LogActionResponse,
    tags=["Audit"],
    summary="Log an agent action",
    description="""
Log an action performed by an agent.

The system automatically:
- Traces back through delegation chain to find human authority
- Records timestamp and all metadata
- Links to agent's identity record
"""
)
async def api_log_action(request: LogActionRequest):
    """Log an agent action."""
    agent = get_agent(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {request.agent_id} not found")
    
    result = log_action(
        agent_id=request.agent_id,
        action=request.action,
        resource=request.resource,
        success=request.success,
        metadata=request.metadata
    )
    return LogActionResponse(**result)


@app.get(
    "/audit/trace/{agent_id}",
    response_model=AuditTraceResponse,
    tags=["Audit"],
    summary="Get full audit trace for an agent",
    description="""
Get the complete delegation chain and audit trail for an agent.

Returns:
- Full delegation chain (human → agent_a → agent_b → ...)
- All logged actions by this agent
- Agent's current scope and lifecycle state
"""
)
async def api_audit_trace(agent_id: str):
    """Get full delegation chain and audit trail for an agent."""
    try:
        result = get_audit_trace(agent_id)
        return AuditTraceResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get(
    "/audit/query",
    response_model=list[AuditLogEntry],
    tags=["Audit"],
    summary="Query audit logs",
    description="""
Query audit logs with filters.

**Example queries:**
- "Show all actions in the last hour"
- "Show all actions by a specific agent"
- "Show all actions authorized by a specific human"
"""
)
async def api_query_audit(
    since: int = Query(None, description="Unix timestamp to filter logs since"),
    agent_id: str = Query(None, description="Filter by agent ID"),
    action: str = Query(None, description="Filter by action type"),
    human_authority: str = Query(None, description="Filter by human authority"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results")
):
    """Query audit logs with filters."""
    results = query_audit_logs(
        since_timestamp=since,
        agent_id=agent_id,
        action=action,
        human_authority=human_authority,
        limit=limit
    )
    return [AuditLogEntry(**r) for r in results]


# Demo/Admin endpoints

@app.post(
    "/admin/reset",
    tags=["Admin"],
    summary="Reset database (demo only)",
    description="**WARNING**: Clears all data. For demo purposes only."
)
async def api_reset():
    """Reset the database (demo purposes only)."""
    reset_database()
    init_db()
    return {"status": "reset", "message": "Database cleared"}


@app.get(
    "/admin/stats",
    tags=["Admin"],
    summary="Get registry statistics"
)
async def api_stats():
    """Get statistics about the registry."""
    agents = get_all_agents(include_terminated=True)
    logs = query_audit_logs(limit=10000)
    
    active = sum(1 for a in agents if a["lifecycle_state"] == "active")
    terminated = sum(1 for a in agents if a["lifecycle_state"] == "terminated")
    
    return {
        "agents": {
            "total": len(agents),
            "active": active,
            "terminated": terminated
        },
        "audit_logs": {
            "total": len(logs)
        }
    }
