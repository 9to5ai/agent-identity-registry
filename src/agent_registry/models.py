"""Pydantic models for Agent Identity Registry API."""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class AgentType(str, Enum):
    AUTONOMOUS = "autonomous"
    SEMI_AUTONOMOUS = "semi-autonomous"
    TOOL = "tool"


class AuthoritySource(str, Enum):
    HUMAN = "human"
    DELEGATED = "delegated"
    POLICY = "policy"


class LifecycleState(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


# Request Models

class RegisterAgentRequest(BaseModel):
    """Request to register a new agent."""
    agent_name: str = Field(..., description="Human-readable name for the agent")
    agent_type: AgentType = Field(..., description="Type of agent")
    created_by: str = Field(..., description="Human ID or parent agent ID that created this agent")
    authority_source: AuthoritySource = Field(
        default=AuthoritySource.HUMAN,
        description="Source of agent's authority"
    )
    scope: list[str] = Field(
        default=[],
        description="List of allowed actions (e.g., ['read:database', 'write:reports'])"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent_name": "CustomerServiceBot",
                    "agent_type": "autonomous",
                    "created_by": "user:jun@apra.gov.au",
                    "authority_source": "human",
                    "scope": ["read:tickets", "write:responses"]
                }
            ]
        }
    }


class SpawnAgentRequest(BaseModel):
    """Request to spawn a sub-agent with delegated authority."""
    agent_name: str = Field(..., description="Name for the new sub-agent")
    agent_type: AgentType = Field(..., description="Type of sub-agent")
    scope: list[str] = Field(
        default=[],
        description="Scope for sub-agent (must be subset of parent's scope)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent_name": "TicketAnalyzer",
                    "agent_type": "tool",
                    "scope": ["read:tickets"]
                }
            ]
        }
    }


class LogActionRequest(BaseModel):
    """Request to log an agent action."""
    agent_id: str = Field(..., description="Agent performing the action")
    action: str = Field(..., description="Action being performed (e.g., 'read:ticket')")
    resource: Optional[str] = Field(None, description="Resource being accessed")
    success: bool = Field(True, description="Whether the action succeeded")
    metadata: Optional[dict] = Field(None, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent_id": "agent_abc123",
                    "action": "read:ticket",
                    "resource": "ticket_12345",
                    "success": True
                }
            ]
        }
    }


class AuditQueryRequest(BaseModel):
    """Query parameters for audit log search."""
    since_timestamp: Optional[int] = Field(None, description="Filter logs since this Unix timestamp")
    agent_id: Optional[str] = Field(None, description="Filter by agent ID")
    action: Optional[str] = Field(None, description="Filter by action type")
    human_authority: Optional[str] = Field(None, description="Filter by human authority")
    limit: int = Field(100, description="Maximum results to return", ge=1, le=1000)


class TerminateAgentRequest(BaseModel):
    """Request to terminate an agent."""
    cascade: bool = Field(True, description="Also terminate all child agents")


# Response Models

class Credentials(BaseModel):
    """API credentials for an agent."""
    api_key: str
    expires_at: int


class RegisterAgentResponse(BaseModel):
    """Response after registering an agent."""
    agent_id: str
    credentials: Credentials


class ChainLink(BaseModel):
    """A link in the delegation chain."""
    type: Literal["human", "agent"]
    id: str
    name: Optional[str] = None


class SpawnAgentResponse(BaseModel):
    """Response after spawning a sub-agent."""
    agent_id: str
    credentials: Credentials
    delegation_chain: list[ChainLink]
    delegation_depth: int


class LogActionResponse(BaseModel):
    """Response after logging an action."""
    log_id: str
    human_authority: Optional[str]
    recorded_at: int


class AuditEntry(BaseModel):
    """A single audit log entry."""
    log_id: str
    action: str
    resource: Optional[str]
    timestamp: int
    success: bool
    metadata: Optional[dict] = None


class AuditTraceResponse(BaseModel):
    """Full audit trace for an agent."""
    agent_id: str
    agent_name: str
    lifecycle_state: str
    delegation_chain: list[ChainLink]
    delegation_depth: int
    scope: list[str]
    audit_trail: list[AuditEntry]


class AuditLogEntry(BaseModel):
    """Audit log entry with agent info."""
    log_id: str
    agent_id: str
    agent_name: Optional[str]
    action: str
    resource: Optional[str]
    timestamp: int
    human_authority: Optional[str]
    success: bool


class TerminateAgentResponse(BaseModel):
    """Response after terminating agents."""
    terminated: list[str]
    count: int


class AgentInfo(BaseModel):
    """Public agent information."""
    agent_id: str
    agent_name: str
    agent_type: str
    created_at: int
    created_by: Optional[str]
    authority_source: str
    scope: list[str]
    lifecycle_state: str


class ScopeCheckResponse(BaseModel):
    """Response from scope check."""
    agent_id: str
    action: str
    allowed: bool
    agent_scope: list[str]


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
