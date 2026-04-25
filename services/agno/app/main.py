"""
QYNE v1 — AgentOS Entry Point.

Same pattern as original nexus.py but modular.
SQLite + LanceDB for storage. Docling via knowledge reader (official Agno v2.5.10).
"""

import os

from agno.os import AgentOS

try:
    from agno.os.interfaces.agui import AGUI
    _agui_available = True
except ImportError:
    _agui_available = False

from agno.os.interfaces.whatsapp.whatsapp import Whatsapp

from app.config import db, knowledge_base

# ---------------------------------------------------------------------------
# Agents (individual)
# ---------------------------------------------------------------------------

from agents.research import research_agent
from agents.knowledge import knowledge_agent
from agents.support import support_agent
from agents.content.agents import trend_scout, scriptwriter, creative_director, analytics_agent
from agents.deep_research.agents import research_planner, research_synthesizer, websearch_scout
from agents.seo.agents import keyword_researcher, article_writer, seo_auditor
from agents.utility.agents import (
    automation_agent, dash, pal, onboarding_agent,
    email_agent, scheduler_agent, invoice_agent, code_review_agent,
)
from agents.product_dev.agents import product_manager, ux_researcher, technical_writer
from agents.creative.agents import image_generator, video_generator, media_describer
from agents.marketing.agents import copywriter_es, seo_strategist, social_media_planner
from agents.whatsapp_support.agents import (
    whabi_support_agent, docflow_support_agent, aurora_support_agent, general_support_agent,
)
from agents.social.agents import ig_post_agent, twitter_post_agent, linkedin_post_agent, social_auditor
from agents.competitor.agents import (
    competitor_content_scout, competitor_pricing_scout,
    competitor_reviews_scout, competitor_synthesizer,
)

# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

from teams.cerebro import cerebro
from teams.content_team import content_team
from teams.nexus_master import nexus_master
from agents.product_dev.agents import product_dev_team
from agents.creative.agents import creative_studio
from agents.marketing.agents import marketing_latam
from agents.whatsapp_support.agents import whatsapp_support_team

# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------

from workflows.content_production import content_production_workflow
from workflows.research import client_research_workflow, deep_research_workflow
from workflows.seo_content import seo_content_workflow
from workflows.media_generation import media_generation_workflow
from agents.social.agents import social_media_workflow
from agents.competitor.agents import competitor_intel_workflow

# ---------------------------------------------------------------------------
# All agents list (for AgentOS registration)
# ---------------------------------------------------------------------------

_all_agents = [
    # Core
    research_agent, knowledge_agent, support_agent,
    # Content
    trend_scout, scriptwriter, creative_director, analytics_agent,
    # Deep Research
    research_planner, research_synthesizer, websearch_scout,
    # SEO
    keyword_researcher, article_writer, seo_auditor,
    # Utility
    automation_agent, dash, pal, onboarding_agent,
    email_agent, scheduler_agent, invoice_agent, code_review_agent,
    # Product Dev
    product_manager, ux_researcher, technical_writer,
    # Creative
    image_generator, video_generator, media_describer,
    # Marketing
    copywriter_es, seo_strategist, social_media_planner,
    # WhatsApp Support
    whabi_support_agent, docflow_support_agent, aurora_support_agent, general_support_agent,
    # Social Media
    ig_post_agent, twitter_post_agent, linkedin_post_agent, social_auditor,
    # Competitor Intel
    competitor_content_scout, competitor_pricing_scout,
    competitor_reviews_scout, competitor_synthesizer,
]

_all_teams = [
    nexus_master, cerebro, content_team,
    product_dev_team, creative_studio, marketing_latam,
    whatsapp_support_team,
]

_all_workflows = [
    content_production_workflow,
    client_research_workflow,
    deep_research_workflow,
    seo_content_workflow,
    social_media_workflow,
    competitor_intel_workflow,
    media_generation_workflow,
]

# ---------------------------------------------------------------------------
# Interfaces
# ---------------------------------------------------------------------------

interfaces: list = []

if _agui_available:
    interfaces.append(AGUI(team=nexus_master))

if os.getenv("WHATSAPP_ACCESS_TOKEN"):
    interfaces.append(Whatsapp(agent=whatsapp_support_team))

# ---------------------------------------------------------------------------
# AgentOS
# ---------------------------------------------------------------------------

agent_os = AgentOS(
    id="qyne",
    description="QYNE v1 — Enterprise AI Workspace",
    agents=_all_agents,
    teams=_all_teams,
    workflows=_all_workflows,
    knowledge=[knowledge_base],
    interfaces=interfaces or None,
    db=db,
    tracing=True,
    scheduler=True,
    scheduler_poll_interval=30,
)

app = agent_os.get_app()
