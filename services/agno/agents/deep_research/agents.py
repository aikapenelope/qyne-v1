"""
QYNE v1 — Research Agents.

Multi-provider deep research system: planner → parallel scouts → quality gate → synthesis.
Scouts are created conditionally based on available API keys.
"""

import os
from pathlib import Path

from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.file import FileTools
from agno.tools.websearch import WebSearchTools

from app.config import TOOL_MODEL, REASONING_MODEL, db, SKILLS_DIR
from app.shared import learning, compression
from app.models import ResearchReport

# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

_deep_search_skills = None
_deep_synthesis_skills = None

if SKILLS_DIR.exists():
    from agno.skills import Skills, LocalSkills

    _search_dirs = ["deep-search", "agent-ops"]
    _synth_dirs = ["deep-synthesis", "agent-ops"]

    loaders = [LocalSkills(str(SKILLS_DIR / d)) for d in _search_dirs if (SKILLS_DIR / d).exists()]
    if loaders:
        _deep_search_skills = Skills(loaders=loaders)

    loaders = [LocalSkills(str(SKILLS_DIR / d)) for d in _synth_dirs if (SKILLS_DIR / d).exists()]
    if loaders:
        _deep_synthesis_skills = Skills(loaders=loaders)


# ---------------------------------------------------------------------------
# Synthesis Agent (used by client_research_workflow)
# ---------------------------------------------------------------------------

synthesis_agent = Agent(
    name="Synthesis Agent",
    model=REASONING_MODEL,
    output_schema=ResearchReport,
    instructions=[
        "You receive research findings and internal knowledge context.",
        "Synthesize everything into a structured research report.",
        "Be concise, analytical, and cite sources.",
    ],
)


# ---------------------------------------------------------------------------
# Research Scouts (conditional on API keys)
# ---------------------------------------------------------------------------

research_scouts: list[tuple[str, Agent]] = []

# Scout: Tavily (AI-optimized search)
if os.getenv("TAVILY_API_KEY"):
    from agno.tools.tavily import TavilyTools

    _tavily_scout = Agent(
        name="Tavily Scout",
        role="AI-optimized web search for news, articles, and current information",
        model=TOOL_MODEL,
        tools=[TavilyTools()],
        tool_call_limit=3,
        retries=1,
        skills=_deep_search_skills,
        instructions=[
            "You are a research agent using Tavily (AI-optimized search).",
            "Follow the Research Planner's plan.",
            "Best for: news articles, blog posts, recent announcements.",
            "Output: FINDINGS with source URLs, then GAPS.",
        ],
        db=db,
        markdown=True,
        compression_manager=compression,
    )
    research_scouts.append(("Tavily Search", _tavily_scout))

# Scout: Exa (semantic search)
if os.getenv("EXA_API_KEY"):
    from agno.tools.exa import ExaTools

    _exa_scout = Agent(
        name="Exa Scout",
        role="Semantic search for research papers and deep web results",
        model=TOOL_MODEL,
        tools=[ExaTools()],
        tool_call_limit=3,
        retries=1,
        skills=_deep_search_skills,
        instructions=[
            "You are a research agent using Exa (semantic/neural search).",
            "Follow the Research Planner's plan.",
            "Best for: research papers, technical docs, niche content.",
            "Output: FINDINGS with source URLs, then GAPS.",
        ],
        db=db,
        markdown=True,
        compression_manager=compression,
    )
    research_scouts.append(("Exa Search", _exa_scout))

# Scout: Firecrawl (full page extraction)
if os.getenv("FIRECRAWL_API_KEY"):
    from agno.tools.firecrawl import FirecrawlTools

    _firecrawl_scout = Agent(
        name="Firecrawl Scout",
        role="Deep page extraction for detailed content and documentation",
        model=TOOL_MODEL,
        tools=[FirecrawlTools()],
        tool_call_limit=3,
        retries=1,
        skills=_deep_search_skills,
        instructions=[
            "You are a research agent using Firecrawl (deep page extraction).",
            "Follow the Research Planner's plan.",
            "Best for: documentation pages, GitHub READMEs, detailed articles.",
            "Output: FINDINGS with source URLs, then GAPS.",
        ],
        db=db,
        markdown=True,
        compression_manager=compression,
    )
    research_scouts.append(("Firecrawl Search", _firecrawl_scout))

# Scout: WebSearch (always available, free fallback)
websearch_scout = Agent(
    name="WebSearch Scout",
    role="General web search using DuckDuckGo as free fallback",
    model=TOOL_MODEL,
    tools=[WebSearchTools(fixed_max_results=8)],
    tool_call_limit=3,
    retries=1,
    skills=_deep_search_skills,
    instructions=[
        "You are a research agent using general web search.",
        "Follow the Research Planner's plan.",
        "Best for: general web results, community forums, broad coverage.",
        "Output: FINDINGS with source URLs, then GAPS.",
    ],
    db=db,
    markdown=True,
    compression_manager=compression,
)
research_scouts.append(("WebSearch", websearch_scout))

# Available scout names for the planner
available_scout_names = [name for name, _ in research_scouts]


# ---------------------------------------------------------------------------
# Research Planner
# ---------------------------------------------------------------------------

research_planner = Agent(
    name="Research Planner",
    role="Create a detailed research execution plan assigning work to available search agents",
    model=TOOL_MODEL,
    instructions=[
        "You are a research strategist. Given a topic, create a DETAILED execution plan",
        f"for {len(research_scouts)} parallel research agents.",
        "",
        f"## Available agents: {', '.join(available_scout_names)}",
        "",
        "## For EACH available agent, provide a section:",
        "AGENT_[NAME]:",
        "  QUERY: [compound search query with keywords and site: filters]",
        "  STRATEGY: [what this agent should focus on given its strengths]",
        "  EXTRACT: [specific data points to look for]",
        "",
        "## Rules",
        "- Assign DIFFERENT angles to each agent. No overlap.",
        "- Always include year (2025 or 2026) in queries for freshness",
        "- For Latam topics, include both English and Spanish queries",
    ],
    db=db,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Research Synthesizer
# ---------------------------------------------------------------------------

research_synthesizer = Agent(
    name="Research Synthesizer",
    role="Produce comprehensive research reports from collected findings",
    model=TOOL_MODEL,
    tools=[FileTools(base_dir=Path("/app/data/knowledge"))],
    tool_call_limit=5,
    skills=_deep_synthesis_skills,
    instructions=[
        "You synthesize research findings into a comprehensive markdown report.",
        "",
        "## Report Structure (follow exactly)",
        "### Executive Summary",
        "2-3 sentences. The key takeaway with the most important number.",
        "",
        "### Key Findings",
        "5-8 bullet points. Each with a specific fact, source URL, and analysis.",
        "",
        "### Analysis",
        "2-3 paragraphs connecting findings into a narrative.",
        "",
        "### Gaps and Uncertainties",
        "What data was unavailable? What claims have only one source?",
        "",
        "### Recommendations",
        "3-5 specific, actionable next steps tied to findings.",
        "",
        "### Sources",
        "All URLs cited, deduplicated.",
        "",
        "## Rules",
        "- Write in markdown, NOT JSON.",
        "- Every finding must have a source URL.",
        "- Write in Spanish if the topic is Latam-specific, English otherwise.",
        "- Save the report: research-<topic-slug>-<date>.md",
    ],
    db=db,
    learning=learning,
    markdown=True,
    compression_manager=compression,
)
