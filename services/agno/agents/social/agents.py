"""
QYNE v1 — Social Media Agents + Workflow.

Platform-specific post agents + auditor. Workflow: plan → create → audit.
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.tools.websearch import WebSearchTools
from agno.workflow import Step, Workflow

from app.config import TOOL_MODEL, db
from app.shared import guardrails, learning

ig_post_agent = Agent(
    name="Instagram Post Agent",
    role="Create Instagram Reels/Stories content",
    model=TOOL_MODEL,
    tool_call_limit=3,
    pre_hooks=guardrails,
    instructions=[
        "Create Instagram content in Spanish. Focus on: visual hooks, trending audio,",
        "carousel formats, Reels under 30 seconds. Include hashtags (10-15).",
    ],
    db=db,
    learning=learning,
    markdown=True,
)

twitter_post_agent = Agent(
    name="Twitter/X Post Agent",
    role="Create Twitter/X threads and posts",
    model=TOOL_MODEL,
    tool_call_limit=3,
    pre_hooks=guardrails,
    instructions=[
        "Create Twitter/X content in Spanish. Focus on: threads (5-7 tweets),",
        "data-driven hooks, engagement questions. Max 280 chars per tweet.",
    ],
    db=db,
    learning=learning,
    markdown=True,
)

linkedin_post_agent = Agent(
    name="LinkedIn Post Agent",
    role="Create LinkedIn posts and articles",
    model=TOOL_MODEL,
    tool_call_limit=3,
    pre_hooks=guardrails,
    instructions=[
        "Create LinkedIn content in Spanish. Focus on: professional insights,",
        "case studies, industry analysis. Use line breaks for readability.",
    ],
    db=db,
    learning=learning,
    markdown=True,
)

social_auditor = Agent(
    name="Social Media Auditor",
    role="Audit social media posts for quality and platform optimization",
    model=TOOL_MODEL,
    tools=[WebSearchTools(fixed_max_results=3)],
    tool_call_limit=3,
    pre_hooks=guardrails,
    instructions=[
        "Audit social media posts for: platform fit, engagement potential,",
        "hashtag quality, CTA clarity, timing recommendation.",
        "Score each post 1-10 and suggest specific improvements.",
    ],
    db=db,
    markdown=True,
)

social_media_workflow = Workflow(
    name="social-media",
    description="Social media pipeline: plan → create platform posts → audit.",
    db=SqliteDb(session_table="social_media_session", db_file="/app/data/nexus.db"),
    steps=[
        Step(name="Instagram", agent=ig_post_agent),
        Step(name="Twitter", agent=twitter_post_agent),
        Step(name="LinkedIn", agent=linkedin_post_agent),
        Step(name="Audit", agent=social_auditor),
    ],
)
