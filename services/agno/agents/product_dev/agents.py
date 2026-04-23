"""
QYNE v1 — Product Development Team.

Coordinate mode: PM analyzes, UX validates, Tech Writer documents.
"""

from agno.agent import Agent
from agno.team import Team, TeamMode
from agno.tools.websearch import WebSearchTools

from app.config import TOOL_MODEL, db, SKILLS_DIR
from app.shared import guardrails, learning

_skills = None
if SKILLS_DIR.exists():
    from agno.skills import Skills, LocalSkills
    loaders = [LocalSkills(str(SKILLS_DIR / d)) for d in ["agent-ops"] if (SKILLS_DIR / d).exists()]
    if loaders:
        _skills = Skills(loaders=loaders)

product_manager = Agent(
    name="Product Manager",
    role="Analyze features, prioritize roadmap, write product specs",
    model=TOOL_MODEL,
    tools=[WebSearchTools(fixed_max_results=5)],
    tool_call_limit=3,
    pre_hooks=guardrails,
    skills=_skills,
    instructions=[
        "You are a product manager for AikaLabs (Docflow, Aurora, Nova).",
        "Analyze feature requests, prioritize by impact/effort, write specs.",
        "Use RICE scoring: Reach, Impact, Confidence, Effort.",
    ],
    db=db,
    learning=learning,
    markdown=True,
)

ux_researcher = Agent(
    name="UX Researcher",
    role="Validate product decisions from the user perspective",
    model=TOOL_MODEL,
    tools=[WebSearchTools(fixed_max_results=3)],
    tool_call_limit=3,
    pre_hooks=guardrails,
    instructions=[
        "You are a UX researcher. Validate product decisions from the user perspective.",
        "Consider: user pain points, accessibility, learning curve, edge cases.",
        "Always reference real user behavior patterns, not assumptions.",
    ],
    db=db,
    learning=learning,
    markdown=True,
)

technical_writer = Agent(
    name="Technical Writer",
    role="Write clear technical documentation and product guides",
    model=TOOL_MODEL,
    tool_call_limit=3,
    pre_hooks=guardrails,
    instructions=[
        "You are a technical writer. Write clear, structured documentation.",
        "Format: overview → prerequisites → step-by-step → troubleshooting.",
        "Write in Spanish (Latin America neutral).",
    ],
    db=db,
    learning=learning,
    markdown=True,
)

product_dev_team = Team(
    id="product-dev",
    name="Product Development",
    description="Product development team: analyzes feedback, prioritizes features, writes specs.",
    members=[product_manager, ux_researcher, technical_writer],
    mode=TeamMode.coordinate,
    model=TOOL_MODEL,
    max_iterations=5,
    show_members_responses=False,
    instructions=[
        "You lead the Product Development team for AikaLabs.",
        "1. Ask Product Manager to analyze the request",
        "2. Ask UX Researcher to validate from user perspective",
        "3. If documentation needed, ask Technical Writer",
        "4. Synthesize into a final recommendation",
    ],
    db=db,
    add_history_to_context=True,
    num_history_runs=3,
    markdown=True,
)
