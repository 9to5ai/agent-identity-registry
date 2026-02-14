#!/usr/bin/env python3
"""
Agent Identity Registry - Demo Scenario

This script demonstrates the core concepts:
1. Human (Jun) authorizes Agent A ("DataAnalyzer")
2. Agent A spawns Agent B ("ReportGenerator")
3. Agent B spawns Agent C ("ChartMaker")
4. Each agent performs actions - all logged with delegation chain
5. Forensic queries trace everything back to Jun

Run: python demo.py [--base-url http://localhost:8000]
"""

import argparse
import json
import sys
import time
from datetime import datetime
import requests

# ANSI colors for nice output
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(text: str):
    print(f"\n{BOLD}{BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{RESET}\n")


def print_step(step: int, text: str):
    print(f"{BOLD}{GREEN}[Step {step}]{RESET} {text}")


def print_result(data: dict, indent: int = 2):
    print(f"{YELLOW}{json.dumps(data, indent=indent)}{RESET}")


def print_error(text: str):
    print(f"{RED}ERROR: {text}{RESET}")
    sys.exit(1)


def run_demo(base_url: str):
    """Run the full demo scenario."""
    
    print_header("Agent Identity Registry - Demo Scenario")
    print(f"Target: {base_url}")
    print(f"Time: {datetime.now().isoformat()}")
    
    # Reset database for clean demo
    print_step(0, "Resetting database for clean demo...")
    r = requests.post(f"{base_url}/admin/reset")
    if r.status_code != 200:
        print_error(f"Failed to reset: {r.text}")
    print("  ✓ Database reset\n")
    
    # Step 1: Human (Jun) registers Agent A
    print_header("PHASE 1: Agent Registration")
    print_step(1, "Human (Jun) authorizes Agent A ('DataAnalyzer')")
    print("  → Jun wants to analyze customer data")
    print("  → Scope: read:database, write:reports, create:charts\n")
    
    agent_a_request = {
        "agent_name": "DataAnalyzer",
        "agent_type": "autonomous",
        "created_by": "user:jun@apra.gov.au",
        "authority_source": "human",
        "scope": ["read:database", "write:reports", "create:charts"]
    }
    
    r = requests.post(f"{base_url}/agents/register", json=agent_a_request)
    if r.status_code != 200:
        print_error(f"Failed to register Agent A: {r.text}")
    
    agent_a = r.json()
    print("  Response:")
    print_result(agent_a)
    print(f"\n  ✓ Agent A registered with ID: {BOLD}{agent_a['agent_id']}{RESET}")
    
    # Step 2: Agent A spawns Agent B
    print_header("PHASE 2: Delegation Chain")
    print_step(2, "Agent A spawns Agent B ('ReportGenerator')")
    print("  → Agent A needs help generating reports")
    print("  → Scope: write:reports (subset of A's scope)\n")
    
    agent_b_request = {
        "agent_name": "ReportGenerator",
        "agent_type": "semi-autonomous",
        "scope": ["write:reports"]
    }
    
    r = requests.post(
        f"{base_url}/agents/{agent_a['agent_id']}/spawn",
        json=agent_b_request
    )
    if r.status_code != 200:
        print_error(f"Failed to spawn Agent B: {r.text}")
    
    agent_b = r.json()
    print("  Response:")
    print_result(agent_b)
    print(f"\n  ✓ Agent B spawned with delegation depth: {agent_b['delegation_depth']}")
    print(f"  ✓ Delegation chain: {' → '.join([c['id'] if c['type'] == 'human' else c['name'] for c in agent_b['delegation_chain']])}")
    
    # Step 3: Agent B spawns Agent C
    print_step(3, "Agent B spawns Agent C ('ChartMaker')")
    print("  → Agent B needs help creating charts")
    print("  → BUT Agent B only has 'write:reports' scope...")
    
    # First, try with invalid scope (should fail)
    print("\n  → First, try requesting 'create:charts' (outside B's scope):\n")
    
    agent_c_invalid = {
        "agent_name": "ChartMaker",
        "agent_type": "tool",
        "scope": ["create:charts"]  # NOT in B's scope!
    }
    
    r = requests.post(
        f"{base_url}/agents/{agent_b['agent_id']}/spawn",
        json=agent_c_invalid
    )
    
    print(f"  {RED}Response (expected failure):{RESET}")
    print_result(r.json())
    print(f"\n  ✓ {BOLD}Scope attenuation enforced!{RESET} Agent C can't have more permissions than B")
    
    # Now spawn correctly with Agent A (which has create:charts)
    print("\n  → Now let's have Agent A spawn Agent C directly:\n")
    
    agent_c_request = {
        "agent_name": "ChartMaker",
        "agent_type": "tool",
        "scope": ["create:charts"]
    }
    
    r = requests.post(
        f"{base_url}/agents/{agent_a['agent_id']}/spawn",
        json=agent_c_request
    )
    if r.status_code != 200:
        print_error(f"Failed to spawn Agent C: {r.text}")
    
    agent_c = r.json()
    print("  Response:")
    print_result(agent_c)
    print(f"\n  ✓ Agent C spawned successfully from Agent A")
    
    # Step 4: Log actions
    print_header("PHASE 3: Agent Actions (Audit Trail)")
    
    actions = [
        (agent_a['agent_id'], "read:database", "customers_table", "Agent A reads customer database"),
        (agent_a['agent_id'], "read:database", "transactions_table", "Agent A reads transactions"),
        (agent_b['agent_id'], "write:reports", "quarterly_report.pdf", "Agent B generates Q1 report"),
        (agent_c['agent_id'], "create:charts", "sales_chart.png", "Agent C creates sales chart"),
        (agent_a['agent_id'], "write:reports", "final_analysis.pdf", "Agent A compiles final analysis"),
    ]
    
    for i, (agent_id, action, resource, desc) in enumerate(actions, 1):
        print_step(3 + i, desc)
        
        log_request = {
            "agent_id": agent_id,
            "action": action,
            "resource": resource,
            "success": True
        }
        
        r = requests.post(f"{base_url}/audit/log", json=log_request)
        if r.status_code != 200:
            print_error(f"Failed to log action: {r.text}")
        
        result = r.json()
        print(f"  → Action: {action}")
        print(f"  → Resource: {resource}")
        print(f"  → Human authority traced: {BOLD}{result['human_authority']}{RESET}")
        print()
    
    # Step 5: Forensic queries
    print_header("PHASE 4: Forensic Queries")
    
    print_step(9, "Query: 'Show me Agent C's full audit trace'")
    print("  → Who authorized Agent C? What has it done?\n")
    
    r = requests.get(f"{base_url}/audit/trace/{agent_c['agent_id']}")
    if r.status_code != 200:
        print_error(f"Failed to get audit trace: {r.text}")
    
    trace = r.json()
    print("  Delegation Chain:")
    for i, link in enumerate(trace['delegation_chain']):
        prefix = "  └─" if i == len(trace['delegation_chain']) - 1 else "  ├─"
        if link['type'] == 'human':
            print(f"  {prefix} 👤 {link['id']}")
        else:
            print(f"  {prefix} 🤖 {link['name']} ({link['id'][:16]}...)")
    
    print(f"\n  ✓ Every action by Agent C traces back to: {BOLD}user:jun@apra.gov.au{RESET}")
    
    print_step(10, "Query: 'Show all actions authorized by Jun'")
    r = requests.get(f"{base_url}/audit/query", params={"human_authority": "user:jun@apra.gov.au"})
    if r.status_code != 200:
        print_error(f"Failed to query: {r.text}")
    
    logs = r.json()
    print(f"\n  Found {len(logs)} actions authorized by Jun:\n")
    for log in logs:
        print(f"  • [{log['action']}] {log['resource'] or 'N/A'} by {log['agent_name']}")
    
    print()
    
    # Final summary
    print_header("DEMO COMPLETE")
    
    r = requests.get(f"{base_url}/admin/stats")
    stats = r.json()
    
    print(f"""
  {BOLD}Summary:{RESET}
  • Agents registered: {stats['agents']['total']}
  • Actions logged: {stats['audit_logs']['total']}
  • All actions trace back to human authority
  
  {BOLD}Key Concepts Demonstrated:{RESET}
  ✓ Agent Identity: Each agent has unique ID (not shared API keys)
  ✓ Delegation: Sub-agents inherit bounded authority from parents
  ✓ Scope Attenuation: Child can't have MORE permissions than parent
  ✓ Audit Trail: Every action logged with delegation chain
  ✓ Forensic Queries: Can trace any action to human authority
  
  {BOLD}Explore the API:{RESET}
  • Swagger docs: {base_url}/docs
  • Agent list: {base_url}/agents
  • Audit logs: {base_url}/audit/query
""")


def main():
    parser = argparse.ArgumentParser(description="Agent Identity Registry Demo")
    parser.add_argument(
        "--base-url", "-u",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)"
    )
    args = parser.parse_args()
    
    # Check if server is running
    try:
        r = requests.get(f"{args.base_url}/health", timeout=5)
        if r.status_code != 200:
            print_error(f"Server not healthy: {r.status_code}")
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to {args.base_url}. Is the server running?")
    
    run_demo(args.base_url)


if __name__ == "__main__":
    main()
