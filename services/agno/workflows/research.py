"""
QYNE v1 — Research Workflows.

client_research_workflow: Parallel web + knowledge → synthesis report.
deep_research_workflow: Planner → N parallel scouts → quality gate → markdown report.
"""

from agno.db.sqlite import SqliteDb
from agno.workflow import Parallel, Step, StepInput, StepOutput, Workflow

from agents.knowledge import knowledge_agent
from agents.deep_research.agents import (
    available_scout_names,
    research_planner,
    research_scouts,
    research_synthesizer,
    synthesis_agent,
)
from agents.research import research_agent


# ---------------------------------------------------------------------------
# Client Research Workflow
# ---------------------------------------------------------------------------

client_research_workflow = Workflow(
    name="client-research",
    description=(
        "Research a client or topic: parallel web + knowledge search, "
        "conditional deep dive if needed, structured synthesis report."
    ),
    db=SqliteDb(
        session_table="workflow_session",
        db_file="/app/data/nexus.db",
    ),
    steps=[
        Parallel(
            Step(name="Web Research", agent=research_agent, skip_on_failure=True, max_retries=2),
            Step(name="Knowledge Lookup", agent=knowledge_agent, skip_on_failure=True, max_retries=1),
            name="Parallel Research",
        ),
        Step(name="Synthesis", agent=synthesis_agent),
    ],
)


# ---------------------------------------------------------------------------
# Quality Gate
# ---------------------------------------------------------------------------


def _quality_gate(step_input: StepInput) -> StepOutput:
    """Check that the analysis has enough substance to proceed."""
    content = str(step_input.previous_step_content or "")
    if len(content) < 200:
        return StepOutput(
            content="Quality gate failed: research too thin.",
            stop=True,
            success=False,
        )
    return StepOutput(content=content, success=True)


# ---------------------------------------------------------------------------
# Deep Research Workflow
# ---------------------------------------------------------------------------

deep_research_workflow = Workflow(
    name="deep-research",
    description=(
        f"Production deep research: planner → {len(research_scouts)} scouts "
        f"({', '.join(available_scout_names)}) in parallel → quality gate → markdown report."
    ),
    db=SqliteDb(
        session_table="deep_research_session",
        db_file="/app/data/nexus.db",
    ),
    steps=[
        Step(name="Plan", agent=research_planner),
        Parallel(
            *[Step(name=name, agent=agent, skip_on_failure=True) for name, agent in research_scouts],
            name="Parallel Research",
        ),
        Step(name="Quality Gate", executor=_quality_gate),
        Step(name="Final Report", agent=research_synthesizer),
    ],
)
