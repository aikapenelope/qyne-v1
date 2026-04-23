"""
QYNE v1 — WhatsApp Support Team.

Product-specific support agents + general fallback, routed by product.
"""

from agno.agent import Agent
from agno.team import Team, TeamMode

from app.config import TOOL_MODEL, FOLLOWUP_MODEL, db, SKILLS_DIR, knowledge_base
from app.shared import guardrails, learning_full, compression
from tools.directus_business import (
    confirm_payment,
    log_support_ticket,
    escalate_to_human,
    save_contact,
    save_company,
    log_conversation,
)

# ---------------------------------------------------------------------------
# Skills per product
# ---------------------------------------------------------------------------

_docflow_skills = None
_aurora_skills = None

if SKILLS_DIR.exists():
    from agno.skills import Skills, LocalSkills

    for name, dirs in [
        ("docflow", ["docflow", "agent-ops"]),
        ("aurora", ["aurora", "agent-ops"]),
    ]:
        loaders = [LocalSkills(str(SKILLS_DIR / d)) for d in dirs if (SKILLS_DIR / d).exists()]
        if loaders:
            s = Skills(loaders=loaders)
            if name == "docflow":
                _docflow_skills = s
            elif name == "aurora":
                _aurora_skills = s

# Shared tools for all support agents
_support_tools = [
    confirm_payment,
    log_support_ticket,
    escalate_to_human,
    save_contact,
    save_company,
    log_conversation,
]

# Shared instructions
_base_instructions = [
    "ALWAYS greet warmly in Spanish. Be professional but friendly.",
    "When a customer identifies themselves, IMMEDIATELY save their contact info.",
    "For payments, ALWAYS use confirm_payment (requires human approval).",
    "For serious complaints or legal issues, use escalate_to_human.",
    "Log every interaction with log_support_ticket for analytics.",
    "At the END of every conversation, call log_conversation.",
]


# ---------------------------------------------------------------------------
# Product-specific agents
# ---------------------------------------------------------------------------

docflow_support_agent = Agent(
    name="Docflow Support",
    id="docflow-support",
    role="Customer support specialist for Docflow (Electronic Health Records)",
    model=TOOL_MODEL,
    tools=_support_tools,
    tool_call_limit=8,
    retries=2,
    pre_hooks=guardrails,
    skills=_docflow_skills,
    knowledge=knowledge_base,
    search_knowledge=True,
    instructions=[
        "You are the support specialist for Docflow (EHR system).",
        *_base_instructions,
        "",
        "## Docflow-specific knowledge",
        "- Plans: Basic $99/mes, Pro $249/mes, Enterprise custom",
        "- Features: document management, compliance, audit trail, roles",
        "- Common issues: document upload, user permissions, retention policies",
    ],
    db=db,
    learning=learning_full,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    update_memory_on_run=True,
    markdown=True,
    followups=True,
    num_followups=3,
    followup_model=FOLLOWUP_MODEL,
    compression_manager=compression,
)

aurora_support_agent = Agent(
    name="Aurora Support",
    id="aurora-support",
    role="Customer support specialist for Aurora (Voice-First PWA)",
    model=TOOL_MODEL,
    tools=_support_tools,
    tool_call_limit=8,
    retries=2,
    pre_hooks=guardrails,
    skills=_aurora_skills,
    knowledge=knowledge_base,
    search_knowledge=True,
    instructions=[
        "You are the support specialist for Aurora (voice-first business PWA).",
        *_base_instructions,
        "",
        "## Aurora-specific knowledge",
        "- Plans: Free $0, Pro $29/mes, Business $79/mes",
        "- Features: voice commands, task management, Nuxt 3, Clerk auth",
        "- Common issues: microphone permissions, PWA install, voice recognition",
    ],
    db=db,
    learning=learning_full,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    update_memory_on_run=True,
    markdown=True,
    followups=True,
    num_followups=3,
    followup_model=FOLLOWUP_MODEL,
    compression_manager=compression,
)

general_support_agent = Agent(
    name="General Support",
    id="general-support",
    role="General customer support fallback for all AikaLabs products",
    model=TOOL_MODEL,
    tools=_support_tools,
    tool_call_limit=8,
    retries=2,
    pre_hooks=guardrails,
    knowledge=knowledge_base,
    search_knowledge=True,
    instructions=[
        "You are the general support agent for AikaLabs.",
        *_base_instructions,
        "",
        "## Your role",
        "- Handle queries that don't fit a specific product",
        "- Route to product-specific agents when the product is identified",
        "- Handle general company inquiries, partnerships, careers",
    ],
    db=db,
    learning=learning_full,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    update_memory_on_run=True,
    markdown=True,
    followups=True,
    num_followups=3,
    followup_model=FOLLOWUP_MODEL,
    compression_manager=compression,
)


# ---------------------------------------------------------------------------
# WhatsApp Support Team (router)
# ---------------------------------------------------------------------------

whatsapp_support_team = Team(
    id="whatsapp-support",
    name="WhatsApp Support",
    description="Routes WhatsApp messages to the right product support agent.",
    members=[docflow_support_agent, aurora_support_agent, general_support_agent],
    mode=TeamMode.route,
    model=TOOL_MODEL,
    respond_directly=True,
    instructions=[
        "You route WhatsApp support messages to the right product agent.",
        "",
        "## Routing rules",
        "- Mentions Docflow/EHR/health records/documents → Docflow Support",
        "- Mentions Aurora/voice/PWA → Aurora Support",
        "- General/unclear → General Support",
        "",
        "## IMPORTANT",
        "- Route to ONE agent only. Do NOT loop.",
        "- If the product is unclear, ask the customer which product they need help with.",
    ],
    db=db,
    enable_session_summaries=False,
    add_history_to_context=False,
    show_members_responses=False,
    markdown=True,
)
