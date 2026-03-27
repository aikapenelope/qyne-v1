"""
QYNE v1 — Marketing LATAM Team.

Spanish copywriting, SEO strategy, and social media planning for Latin America.
"""

from agno.agent import Agent
from agno.team import Team, TeamMode
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.websearch import WebSearchTools

from app.config import TOOL_MODEL, db, SKILLS_DIR
from app.shared import guardrails, learning

_skills = None
if SKILLS_DIR.exists():
    from agno.skills import Skills, LocalSkills
    loaders = [
        LocalSkills(str(SKILLS_DIR / d))
        for d in ["copywriting-es", "seo-geo", "content-strategy"]
        if (SKILLS_DIR / d).exists()
    ]
    if loaders:
        _skills = Skills(loaders=loaders)

copywriter_es = Agent(
    name="Copywriter ES",
    role="Write persuasive copy in Spanish for Latin America",
    model=TOOL_MODEL,
    tool_call_limit=3,
    pre_hooks=guardrails,
    skills=_skills,
    instructions=[
        "You write persuasive copy in Spanish (Latin America neutral).",
        "Tone: professional but warm. No 'vosotros'. Use 'tu' for informal, 'usted' for formal.",
        "Formats: landing pages, email sequences, ad copy, social posts.",
    ],
    db=db,
    learning=learning,
    markdown=True,
)

seo_strategist = Agent(
    name="SEO Strategist",
    role="Develop SEO and GEO strategies for Spanish-language content",
    model=TOOL_MODEL,
    tools=[DuckDuckGoTools(), WebSearchTools(fixed_max_results=5)],
    tool_call_limit=5,
    pre_hooks=guardrails,
    skills=_skills,
    instructions=[
        "You develop SEO and GEO strategies for Spanish-language content.",
        "Focus on: keyword gaps, AI citation potential, competitor analysis.",
        "Always include both Google SEO and AI engine (ChatGPT/Perplexity) optimization.",
    ],
    db=db,
    learning=learning,
    markdown=True,
)

social_media_planner = Agent(
    name="Social Media Planner",
    role="Plan social media content calendars and campaigns",
    model=TOOL_MODEL,
    tools=[WebSearchTools(fixed_max_results=3)],
    tool_call_limit=3,
    pre_hooks=guardrails,
    skills=_skills,
    instructions=[
        "You plan social media content for Instagram, TikTok, LinkedIn, and X.",
        "Create weekly content calendars with: post type, topic, hook, CTA, hashtags.",
        "Optimize for each platform's algorithm and audience behavior.",
    ],
    db=db,
    learning=learning,
    markdown=True,
)

marketing_latam = Team(
    id="marketing-latam",
    name="Marketing LATAM",
    description="Spanish-language marketing: copywriting, SEO, social media planning.",
    members=[copywriter_es, seo_strategist, social_media_planner],
    mode=TeamMode.coordinate,
    model=TOOL_MODEL,
    max_iterations=3,
    instructions=[
        "You lead the Marketing LATAM team.",
        "Coordinate between copywriter, SEO strategist, and social media planner.",
        "All content must be in Spanish (Latin America neutral).",
    ],
    db=db,
    markdown=True,
)
