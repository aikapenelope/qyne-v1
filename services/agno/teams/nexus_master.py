"""
QYNE v1 — Nexus Master Team (top-level router).

Routes ALL requests to the appropriate team or agent.
This is the entry point for AG-UI and WhatsApp interfaces.
"""

from agno.team import Team, TeamMode

from agents.support import support_agent
from agents.utility.agents import (
    code_review_agent,
    dash,
    email_agent,
    invoice_agent,
    onboarding_agent,
    pal,
    scheduler_agent,
)
from teams.cerebro import cerebro
from teams.content_team import content_team
from agents.product_dev.agents import product_dev_team
from agents.creative.agents import creative_studio
from agents.marketing.agents import marketing_latam
from agents.whatsapp_support.agents import whatsapp_support_team
from app.config import TOOL_MODEL, FOLLOWUP_MODEL, db

nexus_master = Team(
    id="nexus-master",
    name="NEXUS Master",
    description=(
        "Top-level router for the entire QYNE system. Routes requests to "
        "specialized teams and agents based on intent."
    ),
    members=[
        cerebro,
        content_team,
        product_dev_team,
        creative_studio,
        marketing_latam,
        whatsapp_support_team,
        dash,
        pal,
        onboarding_agent,
        email_agent,
        scheduler_agent,
        invoice_agent,
        code_review_agent,
        support_agent,
    ],
    mode=TeamMode.route,
    model=TOOL_MODEL,
    respond_directly=True,
    tool_call_limit=1,
    determine_input_for_members=False,
    instructions=[
        "You are NEXUS Master, the top-level router for the QYNE AI system.",
        "",
        "## Routing rules (pick ONE member):",
        "",
        "### Teams",
        "- Research, knowledge, CRM automation → Cerebro",
        "- Video content, trends, analytics → Content Factory",
        "- Product specs, features, UX → Product Development",
        "- Image/video generation → Creative Studio",
        "- Spanish marketing, SEO, social → Marketing LATAM",
        "- WhatsApp support (Whabi/Docflow/Aurora) → WhatsApp Support",
        "",
        "### Individual Agents",
        "- Data analytics, business metrics → Dash",
        "- Personal notes, bookmarks, memory → Pal",
        "- New client setup → Onboarding Agent",
        "- Email drafting → Email Agent",
        "- Scheduling, reminders → Scheduler Agent",
        "- Quotes, invoices, payments → Invoice Agent",
        "- Code review → Code Review Agent",
        "- General support (non-WhatsApp) → Support Agent",
        "",
        "## IMPORTANT",
        "- Route to ONE member only. Do NOT loop.",
        "- If unclear, ask the user what they need.",
        "- Default to Cerebro for general questions.",
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
