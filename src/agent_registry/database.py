"""Database layer for Agent Identity Registry."""
import sqlite3
import json
import secrets
import time
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

DATABASE_PATH = Path(__file__).parent.parent.parent / "data" / "registry.db"


def get_db_path() -> Path:
    """Get database path, creating directory if needed."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DATABASE_PATH


@contextmanager
def get_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                agent_type TEXT CHECK(agent_type IN ('autonomous', 'semi-autonomous', 'tool')),
                created_at INTEGER NOT NULL,
                created_by TEXT,
                authority_source TEXT CHECK(authority_source IN ('human', 'delegated', 'policy')),
                scope_json TEXT,
                lifecycle_state TEXT CHECK(lifecycle_state IN ('active', 'suspended', 'terminated')) DEFAULT 'active',
                terminated_at INTEGER,
                api_key TEXT,
                api_key_expires_at INTEGER
            )
        """)
        
        # Delegations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delegations (
                delegation_id TEXT PRIMARY KEY,
                parent_id TEXT NOT NULL,
                child_id TEXT NOT NULL,
                delegated_at INTEGER NOT NULL,
                delegation_depth INTEGER,
                FOREIGN KEY (parent_id) REFERENCES agents(agent_id),
                FOREIGN KEY (child_id) REFERENCES agents(agent_id)
            )
        """)
        
        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource TEXT,
                timestamp INTEGER NOT NULL,
                human_authority TEXT,
                success INTEGER,
                metadata_json TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_delegations_parent ON delegations(parent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_delegations_child ON delegations(child_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_log(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
        
        conn.commit()


def generate_agent_id() -> str:
    """Generate a unique agent ID."""
    return f"agent_{secrets.token_hex(8)}"


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"air_{secrets.token_urlsafe(32)}"


def generate_log_id() -> str:
    """Generate a unique log ID."""
    return f"log_{secrets.token_hex(8)}"


def generate_delegation_id() -> str:
    """Generate a unique delegation ID."""
    return f"del_{secrets.token_hex(8)}"


def register_agent(
    agent_name: str,
    agent_type: str,
    created_by: str,
    authority_source: str,
    scope: list[str],
    api_key_ttl_seconds: int = 86400 * 365  # 1 year default
) -> dict:
    """Register a new agent and return credentials."""
    agent_id = generate_agent_id()
    api_key = generate_api_key()
    now = int(time.time())
    expires_at = now + api_key_ttl_seconds
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agents (
                agent_id, agent_name, agent_type, created_at, created_by,
                authority_source, scope_json, lifecycle_state, api_key, api_key_expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """, (
            agent_id, agent_name, agent_type, now, created_by,
            authority_source, json.dumps(scope), api_key, expires_at
        ))
        conn.commit()
    
    return {
        "agent_id": agent_id,
        "credentials": {
            "api_key": api_key,
            "expires_at": expires_at
        }
    }


def get_agent(agent_id: str) -> Optional[dict]:
    """Get agent by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def get_agent_by_api_key(api_key: str) -> Optional[dict]:
    """Get agent by API key."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM agents WHERE api_key = ? AND lifecycle_state = 'active'",
            (api_key,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def get_agent_scope(agent_id: str) -> list[str]:
    """Get agent's scope as a list."""
    agent = get_agent(agent_id)
    if agent and agent["scope_json"]:
        return json.loads(agent["scope_json"])
    return []


def spawn_agent(
    parent_id: str,
    agent_name: str,
    agent_type: str,
    scope: list[str]
) -> dict:
    """Create a sub-agent with delegated authority."""
    parent = get_agent(parent_id)
    if not parent:
        raise ValueError(f"Parent agent {parent_id} not found")
    
    if parent["lifecycle_state"] != "active":
        raise ValueError(f"Parent agent {parent_id} is not active")
    
    # Get parent scope
    parent_scope = json.loads(parent["scope_json"]) if parent["scope_json"] else []
    
    # Enforce scope attenuation - child can't have more than parent
    invalid_scopes = [s for s in scope if s not in parent_scope]
    if invalid_scopes:
        raise ValueError(f"Scope attenuation violation: {invalid_scopes} not in parent scope")
    
    # Calculate delegation depth
    parent_depth = get_delegation_depth(parent_id)
    child_depth = parent_depth + 1
    
    # Register the new agent
    result = register_agent(
        agent_name=agent_name,
        agent_type=agent_type,
        created_by=parent_id,
        authority_source="delegated",
        scope=scope
    )
    
    child_id = result["agent_id"]
    
    # Create delegation record
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO delegations (delegation_id, parent_id, child_id, delegated_at, delegation_depth)
            VALUES (?, ?, ?, ?, ?)
        """, (generate_delegation_id(), parent_id, child_id, int(time.time()), child_depth))
        conn.commit()
    
    # Get full delegation chain
    chain = get_delegation_chain(child_id)
    
    return {
        "agent_id": child_id,
        "credentials": result["credentials"],
        "delegation_chain": chain,
        "delegation_depth": child_depth
    }


def get_delegation_depth(agent_id: str) -> int:
    """Get the delegation depth of an agent (0 = human-authorized)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT delegation_depth FROM delegations WHERE child_id = ?",
            (agent_id,)
        )
        row = cursor.fetchone()
        if row:
            return row["delegation_depth"]
    
    # If no delegation record, check if human-authorized
    agent = get_agent(agent_id)
    if agent and agent["authority_source"] == "human":
        return 0
    return 0


def get_delegation_chain(agent_id: str) -> list[dict]:
    """Get the full delegation chain for an agent."""
    chain = []
    current_id = agent_id
    
    while current_id:
        agent = get_agent(current_id)
        if not agent:
            break
        
        if current_id.startswith("user:") or current_id.startswith("human:"):
            chain.append({"type": "human", "id": current_id})
            break
        
        chain.append({
            "type": "agent",
            "id": current_id,
            "name": agent["agent_name"]
        })
        
        # Look for parent
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT parent_id FROM delegations WHERE child_id = ?",
                (current_id,)
            )
            row = cursor.fetchone()
            if row:
                current_id = row["parent_id"]
            else:
                # No parent in delegations, check created_by
                created_by = agent["created_by"]
                if created_by and (created_by.startswith("user:") or created_by.startswith("human:")):
                    chain.append({"type": "human", "id": created_by})
                break
    
    # Reverse to show human → agent order
    return list(reversed(chain))


def get_human_authority(agent_id: str) -> Optional[str]:
    """Trace back to find the human authority for an agent."""
    chain = get_delegation_chain(agent_id)
    for item in chain:
        if item["type"] == "human":
            return item["id"]
    return None


def log_action(
    agent_id: str,
    action: str,
    resource: Optional[str] = None,
    success: bool = True,
    metadata: Optional[dict] = None
) -> dict:
    """Log an agent action with full traceability."""
    log_id = generate_log_id()
    now = int(time.time())
    human_authority = get_human_authority(agent_id)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (
                log_id, agent_id, action, resource, timestamp,
                human_authority, success, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id, agent_id, action, resource, now,
            human_authority, int(success),
            json.dumps(metadata) if metadata else None
        ))
        conn.commit()
    
    return {
        "log_id": log_id,
        "human_authority": human_authority,
        "recorded_at": now
    }


def get_audit_trace(agent_id: str) -> dict:
    """Get full delegation chain and audit trail for an agent."""
    agent = get_agent(agent_id)
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")
    
    chain = get_delegation_chain(agent_id)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT log_id, action, resource, timestamp, success, metadata_json
            FROM audit_log
            WHERE agent_id = ?
            ORDER BY timestamp DESC
        """, (agent_id,))
        rows = cursor.fetchall()
    
    audit_trail = [
        {
            "log_id": row["log_id"],
            "action": row["action"],
            "resource": row["resource"],
            "timestamp": row["timestamp"],
            "success": bool(row["success"]),
            "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else None
        }
        for row in rows
    ]
    
    return {
        "agent_id": agent_id,
        "agent_name": agent["agent_name"],
        "lifecycle_state": agent["lifecycle_state"],
        "delegation_chain": chain,
        "delegation_depth": get_delegation_depth(agent_id),
        "scope": json.loads(agent["scope_json"]) if agent["scope_json"] else [],
        "audit_trail": audit_trail
    }


def check_scope(agent_id: str, required_action: str) -> bool:
    """Check if agent has the required action in scope."""
    scope = get_agent_scope(agent_id)
    return required_action in scope


def query_audit_logs(
    since_timestamp: Optional[int] = None,
    agent_id: Optional[str] = None,
    action: Optional[str] = None,
    human_authority: Optional[str] = None,
    limit: int = 100
) -> list[dict]:
    """Query audit logs with filters."""
    conditions = []
    params = []
    
    if since_timestamp:
        conditions.append("timestamp >= ?")
        params.append(since_timestamp)
    
    if agent_id:
        conditions.append("agent_id = ?")
        params.append(agent_id)
    
    if action:
        conditions.append("action = ?")
        params.append(action)
    
    if human_authority:
        conditions.append("human_authority = ?")
        params.append(human_authority)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT al.*, a.agent_name
            FROM audit_log al
            LEFT JOIN agents a ON al.agent_id = a.agent_id
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """, params + [limit])
        rows = cursor.fetchall()
    
    return [
        {
            "log_id": row["log_id"],
            "agent_id": row["agent_id"],
            "agent_name": row["agent_name"],
            "action": row["action"],
            "resource": row["resource"],
            "timestamp": row["timestamp"],
            "human_authority": row["human_authority"],
            "success": bool(row["success"])
        }
        for row in rows
    ]


def terminate_agent(agent_id: str, cascade: bool = True) -> dict:
    """Terminate an agent and optionally its children."""
    agent = get_agent(agent_id)
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")
    
    terminated = []
    
    with get_connection() as conn:
        cursor = conn.cursor()
        now = int(time.time())
        
        # Terminate the agent
        cursor.execute("""
            UPDATE agents SET lifecycle_state = 'terminated', terminated_at = ?
            WHERE agent_id = ?
        """, (now, agent_id))
        terminated.append(agent_id)
        
        if cascade:
            # Find all children recursively
            children_to_check = [agent_id]
            while children_to_check:
                current = children_to_check.pop()
                cursor.execute(
                    "SELECT child_id FROM delegations WHERE parent_id = ?",
                    (current,)
                )
                for row in cursor.fetchall():
                    child_id = row["child_id"]
                    cursor.execute("""
                        UPDATE agents SET lifecycle_state = 'terminated', terminated_at = ?
                        WHERE agent_id = ? AND lifecycle_state = 'active'
                    """, (now, child_id))
                    if cursor.rowcount > 0:
                        terminated.append(child_id)
                        children_to_check.append(child_id)
        
        conn.commit()
    
    return {
        "terminated": terminated,
        "count": len(terminated)
    }


def get_all_agents(include_terminated: bool = False) -> list[dict]:
    """Get all agents."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if include_terminated:
            cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")
        else:
            cursor.execute(
                "SELECT * FROM agents WHERE lifecycle_state = 'active' ORDER BY created_at DESC"
            )
        rows = cursor.fetchall()
    
    return [
        {
            **dict(row),
            "scope": json.loads(row["scope_json"]) if row["scope_json"] else []
        }
        for row in rows
    ]


def reset_database():
    """Reset the database (for demo purposes)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audit_log")
        cursor.execute("DELETE FROM delegations")
        cursor.execute("DELETE FROM agents")
        conn.commit()
