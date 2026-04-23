"""
QYNE v1 — Pydantic Models for structured agent outputs.

These models enforce consistent output formats across agents.
Used with Agent(output_model=...) for typed responses.
"""

from pydantic import BaseModel, Field


class ResearchReport(BaseModel):
    """Structured research output for consistent reporting."""

    executive_summary: str = Field(description="2-3 sentence overview of findings")
    key_findings: list[str] = Field(description="List of key findings with sources")
    recommendations: list[str] = Field(description="Actionable next steps")
    sources: list[str] = Field(description="URLs and references used")
    confidence: str = Field(description="high, medium, or low confidence level")


class LeadReport(BaseModel):
    """Structured lead/client analysis for CRM integration."""

    company_name: str = Field(description="Company or person name")
    industry: str = Field(description="Industry or sector")
    score: int = Field(ge=1, le=10, description="Lead quality score 1-10")
    pain_points: list[str] = Field(description="Identified pain points or needs")
    next_steps: list[str] = Field(description="Recommended follow-up actions")
    notes: str = Field(description="Additional context or observations")


class TaskSummary(BaseModel):
    """Structured task output for automation tracking."""

    action: str = Field(description="What was done")
    status: str = Field(description="success, partial, or failed")
    details: str = Field(description="Details of the action taken")
    follow_up: list[str] = Field(default_factory=list, description="Follow-up items")


class ContentBrief(BaseModel):
    """Research brief for a content piece."""

    topic: str = Field(description="Topic title")
    pillar: str = Field(
        description="Content pillar (AI Trends, Tools, Business, Future, BTS)"
    )
    timeliness: str = Field(description="Why this topic matters right now")
    key_facts: list[str] = Field(
        description="Key facts with specific numbers and sources"
    )
    sources: list[str] = Field(description="Source URLs")
    angle: str = Field(description="Our unique perspective or take")
    hook_variants: list[str] = Field(
        description="2-3 hook options for the first 3 seconds"
    )
    visual_ideas: list[str] = Field(description="What to show on screen")
    relevance_score: int = Field(ge=1, le=10, description="Relevance to audience 1-10")


class VideoScene(BaseModel):
    """A single scene in a video storyboard."""

    text: str = Field(description="Narration text for this scene (Spanish)")
    visual: str = Field(
        description="Detailed image/visual description for generation"
    )
    duration_seconds: int = Field(ge=2, le=15, description="Scene duration in seconds")
    transition: str = Field(
        default="fade", description="Transition type: fade, slide, cut, zoom"
    )


class VideoStoryboard(BaseModel):
    """Complete video storyboard ready for Remotion rendering."""

    title: str = Field(description="Video title")
    hook: str = Field(description="Selected hook (first 3 seconds)")
    language: str = Field(default="es", description="Content language")
    total_duration_seconds: int = Field(description="Total video duration")
    scenes: list[VideoScene] = Field(description="Ordered list of scenes")
    hashtags: list[str] = Field(description="Platform hashtags")
    cta: str = Field(description="Call to action at the end")
    platform: str = Field(
        default="instagram_reels",
        description="Target platform: instagram_reels, tiktok",
    )
    style: dict = Field(
        default_factory=lambda: {
            "font": "Inter",
            "primary_color": "#1a1a2e",
            "accent_color": "#e94560",
        },
        description="Visual style configuration",
    )


class SupportTicket(BaseModel):
    """Structured support interaction for CRM logging and analytics."""

    product: str = Field(description="Product: docflow, aurora, or nova")
    intent: str = Field(
        description="Customer intent: faq, pricing, payment, complaint, "
        "technical_issue, appointment, document_status, subscription, other"
    )
    urgency: str = Field(description="low, medium, high, or critical")
    summary: str = Field(description="One-line summary of the customer request")
    resolution: str = Field(description="What was done or recommended")
    escalated: bool = Field(default=False, description="Whether escalated to human")
    lead_score: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Lead quality score 0-10 (0 = not a lead, 10 = ready to close)",
    )


class PaymentConfirmation(BaseModel):
    """Structured payment request requiring human approval."""

    product: str = Field(description="Product: docflow, aurora, or nova")
    client_name: str = Field(description="Client name as provided")
    amount: str = Field(description="Payment amount with currency (e.g., '$150 USD')")
    method: str = Field(
        description="Payment method: transfer, card, paypal, crypto, other"
    )
    reference: str = Field(
        default="", description="Payment reference or invoice number"
    )
    notes: str = Field(default="", description="Additional context about the payment")
