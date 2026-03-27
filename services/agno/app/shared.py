"""
QYNE v1 — Shared components (guardrails, learning, compression).

Same as original nexus.py, extracted for modularity.
"""

from agno.compression.manager import CompressionManager
from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail
from agno.learn.machine import LearningMachine
from agno.learn import (
    DecisionLogConfig,
    LearnedKnowledgeConfig,
    LearningMode,
    UserProfileConfig,
    UserMemoryConfig,
    EntityMemoryConfig,
)

from app.config import TOOL_MODEL, FAST_MODEL, learnings_knowledge

# ---------------------------------------------------------------------------
# Guardrails (same as original nexus.py)
# ---------------------------------------------------------------------------

guardrails = [
    PIIDetectionGuardrail(
        mask_pii=True,
        enable_phone_check=False,
    ),
    PromptInjectionGuardrail(),
]

# ---------------------------------------------------------------------------
# Learning Machines (same as original nexus.py)
# ---------------------------------------------------------------------------

# Minimal learning: only learned_knowledge (patterns, solutions).
learning_minimal = LearningMachine(
    model=TOOL_MODEL,
    knowledge=learnings_knowledge,
    learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
)

# Full learning: profile + memory + entities + knowledge + decision log.
learning_full = LearningMachine(
    model=TOOL_MODEL,
    knowledge=learnings_knowledge,
    user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),
    user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
    entity_memory=EntityMemoryConfig(mode=LearningMode.AGENTIC),
    learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
    decision_log=DecisionLogConfig(mode=LearningMode.AGENTIC),
)

# ---------------------------------------------------------------------------
# Context Compression (same as original nexus.py)
# ---------------------------------------------------------------------------

compression = CompressionManager(
    model=FAST_MODEL,
    compress_tool_results=True,
)

# Convenience aliases
learning = learning_minimal
