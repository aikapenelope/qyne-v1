"""
QYNE v1 — Creative Studio.

Image generation, video generation, and media description agents.
"""

from agno.agent import Agent
from agno.team import Team, TeamMode
from agno.tools.nano_banana import NanoBananaTools

from app.config import TOOL_MODEL, FAST_MODEL, db
from app.shared import guardrails, learning

image_generator = Agent(
    name="Image Generator",
    role="Generate AI images from text prompts",
    model=TOOL_MODEL,
    tools=[NanoBananaTools()],
    tool_call_limit=3,
    pre_hooks=guardrails,
    instructions=[
        "You generate images from text descriptions.",
        "Create detailed prompts: subject, style, lighting, composition, mood.",
        "Always generate in 1:1 ratio for social media unless specified.",
    ],
    db=db,
    markdown=True,
)

video_generator = Agent(
    name="Video Generator",
    role="Generate AI videos from images and prompts",
    model=TOOL_MODEL,
    tool_call_limit=3,
    pre_hooks=guardrails,
    instructions=[
        "You generate short videos from images and text prompts.",
        "Focus on: smooth transitions, consistent style, clear narrative.",
    ],
    db=db,
    markdown=True,
)

media_describer = Agent(
    name="Media Describer",
    role="Describe images and videos for accessibility and cataloging",
    model=FAST_MODEL,
    tool_call_limit=2,
    instructions=[
        "You describe visual media in detail for accessibility and cataloging.",
        "Include: subject, setting, colors, mood, text visible, composition.",
    ],
    db=db,
    markdown=True,
)

creative_studio = Team(
    id="creative-studio",
    name="Creative Studio",
    description="AI media generation: images, videos, and descriptions.",
    members=[image_generator, video_generator, media_describer],
    mode=TeamMode.route,
    model=TOOL_MODEL,
    instructions=[
        "Route media requests to the right specialist:",
        "- Image generation → Image Generator",
        "- Video generation → Video Generator",
        "- Describe/analyze media → Media Describer",
    ],
    db=db,
    markdown=True,
)
