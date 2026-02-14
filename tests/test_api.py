"""Tests for Agent Identity Registry API."""
import pytest
from fastapi.testclient import TestClient

from src.agent_registry.main import app
from src.agent_registry.database import reset_database, init_db


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    init_db()
    reset_database()
    init_db()
    yield


client = TestClient(app)


def test_health():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


def test_register_agent():
    """Test agent registration."""
    response = client.post("/agents/register", json={
        "agent_name": "TestBot",
        "agent_type": "autonomous",
        "created_by": "user:test@example.com",
        "authority_source": "human",
        "scope": ["read:data", "write:data"]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"].startswith("agent_")
    assert "api_key" in data["credentials"]


def test_spawn_agent():
    """Test sub-agent spawning."""
    # First register a parent
    parent_resp = client.post("/agents/register", json={
        "agent_name": "ParentBot",
        "agent_type": "autonomous",
        "created_by": "user:test@example.com",
        "authority_source": "human",
        "scope": ["read:data", "write:data"]
    })
    parent_id = parent_resp.json()["agent_id"]
    
    # Spawn a child
    child_resp = client.post(f"/agents/{parent_id}/spawn", json={
        "agent_name": "ChildBot",
        "agent_type": "tool",
        "scope": ["read:data"]
    })
    assert child_resp.status_code == 200
    child_data = child_resp.json()
    assert child_data["delegation_depth"] == 1
    assert len(child_data["delegation_chain"]) == 3  # human, parent, child


def test_scope_attenuation():
    """Test that scope attenuation is enforced."""
    # Register parent with limited scope
    parent_resp = client.post("/agents/register", json={
        "agent_name": "LimitedBot",
        "agent_type": "autonomous",
        "created_by": "user:test@example.com",
        "authority_source": "human",
        "scope": ["read:data"]
    })
    parent_id = parent_resp.json()["agent_id"]
    
    # Try to spawn child with MORE scope - should fail
    child_resp = client.post(f"/agents/{parent_id}/spawn", json={
        "agent_name": "OverreachBot",
        "agent_type": "tool",
        "scope": ["read:data", "write:data"]  # write:data not in parent!
    })
    assert child_resp.status_code == 400
    assert "attenuation" in child_resp.json()["detail"].lower()


def test_audit_logging():
    """Test audit log creation."""
    # Register agent
    agent_resp = client.post("/agents/register", json={
        "agent_name": "AuditTestBot",
        "agent_type": "autonomous",
        "created_by": "user:auditor@example.com",
        "authority_source": "human",
        "scope": ["read:logs"]
    })
    agent_id = agent_resp.json()["agent_id"]
    
    # Log an action
    log_resp = client.post("/audit/log", json={
        "agent_id": agent_id,
        "action": "read:logs",
        "resource": "system.log",
        "success": True
    })
    assert log_resp.status_code == 200
    log_data = log_resp.json()
    assert log_data["human_authority"] == "user:auditor@example.com"


def test_audit_trace():
    """Test audit trace retrieval."""
    # Register and log
    agent_resp = client.post("/agents/register", json={
        "agent_name": "TraceBot",
        "agent_type": "tool",
        "created_by": "user:tracer@example.com",
        "authority_source": "human",
        "scope": ["action:test"]
    })
    agent_id = agent_resp.json()["agent_id"]
    
    client.post("/audit/log", json={
        "agent_id": agent_id,
        "action": "action:test",
        "resource": "test_resource"
    })
    
    # Get trace
    trace_resp = client.get(f"/audit/trace/{agent_id}")
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()
    assert trace_data["agent_id"] == agent_id
    assert len(trace_data["delegation_chain"]) >= 1
    assert len(trace_data["audit_trail"]) == 1


def test_terminate_cascade():
    """Test cascade termination."""
    # Create parent -> child
    parent_resp = client.post("/agents/register", json={
        "agent_name": "ParentToTerminate",
        "agent_type": "autonomous",
        "created_by": "user:test@example.com",
        "scope": ["any:action"]
    })
    parent_id = parent_resp.json()["agent_id"]
    
    child_resp = client.post(f"/agents/{parent_id}/spawn", json={
        "agent_name": "ChildToTerminate",
        "agent_type": "tool",
        "scope": ["any:action"]
    })
    child_id = child_resp.json()["agent_id"]
    
    # Terminate parent with cascade
    term_resp = client.post(f"/agents/{parent_id}/terminate", json={
        "cascade": True
    })
    assert term_resp.status_code == 200
    term_data = term_resp.json()
    assert parent_id in term_data["terminated"]
    assert child_id in term_data["terminated"]


def test_query_by_human_authority():
    """Test querying logs by human authority."""
    # Create agent and log actions
    agent_resp = client.post("/agents/register", json={
        "agent_name": "QueryTestBot",
        "agent_type": "tool",
        "created_by": "user:query_test@example.com",
        "scope": ["test:action"]
    })
    agent_id = agent_resp.json()["agent_id"]
    
    client.post("/audit/log", json={
        "agent_id": agent_id,
        "action": "test:action"
    })
    
    # Query by human authority
    query_resp = client.get("/audit/query", params={
        "human_authority": "user:query_test@example.com"
    })
    assert query_resp.status_code == 200
    logs = query_resp.json()
    assert len(logs) >= 1
    assert all(l["human_authority"] == "user:query_test@example.com" for l in logs)
