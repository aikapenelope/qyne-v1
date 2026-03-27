"""
QYNE v1 — SEO Content Workflow.

Pipeline: keyword research → article draft → audit/revise loop → publish-ready MDX.
"""

from agno.db.sqlite import SqliteDb
from agno.workflow import Loop, Step, StepInput, StepOutput, Workflow

from agents.seo.agents import article_writer, keyword_researcher, seo_auditor


def _check_publish_ready(step_input: StepInput) -> StepOutput:
    """Check if the SEO auditor approved the article for publishing."""
    content = step_input.previous_step_content or ""
    is_ready = "PUBLISH" in content.upper() and "REWRITE" not in content.upper()
    return StepOutput(content=content, stop=is_ready)


seo_content_workflow = Workflow(
    name="seo-content",
    description=(
        "SEO/GEO content pipeline: keyword research → article draft → "
        "audit/revise loop (max 2 rounds) → publish-ready MDX."
    ),
    db=SqliteDb(
        session_table="seo_content_session",
        db_file="/app/data/nexus.db",
    ),
    steps=[
        Step(name="Keyword Research", agent=keyword_researcher),
        Step(name="Article Draft", agent=article_writer),
        Loop(
            steps=[
                Step(name="SEO Audit", agent=seo_auditor),
                Step(name="Check Quality", executor=_check_publish_ready),
            ],
            max_iterations=2,
            forward_iteration_output=True,
        ),
    ],
)
