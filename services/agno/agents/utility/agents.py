"""
QYNE v1 — Utility Agents.

General-purpose agents: dash (data), pal (personal), onboarding, email,
scheduler, invoice, code review, automation.
"""

import os
from pathlib import Path

from agno.agent import Agent
from agno.tools.calculator import CalculatorTools
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.mcp import MCPTools
from agno.tools.python import PythonTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.websearch import WebSearchTools

from app.config import TOOL_MODEL, FOLLOWUP_MODEL, db, SKILLS_DIR, knowledge_base
from app.shared import guardrails, learning, learning_full, compression
from tools.directus_business import (
    confirm_payment,
    log_support_ticket,
    save_contact,
    save_company,
    log_conversation,
)
from tools.prefect_api import (
    list_prefect_deployments,
    trigger_prefect_flow,
    trigger_website_crawler,
    check_prefect_flow_status,
    list_recent_flow_runs,
)
from tools.chat_export import save_chat_to_directus, save_chat_to_knowledge

# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

_skills = None
_onboarding_skills = None

if SKILLS_DIR.exists():
    from agno.skills import Skills, LocalSkills

    _all_dirs = [d.name for d in SKILLS_DIR.iterdir() if d.is_dir()]
    loaders = [LocalSkills(str(SKILLS_DIR / d)) for d in _all_dirs]
    if loaders:
        _skills = Skills(loaders=loaders)

    _onb_dirs = ["docflow", "aurora", "agent-ops"]
    loaders = [LocalSkills(str(SKILLS_DIR / d)) for d in _onb_dirs if (SKILLS_DIR / d).exists()]
    if loaders:
        _onboarding_skills = Skills(loaders=loaders)


# ---------------------------------------------------------------------------
# Automation tools (MCP: n8n + Directus)
# ---------------------------------------------------------------------------

_automation_tools: list = [
    save_contact, save_company, log_conversation, log_support_ticket,
    list_prefect_deployments, trigger_prefect_flow, trigger_website_crawler,
    check_prefect_flow_status, list_recent_flow_runs,
    save_chat_to_directus, save_chat_to_knowledge,
]

if os.getenv("N8N_API_KEY"):
    _automation_tools.append(
        MCPTools(
            command="npx -y @makafeli/n8n-workflow-builder",
            env={
                "N8N_HOST": "http://n8n:5678",
                "N8N_API_KEY": os.getenv("N8N_API_KEY", ""),
            },
            include_tools=[
                "list_workflows", "get_workflow", "create_workflow",
                "update_workflow", "activate_workflow", "deactivate_workflow",
                "execute_workflow", "list_executions", "get_execution",
            ],
            timeout_seconds=30,
        )
    )

if os.getenv("DIRECTUS_TOKEN"):
    _automation_tools.append(
        MCPTools(
            command="npx @directus/content-mcp@latest",
            env={
                "DIRECTUS_URL": os.getenv("DIRECTUS_URL", "http://directus:8055"),
                "DIRECTUS_TOKEN": os.getenv("DIRECTUS_TOKEN", ""),
            },
            include_tools=[
                "read-items", "create-item", "update-item",
                "read-collections", "read-fields", "read-flows", "trigger-flow",
            ],
            timeout_seconds=30,
        )
    )


# ---------------------------------------------------------------------------
# Automation Agent
# ---------------------------------------------------------------------------

automation_agent = Agent(
    name="Automation Agent",
    id="automation-agent",
    role="Execute workflows, manage CRM, and run automations",
    model=TOOL_MODEL,
    tools=_automation_tools or None,
    tool_call_limit=5,
    pre_hooks=guardrails,
    skills=_skills,
    instructions=[
        "You are an automation specialist with access to n8n, Directus CRM, and Prefect.",
        "IMPORTANT: Always USE your tools to execute actions. NEVER just explain.",
        "",
        "## Prefect (background data flows)",
        "- list_prefect_deployments: see available flows (scraper, ETL, backup, etc.)",
        "- trigger_prefect_flow: start a flow with parameters",
        "- check_prefect_flow_status: check if a flow finished",
        "- list_recent_flow_runs: see what ran recently",
        "",
        "## When user says 'scrapea [URL]':",
        "1. Call list_prefect_deployments to find the scraper deployment ID",
        "2. Call trigger_prefect_flow with the deployment ID and URLs as parameters",
        "3. Report that the flow was triggered",
        "",
        "## When user says 'procesa documentos' or 'indexa':",
        "1. Find the etl-documents or knowledge-indexer deployment",
        "2. Trigger it with the appropriate parameters",
        "",
        "## n8n (workflow automation)",
        "- List, create, execute n8n workflows via MCP tools.",
        "",
        "## Directus CRM (direct REST API)",
        "- save_contact, save_company, log_conversation, log_support_ticket",
        "",
        "## Rules",
        "- ALWAYS call tools first, then report results.",
        "- Confirm before executing destructive or irreversible actions.",
    ],
    db=db,
    learning=learning,
    add_history_to_context=True,
    num_history_runs=2,
    add_datetime_to_context=True,
    markdown=True,
    followups=True,
    num_followups=3,
    followup_model=FOLLOWUP_MODEL,
    compression_manager=compression,
)


# ---------------------------------------------------------------------------
# Dash — Data Analytics Agent
# ---------------------------------------------------------------------------

dash = Agent(
    name="Dash",
    id="dash",
    role="Data analytics agent for Docflow, Aurora, and Nova business metrics",
    model=TOOL_MODEL,
    tools=[CalculatorTools(), PythonTools()] + _automation_tools,
    tool_call_limit=5,
    retries=1,
    pre_hooks=guardrails,
    skills=_skills,
    instructions=[
        "You are Dash, a self-learning data analytics agent.",
        "",
        "## Your Purpose",
        "Answer business questions about Docflow, Aurora, and Nova using",
        "data from Directus CRM. Interpret data, find patterns, explain meaning.",
        "",
        "## Data Sources",
        "- Directus CRM: contacts, companies, tasks, tickets (via MCP tools)",
        "- Calculator: compute metrics, percentages, growth rates",
        "- Python: complex calculations, data transformations",
        "",
        "## Product Context",
        "- Docflow: EHR system. Key metrics: documents processed, compliance rate",
        "- Aurora: Voice PWA. Key metrics: active users, voice commands/day, retention",
        "",
        "## Output Format",
        "- The number (specific, not 'many')",
        "- The trend (up/down/stable vs last period)",
        "- What it means (so what?)",
        "- Recommended action (if applicable)",
    ],
    db=db,
    learning=learning_full,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    markdown=True,
    compression_manager=compression,
)


# ---------------------------------------------------------------------------
# Pal — Personal Agent
# ---------------------------------------------------------------------------

_pal_storage = Path("/app/data/pal-data")
_pal_storage.mkdir(exist_ok=True)

pal = Agent(
    name="Pal",
    id="pal",
    role="Personal agent that remembers everything and organizes your world",
    model=TOOL_MODEL,
    tools=[
        FileTools(base_dir=_pal_storage),
        PythonTools(),
        WebSearchTools(fixed_max_results=5),
    ],
    tool_call_limit=5,
    retries=1,
    pre_hooks=guardrails,
    skills=_skills,
    instructions=[
        "You are Pal, a personal agent that learns everything about its user.",
        "",
        "## Storage System",
        "JSON files in pal-data/: notes.json, bookmarks.json, people.json,",
        "projects.json, decisions.json",
        "",
        "## Workflow",
        "1. Recall: search learnings FIRST",
        "2. Understand: storing, retrieving, or connecting information?",
        "3. Act: read file → append → save (for storing), search files (for retrieving)",
        "4. Learn: save new knowledge about user preferences",
        "",
        "## Rules",
        "- Always read the file before writing (to append, not overwrite)",
        "- Use tags consistently to connect information across files",
        "- If a file doesn't exist yet, create it with an empty array []",
    ],
    db=db,
    learning=learning_full,
    add_history_to_context=True,
    num_history_runs=10,
    add_datetime_to_context=True,
    markdown=True,
    enable_agentic_memory=True,
)


# ---------------------------------------------------------------------------
# Onboarding Agent
# ---------------------------------------------------------------------------

onboarding_agent = Agent(
    name="Onboarding Agent",
    id="onboarding-agent",
    role="Guide new clients through product setup and first steps",
    model=TOOL_MODEL,
    tools=[WebSearchTools(fixed_max_results=3)],
    tool_call_limit=3,
    retries=1,
    pre_hooks=guardrails,
    skills=_onboarding_skills,
    knowledge=knowledge_base,
    search_knowledge=True,
    instructions=[
        "You are the onboarding specialist for AikaLabs products.",
        "You guide new clients through setup step by step in Spanish.",
        "",
        "## Products: Docflow (EHR), Aurora (Voice PWA), Nova",
        "",
        "## Rules",
        "- Always ask which product the client is onboarding for",
        "- Go ONE step at a time. Don't dump all steps at once.",
        "- After each step, ask 'Did that work? Ready for the next step?'",
        "- Be patient. Assume zero technical knowledge.",
    ],
    db=db,
    learning=learning,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Email Agent
# ---------------------------------------------------------------------------

_email_tools: list = []
if os.getenv("EMAIL_SENDER") and os.getenv("EMAIL_PASSKEY"):
    from agno.tools.email import EmailTools
    _email_tools.append(EmailTools())

email_agent = Agent(
    name="Email Agent",
    id="email-agent",
    role="Draft and send professional emails for follow-ups and outreach",
    model=TOOL_MODEL,
    tools=_email_tools or [WebSearchTools(fixed_max_results=3)],
    tool_call_limit=3,
    retries=1,
    pre_hooks=guardrails,
    instructions=[
        "You are an email specialist. You draft and send professional emails.",
        "You write in Spanish (Latin America neutral) unless told otherwise.",
        "",
        "## Rules",
        "- ALWAYS show the draft to the user before sending",
        "- Never send without explicit user confirmation",
        "- If EmailTools is not configured, draft the email as text",
    ],
    db=db,
    learning=learning,
    add_history_to_context=True,
    num_history_runs=2,
    add_datetime_to_context=True,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Scheduler Agent
# ---------------------------------------------------------------------------

scheduler_agent = Agent(
    name="Scheduler Agent",
    id="scheduler-agent",
    role="Create reminders, schedule tasks, and manage calendar entries",
    model=TOOL_MODEL,
    tools=_automation_tools + [CalculatorTools()],
    tool_call_limit=4,
    retries=1,
    pre_hooks=guardrails,
    instructions=[
        "You are a scheduling specialist. You create tasks, reminders, and events.",
        "You respond in Spanish (Latin America neutral).",
        "",
        "## What you handle",
        "- 'Recuerdame llamar a Juan el viernes' → create task in Directus CRM",
        "- 'Que tengo pendiente esta semana?' → list tasks from CRM",
        "- 'Marca como completada la tarea de...' → update task status",
        "",
        "## Rules",
        "- Always confirm the date and time before creating",
        "- Use America/Bogota timezone unless told otherwise",
        "- If no time specified, default to 9:00 AM",
    ],
    db=db,
    learning=learning,
    add_history_to_context=True,
    num_history_runs=2,
    add_datetime_to_context=True,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Invoice Agent
# ---------------------------------------------------------------------------

invoice_agent = Agent(
    name="Invoice Agent",
    id="invoice-agent",
    role="Generate quotes, invoices, and track payments for clients",
    model=TOOL_MODEL,
    tools=[confirm_payment, log_support_ticket] + _automation_tools + [CalculatorTools(), PythonTools()],
    tool_call_limit=5,
    retries=1,
    pre_hooks=guardrails,
    instructions=[
        "You are a billing specialist. You generate quotes, invoices, and track payments.",
        "You respond in Spanish (Latin America neutral).",
        "",
        "## Pricing Reference",
        "- Docflow Basic: $99/mes | Pro: $249/mes | Enterprise: custom",
        "- Aurora Free: $0 | Pro: $29/mes | Business: $79/mes",
        "",
        "## Rules",
        "- ALWAYS use confirm_payment for payment confirmations",
        "- Never confirm a payment without @approval",
        "- Log every billing interaction via log_support_ticket",
        "- Prices are in USD unless client specifies local currency",
    ],
    db=db,
    learning=learning,
    add_history_to_context=True,
    num_history_runs=3,
    add_datetime_to_context=True,
    markdown=True,
    compression_manager=compression,
)


# ---------------------------------------------------------------------------
# Code Review Agent
# ---------------------------------------------------------------------------

_code_workspace = Path("/app/data/workspace")
_code_workspace.mkdir(exist_ok=True)

code_review_agent = Agent(
    name="Code Review Agent",
    id="code-review-agent",
    role="Review, write, and iterate on code with self-learning",
    model=TOOL_MODEL,
    tools=[
        CodingTools(base_dir=str(_code_workspace)),
        ReasoningTools(),
    ],
    tool_call_limit=5,
    pre_hooks=guardrails,
    reasoning=True,
    reasoning_min_steps=2,
    reasoning_max_steps=5,
    instructions=[
        "You are a code review specialist that gets sharper with every review.",
        "You operate in a sandboxed workspace directory.",
        "",
        "## Review Process",
        "1. Read the code carefully using read_file",
        "2. Think through potential issues using reasoning tools",
        "3. Produce a structured review:",
        "   - SEVERITY: critical / warning / info",
        "   - ISSUE: what's wrong and where (file:line)",
        "   - FIX: specific code change to resolve it",
        "   - WHY: explanation of the impact",
        "",
        "## Rules",
        "- Always check for: SQL injection, XSS, hardcoded secrets, race conditions",
        "- Flag missing error handling and edge cases",
        "- Use relative paths within the workspace only",
    ],
    db=db,
    learning=learning,
    add_history_to_context=True,
    num_history_runs=3,
    add_datetime_to_context=True,
    markdown=True,
    compression_manager=compression,
)
