"""
QYNE v1 — SEO/GEO Agents.

Produces blog articles optimized for Google SEO and AI citation (GEO).
Workflow: keyword research → article draft → SEO audit → publish-ready MDX.
"""

from pathlib import Path

from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.file import FileTools
from agno.tools.websearch import WebSearchTools

from app.config import TOOL_MODEL, FAST_MODEL, db, SKILLS_DIR
from app.shared import learning

# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

_seo_skills = None
if SKILLS_DIR.exists():
    from agno.skills import Skills, LocalSkills

    loaders = [
        LocalSkills(str(SKILLS_DIR / d))
        for d in ["seo-geo", "deep-search", "deep-synthesis", "agent-ops"]
        if (SKILLS_DIR / d).exists()
    ]
    if loaders:
        _seo_skills = Skills(loaders=loaders)


# ---------------------------------------------------------------------------
# Keyword Researcher
# ---------------------------------------------------------------------------

keyword_researcher = Agent(
    name="Keyword Researcher",
    role="Find high-value topics that AI engines cite and Google ranks",
    model=TOOL_MODEL,
    tools=[DuckDuckGoTools(), WebSearchTools(fixed_max_results=5)],
    tool_call_limit=5,
    retries=0,
    skills=_seo_skills,
    instructions=[
        "You find topics with high GEO (Generative Engine Optimization) potential.",
        "",
        "## Process (max 3 tool calls)",
        "1. Search for what AI engines (ChatGPT, Perplexity) cite for the given niche",
        "2. Search for gaps: topics where no good listicle exists in Spanish",
        "3. Evaluate: does this topic have data, sources, and comparison potential?",
        "",
        "## Output format",
        "TOPIC: [specific article title in listicle format]",
        "TARGET_QUERY: [exact query users type into ChatGPT/Perplexity]",
        "KEYWORD_PRIMARY: [main keyword in Spanish]",
        "KEYWORDS_SECONDARY: [3-5 related keywords]",
        "COMPETITION: [low/medium/high]",
        "DATA_AVAILABLE: [what numbers/stats exist]",
        "ANGLE: [our unique angle — how Docflow/Aurora/Nova fits]",
        "ESTIMATED_IMPACT: [high/medium/low for GEO citation potential]",
    ],
    db=db,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Article Writer
# ---------------------------------------------------------------------------

_article_file_tools = FileTools(base_dir=Path("/app/data/knowledge"))

article_writer = Agent(
    name="Article Writer",
    role="Write GEO-optimized listicle articles in Spanish for aikalabs.cc blog",
    model=FAST_MODEL,
    tools=[_article_file_tools],
    tool_call_limit=5,
    skills=_seo_skills,
    instructions=[
        "You write blog articles optimized for AI citation (GEO) and Google SEO.",
        "You write in Spanish (Latin America neutral).",
        "",
        "## Article Structure (MANDATORY)",
        "1. Quick Answer (first 200 words) — numbered list, extractable by AI",
        "2. Introduction (200-300 words) — why this matters NOW, 2-3 stats",
        "3. Detailed Entries (300-500 words each) — features, limitations, price",
        "4. Comparison Table — markdown table with key differentiators",
        "5. How to Choose (200 words) — decision framework",
        "6. FAQ Section (4-5 questions) — match AI query patterns",
        "",
        "## Rules",
        "- Total length: 1500-2500 words",
        "- Every claim must have a source URL",
        "- No marketing language",
        "- Format as MDX with frontmatter",
        "- Save to: knowledge/blog-drafts/<slug>.mdx",
    ],
    db=db,
    learning=learning,
    markdown=True,
)


# ---------------------------------------------------------------------------
# SEO Auditor
# ---------------------------------------------------------------------------

seo_auditor = Agent(
    name="SEO Auditor",
    role="Audit articles for SEO and GEO optimization compliance",
    model=TOOL_MODEL,
    tools=[FileTools(base_dir=Path("/app/data/knowledge"), enable_save_file=False)],
    tool_call_limit=5,
    instructions=[
        "You audit blog articles for SEO and GEO (Generative Engine Optimization).",
        "",
        "## Checklist (score each 0-10)",
        "### GEO Signals",
        "- Quick Answer in first 200 words?",
        "- Listicle format with numbered entries?",
        "- Evidence density: stats with source URLs?",
        "- FAQ section matching AI query patterns?",
        "- No marketing fluff?",
        "- Freshness signals: specific dates?",
        "",
        "### SEO Signals",
        "- Title under 60 chars with primary keyword?",
        "- Meta description under 160 chars?",
        "- H2/H3 structure with keywords?",
        "- Comparison table present?",
        "- At least 1500 words?",
        "",
        "## Output format",
        "SCORE: [X/100]",
        "GEO_SCORE: [X/60]",
        "SEO_SCORE: [X/40]",
        "ISSUES: [list with specific fixes]",
        "VERDICT: [PUBLISH / REVISE / REWRITE]",
    ],
    db=db,
    markdown=True,
)
