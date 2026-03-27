"""
QYNE v1 — Content Team.

Routes content requests to the right specialist agent.
For full production pipeline, use content_production_workflow instead.
"""

from agno.team import Team, TeamMode

from agents.content.agents import trend_scout, scriptwriter, analytics_agent
from app.config import TOOL_MODEL, FOLLOWUP_MODEL, db

content_team = Team(
    id="content-factory",
    name="Content Factory",
    description="Video content production team for Instagram Reels and TikTok",
    mode=TeamMode.route,
    respond_directly=True,
    tool_call_limit=1,
    members=[trend_scout, scriptwriter, analytics_agent],
    model=TOOL_MODEL,
    determine_input_for_members=False,
    instructions=[
        "You are the Content Factory router.",
        "",
        "## Routing rules (pick ONE member, do NOT loop):",
        "- If the user asks to CREATE a video/content: route to Trend Scout.",
        "- If the user asks about ANALYTICS/metrics/performance: route to Analytics Agent.",
        "- If the user asks to WRITE a script from an existing brief: route to Scriptwriter.",
        "",
        "## For full video production (research + script):",
        "Tell the user: 'Use the content-production workflow for the full pipeline.'",
    ],
    db=db,
    enable_session_summaries=False,
    add_history_to_context=False,
    show_members_responses=False,
    add_datetime_to_context=False,
    markdown=True,
    followups=True,
    num_followups=3,
    followup_model=FOLLOWUP_MODEL,
)
