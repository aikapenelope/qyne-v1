"""
QYNE v1 — Competitor Intelligence Agents + Workflow.

Content, pricing, and reviews scouts → synthesis report.
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.websearch import WebSearchTools
from agno.workflow import Parallel, Step, Workflow

from app.config import TOOL_MODEL, db
from app.shared import guardrails, learning, compression

competitor_content_scout = Agent(
    name="Competitor Content Scout",
    role="Analyze competitor content strategy and positioning",
    model=TOOL_MODEL,
    tools=[DuckDuckGoTools(), WebSearchTools(fixed_max_results=5)],
    tool_call_limit=5,
    pre_hooks=guardrails,
    instructions=[
        "Analyze competitor content: blog posts, social media, videos.",
        "Report: topics covered, posting frequency, engagement levels, gaps.",
    ],
    db=db,
    markdown=True,
    compression_manager=compression,
)

competitor_pricing_scout = Agent(
    name="Competitor Pricing Scout",
    role="Research competitor pricing and packaging",
    model=TOOL_MODEL,
    tools=[DuckDuckGoTools(), WebSearchTools(fixed_max_results=5)],
    tool_call_limit=5,
    pre_hooks=guardrails,
    instructions=[
        "Research competitor pricing pages and plans.",
        "Report: plan names, prices, features per tier, free trial availability.",
    ],
    db=db,
    markdown=True,
    compression_manager=compression,
)

competitor_reviews_scout = Agent(
    name="Competitor Reviews Scout",
    role="Gather and analyze competitor reviews and sentiment",
    model=TOOL_MODEL,
    tools=[DuckDuckGoTools(), WebSearchTools(fixed_max_results=5)],
    tool_call_limit=5,
    pre_hooks=guardrails,
    instructions=[
        "Find competitor reviews on G2, Capterra, ProductHunt, Reddit.",
        "Report: common praise, common complaints, NPS indicators, feature requests.",
    ],
    db=db,
    markdown=True,
    compression_manager=compression,
)

competitor_synthesizer = Agent(
    name="Competitor Synthesizer",
    role="Synthesize competitor intelligence into actionable report",
    model=TOOL_MODEL,
    tool_call_limit=3,
    instructions=[
        "Synthesize all competitor findings into a structured report:",
        "1. Competitive landscape overview",
        "2. Pricing comparison table",
        "3. Content strategy gaps (opportunities for us)",
        "4. Customer sentiment analysis",
        "5. Recommended actions (3-5 specific steps)",
    ],
    db=db,
    learning=learning,
    markdown=True,
)

competitor_intel_workflow = Workflow(
    name="competitor-intel",
    description="Competitor intelligence: parallel scouts (content + pricing + reviews) → synthesis.",
    db=SqliteDb(session_table="competitor_intel_session", db_file="/app/data/nexus.db"),
    steps=[
        Parallel(
            Step(name="Content Analysis", agent=competitor_content_scout, skip_on_failure=True),
            Step(name="Pricing Research", agent=competitor_pricing_scout, skip_on_failure=True),
            Step(name="Reviews Analysis", agent=competitor_reviews_scout, skip_on_failure=True),
            name="Parallel Intel",
        ),
        Step(name="Synthesis", agent=competitor_synthesizer),
    ],
)
