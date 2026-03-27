"""
NEXUS Cerebro — AgentOS Entry Point.

Production entry point that registers all agents, teams, and workflows.
Uses PostgreSQL + pgvector (configured in app.config).
"""

import os

from agno.os import AgentOS

try:
    from agno.os.interfaces.agui import AGUI

    _agui_available = True
except ImportError:
    _agui_available = False

from agno.os.interfaces.whatsapp.whatsapp import Whatsapp

from app.config import (
    db,
    knowledge_base,
    whabi_knowledge,
    docflow_knowledge,
    aurora_knowledge,
    learnings_knowledge,
    load_initial_knowledge,
)

# Load initial knowledge documents from knowledge/ folder (first startup only)
load_initial_knowledge()

# Import modular agents (production-ready, PostgreSQL-native)
from agents.research import research_agent
from agents.knowledge import knowledge_agent
from agents.support import support_agent

# ---------------------------------------------------------------------------
# Interfaces
# ---------------------------------------------------------------------------

interfaces: list = []

if _agui_available:
    interfaces.append(AGUI())

if os.getenv("WHATSAPP_ACCESS_TOKEN"):
    interfaces.append(Whatsapp(agent=support_agent))

# ---------------------------------------------------------------------------
# AgentOS
# ---------------------------------------------------------------------------

agent_os = AgentOS(
    id="nexus",
    description="NEXUS Cerebro Corporativo — Enterprise AI Workspace",
    agents=[
        research_agent,
        knowledge_agent,
        support_agent,
    ],
    teams=[],
    workflows=[],
    knowledge=[knowledge_base, whabi_knowledge, docflow_knowledge, aurora_knowledge],
    interfaces=interfaces or None,
    db=db,
    tracing=True,
    scheduler=True,
    scheduler_poll_interval=30,
)

app = agent_os.get_app()
