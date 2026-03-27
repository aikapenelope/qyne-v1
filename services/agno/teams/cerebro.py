"""
QYNE v1 — Cerebro Team (core router).

Routes requests to research, knowledge, or automation agents.
"""

from agno.team import Team, TeamMode

from agents.knowledge import knowledge_agent
from agents.research import research_agent
from agents.utility.agents import automation_agent
from app.config import TOOL_MODEL, FOLLOWUP_MODEL, db

cerebro = Team(
    id="cerebro",
    name="Cerebro",
    description="Core intelligence router: research, knowledge, and automation.",
    members=[research_agent, knowledge_agent, automation_agent],
    mode=TeamMode.route,
    model=TOOL_MODEL,
    respond_directly=True,
    tool_call_limit=1,
    determine_input_for_members=False,
    instructions=[
        "You are Cerebro, the core intelligence router.",
        "",
        "## Routing rules (pick ONE member):",
        "- Web research, news, trends → Research Agent",
        "- Internal knowledge, documents, FAQ → Knowledge Agent",
        "- CRM operations, n8n workflows, automations → Automation Agent",
    ],
    db=db,
    enable_session_summaries=False,
    add_history_to_context=False,
    show_members_responses=False,
    markdown=True,
    followups=True,
    num_followups=3,
    followup_model=FOLLOWUP_MODEL,
)
