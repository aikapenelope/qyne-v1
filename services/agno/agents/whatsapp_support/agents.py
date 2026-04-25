"""
QYNE v1 — WhatsApp Support Team.

Product-specific support agents + general fallback, routed by product.
Optimized for WhatsApp: concise responses, interactive messages, session memory.
"""

from agno.agent import Agent
from agno.team import Team, TeamMode
from agno.tools.whatsapp import WhatsAppTools

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
from tools.directus_pipeline import (
    create_deal,
    update_deal_stage,
    get_contact_deals,
    get_pipeline_summary,
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

# ---------------------------------------------------------------------------
# WhatsApp interactive tools (buttons, lists, media)
# ---------------------------------------------------------------------------

_whatsapp_tools = WhatsAppTools(
    enable_send_reply_buttons=True,
    enable_send_list_message=True,
)

# Shared CRM tools for all support agents
_support_tools = [
    confirm_payment,
    log_support_ticket,
    escalate_to_human,
    save_contact,
    save_company,
    log_conversation,
    _whatsapp_tools,
    create_deal,
    update_deal_stage,
    get_contact_deals,
    get_pipeline_summary,
]

# ---------------------------------------------------------------------------
# Shared instructions (WhatsApp-optimized)
# ---------------------------------------------------------------------------

_base_instructions = [
    "ALWAYS greet warmly in Spanish. Be professional but friendly.",
    "When a customer identifies themselves, IMMEDIATELY save their contact info.",
    "For payments, ALWAYS use confirm_payment (requires human approval).",
    "For serious complaints or legal issues, use escalate_to_human.",
    "Log every interaction with log_support_ticket for analytics.",
    "At the END of every conversation, call log_conversation.",
    "",
    "## WhatsApp format rules",
    "- Keep responses under 500 words. WhatsApp users expect concise answers.",
    "- Structure responses as short paragraphs separated by double newlines.",
    "- Use *bold* for emphasis (WhatsApp supports it).",
    "- Never use markdown tables, code blocks, or headers -- WhatsApp doesn't render them.",
    "- Use numbered lists (1. 2. 3.) for steps, bullet points for options.",
    "- Use reply buttons when offering 2-3 choices (e.g., product selection, yes/no).",
    "- Use list messages when offering 4+ options (e.g., plan comparison, FAQ topics).",
    "",
    "## Sales pipeline rules",
    "- When a customer asks about pricing or plans, use create_deal to open a deal.",
    "- When a deal progresses (demo requested, proposal sent, etc.), use update_deal_stage.",
    "- Before creating a deal, use get_contact_deals to check if one already exists.",
    "- If a customer says they are NOT interested, use update_deal_stage with stage=lost.",
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
        "- When the product is unclear, use reply buttons to ask:",
        "  'Sobre cual producto necesitas ayuda?' with buttons: Docflow / Aurora / Otro",
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
    determine_input_for_members=False,
    instructions=[
        "You route WhatsApp support messages to the right product agent.",
        "",
        "## Routing rules",
        "- Mentions Docflow/EHR/health records/documents/clinica → Docflow Support",
        "- Mentions Aurora/voice/PWA/voz/app → Aurora Support",
        "- General/unclear/greeting → General Support",
        "",
        "## IMPORTANT",
        "- Route to ONE agent only. Do NOT loop.",
        "- If the product is unclear, route to General Support (it will ask the customer).",
    ],
    db=db,
    enable_session_summaries=False,
    add_history_to_context=False,
    show_members_responses=False,
    markdown=True,
)
