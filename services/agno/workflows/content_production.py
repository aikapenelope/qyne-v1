"""
QYNE v1 — Content Production Workflow.

Full pipeline: research → compact → 3 script variants → creative review.
"""

from agno.db.sqlite import SqliteDb
from agno.workflow import Step, StepInput, StepOutput, Workflow

from agents.content.agents import creative_director, scriptwriter, trend_scout


def _compact_research(step_input: StepInput) -> StepOutput:
    """Compaction function: extract only the brief from Trend Scout output."""
    content = step_input.previous_step_content or step_input.input or ""
    return StepOutput(content=content)


content_production_workflow = Workflow(
    name="content-production",
    description=(
        "Full content pipeline: research → compact → 3 script variants "
        "→ creative review → human selects best → save."
    ),
    db=SqliteDb(
        session_table="content_workflow_session",
        db_file="/app/data/nexus.db",
    ),
    steps=[
        Step(name="Trend Research", agent=trend_scout, skip_on_failure=False),
        Step(name="Compact Brief", executor=_compact_research),
        Step(name="Script Variants", agent=scriptwriter),
        Step(name="Creative Review", agent=creative_director),
    ],
)
