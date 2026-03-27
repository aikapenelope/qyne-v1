"""
QYNE v1 — Media Generation Workflow.

Describe media → generate image/video → review.
"""

from agno.db.sqlite import SqliteDb
from agno.workflow import Step, Workflow

from agents.creative.agents import image_generator, media_describer

media_generation_workflow = Workflow(
    name="media-generation",
    description="Media pipeline: describe → generate → review.",
    db=SqliteDb(session_table="media_gen_session", db_file="/app/data/nexus.db"),
    steps=[
        Step(name="Describe", agent=media_describer),
        Step(name="Generate", agent=image_generator),
    ],
)
