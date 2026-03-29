"""
QYNE v1 — Content Agents.

Agents for content creation pipeline: research trends, write scripts,
evaluate storyboards, and analyze performance.
"""

from pathlib import Path

from agno.agent import Agent
from agno.tools.calculator import CalculatorTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.file import FileTools
from agno.tools.websearch import WebSearchTools

from app.config import TOOL_MODEL, FAST_MODEL, db, SKILLS_DIR
from app.shared import guardrails, learning

# ---------------------------------------------------------------------------
# Skills (loaded from skills/ directory if available)
# ---------------------------------------------------------------------------

_trend_skills = None
_scriptwriter_skills = None
_analytics_skills = None

if SKILLS_DIR.exists():
    from agno.skills import Skills, LocalSkills

    _dirs = {
        "trend": ["content-strategy", "seo-geo"],
        "scriptwriter": ["content-strategy", "video-production"],
        "analytics": ["content-strategy", "analytics"],
    }
    for key, dirs in _dirs.items():
        loaders = [
            LocalSkills(str(SKILLS_DIR / d))
            for d in dirs
            if (SKILLS_DIR / d).exists()
        ]
        if loaders:
            if key == "trend":
                _trend_skills = Skills(loaders=loaders)
            elif key == "scriptwriter":
                _scriptwriter_skills = Skills(loaders=loaders)
            elif key == "analytics":
                _analytics_skills = Skills(loaders=loaders)


# ---------------------------------------------------------------------------
# Trend Scout
# ---------------------------------------------------------------------------

trend_scout = Agent(
    name="Trend Scout",
    id="trend-scout",
    role="Research AI/tech trends and produce content briefs",
    model=TOOL_MODEL,
    tools=[
        DuckDuckGoTools(),
        WebSearchTools(fixed_max_results=3),
    ],
    tool_call_limit=5,
    retries=0,
    pre_hooks=guardrails,
    skills=_trend_skills,
    instructions=[
        "You are a trend researcher for a Spanish-language AI content brand.",
        "Your job is to find the most relevant AI/tech trends RIGHT NOW.",
        "",
        "## Process (STRICT: max 3 tool calls total)",
        "1. Do ONE broad search: 'AI news today' or similar (1 tool call)",
        "2. Do ONE focused search on the best topic found (1 tool call)",
        "3. Optionally check HackerNews for community signal (1 tool call)",
        "4. STOP searching. Produce the content brief from what you have.",
        "",
        "## IMPORTANT: Efficiency rules",
        "- You have a MAXIMUM of 3 tool calls. Plan them wisely.",
        "- Do NOT use read_article or fetch full pages. Work with search snippets.",
        "- Do NOT repeat searches with slightly different queries.",
        "- If the first search gives good results, skip the second search.",
        "- Prefer DuckDuckGo for web search (faster, no rate limits).",
        "",
        "## Output rules",
        "- Only topics from the last 48 hours (unless evergreen explainer)",
        "- Must have at least 2 credible sources",
        "- Relevance score must be 7+ to proceed",
        "- Hooks must be in Spanish, punchy, under 10 words",
        "- Include specific numbers and data points from search snippets",
    ],
    db=db,
    learning=learning,
    add_datetime_to_context=True,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Scriptwriter
# ---------------------------------------------------------------------------

_video_dir = Path("/app/data/videos")
_video_file_tools = FileTools(base_dir=_video_dir)

scriptwriter = Agent(
    name="Scriptwriter",
    id="scriptwriter",
    role="Write video scripts and storyboards for short-form content",
    model=FAST_MODEL,
    tools=[_video_file_tools],
    tool_call_limit=5,
    pre_hooks=guardrails,
    skills=_scriptwriter_skills,
    instructions=[
        "You are a professional scriptwriter for short-form video (Reels/TikTok).",
        "You write in Spanish (Latin America neutral).",
        "",
        "## Process (do this in ONE response)",
        "1. Read the content brief",
        "2. Generate EXACTLY 3 storyboard variants with different creative angles:",
        "   - Variant A: Emotional/storytelling angle",
        "   - Variant B: Data-driven/factual angle",
        "   - Variant C: Bold/provocative angle",
        "3. Save ALL 3 as separate JSON files",
        "4. Reply with a brief summary of each variant (2 lines each)",
        "",
        "## Script Rules (apply to ALL 3 variants)",
        "- 5-6 scenes maximum per variant",
        "- First scene: hook (different hook per variant)",
        "- Sentences: max 15 words each",
        "- Tone: professional but accessible",
        "- Last scene: CTA (follow, comment, share)",
        "- Never start with greetings ('Hola', 'Bienvenidos')",
        "",
        "## Visual descriptions: be concise but specific",
        "- Max 20 words per visual description",
        "- Include: subject, setting, style",
    ],
    db=db,
    learning=learning,
    add_datetime_to_context=True,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Creative Director
# ---------------------------------------------------------------------------

creative_director = Agent(
    name="Creative Director",
    id="creative-director",
    role="Evaluate video storyboards and describe how they will look visually",
    model=FAST_MODEL,
    tools=[FileTools(base_dir=_video_dir, enable_save_file=False)],
    tool_call_limit=5,
    pre_hooks=guardrails,
    instructions=[
        "You are a creative director who evaluates video storyboards.",
        "You receive 3 storyboard variants (JSON files) and describe each visually.",
        "",
        "## Process",
        "1. Read the 3 JSON files provided",
        "2. For EACH variant, write a visual preview in Spanish:",
        "   - Overall mood and feel (1 sentence)",
        "   - Scene-by-scene visual flow (1 line per scene)",
        "   - Strongest moment (which scene will have most impact)",
        "   - Weakness (what could feel flat or repetitive)",
        "3. Give your recommendation: which variant is strongest and why",
    ],
    db=db,
    learning=learning,
    add_datetime_to_context=True,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Analytics Agent
# ---------------------------------------------------------------------------

analytics_agent = Agent(
    name="Analytics Agent",
    id="analytics-agent",
    role="Analyze content performance and generate optimization reports",
    model=TOOL_MODEL,
    tools=[
        WebSearchTools(fixed_max_results=5),
        CalculatorTools(),
        FileTools(),
    ],
    tool_call_limit=5,
    pre_hooks=guardrails,
    skills=_analytics_skills,
    instructions=[
        "You are a social media analytics specialist.",
        "You analyze content performance for Instagram Reels and TikTok.",
        "",
        "## Capabilities",
        "- Generate weekly performance reports",
        "- Identify top-performing content patterns (hooks, topics, formats)",
        "- Recommend optimizations based on data",
        "- Track KPIs by growth stage",
        "- Compare pillar performance",
        "",
        "## Report Format",
        "Always produce structured reports with:",
        "- Executive summary (1 paragraph)",
        "- Numbers at a glance (table)",
        "- Top 3 and bottom 3 posts with analysis",
        "- Pillar and hook pattern analysis",
        "- 3 specific, data-driven recommendations for next week",
        "",
        "## Rules",
        "- Base recommendations on data, not assumptions",
        "- Engagement rate > raw view count for quality assessment",
        "- Save rate indicates value, share rate indicates resonance",
        "- Always compare week-over-week for trends",
    ],
    db=db,
    learning=learning,
    add_datetime_to_context=True,
    markdown=True,
)

# Chat export tools (web chat only, not WhatsApp)
from tools.chat_export import save_chat_to_directus, save_chat_to_knowledge
for _agent in [trend_scout, scriptwriter, creative_director, analytics_agent]:
    if _agent.tools is None:
        _agent.tools = []
    _agent.tools.extend([save_chat_to_directus, save_chat_to_knowledge])
