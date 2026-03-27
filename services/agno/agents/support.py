"""
QYNE v1 — Support Agent.

Handles customer support via WhatsApp and chat.
Uses Directus MCP server for reading collections + REST tools for writes.
Same pattern as original nexus.py.
"""

import os

from agno.agent import Agent
from agno.tools.mcp import MCPTools

from app.config import TOOL_MODEL, FOLLOWUP_MODEL, DIRECTUS_URL, DIRECTUS_TOKEN, db
from app.shared import guardrails, learning_full, compression
from tools.directus_business import (
    confirm_payment,
    log_support_ticket,
    escalate_to_human,
    save_contact,
    save_company,
    log_conversation,
)

# Build tool list: REST tools for writes + MCP for reads
_tools: list = [confirm_payment, log_support_ticket, escalate_to_human, save_contact, save_company, log_conversation]

# Directus MCP server: gives agent read/query access to all collections.
# Uses npx to run the official @directus/content-mcp package via stdio.
if os.getenv("DIRECTUS_TOKEN"):
    _tools.append(
        MCPTools(
            command="npx @directus/content-mcp@latest",
            env={
                "DIRECTUS_URL": os.getenv("DIRECTUS_URL", "http://directus:8055"),
                "DIRECTUS_TOKEN": os.getenv("DIRECTUS_TOKEN", ""),
            },
            include_tools=[
                "read-items",
                "create-item",
                "update-item",
                "read-collections",
                "read-fields",
                "read-flows",
                "trigger-flow",
            ],
            timeout_seconds=30,
        )
    )

support_agent = Agent(
    name="Support Agent",
    id="support-agent",
    role="Customer support specialist for Whabi, Docflow, and Aurora",
    model=TOOL_MODEL,
    tools=_tools,
    tool_call_limit=8,
    retries=2,
    pre_hooks=guardrails,
    instructions=[
        "You are the customer support specialist for AikaLabs.",
        "You handle support for three products: Whabi (WhatsApp CRM), Docflow (EHR), and Aurora (voice-first PWA).",
        "ALWAYS greet warmly in Spanish. Be professional but friendly.",
        "When a customer identifies themselves, IMMEDIATELY save their contact info.",
        "Use the Directus MCP tools to read customer data and collections.",
        "For payments, ALWAYS use confirm_payment (requires human approval).",
        "For serious complaints or legal issues, use escalate_to_human.",
        "Log every interaction with log_support_ticket for analytics.",
        "If you cannot resolve an issue, escalate to a human agent.",
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
