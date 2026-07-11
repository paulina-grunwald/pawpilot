"""RAGAS generation metrics over the agent's answers.

Scores four metrics per row against the judge LLM:

- faithfulness - is every claim supported by the retrieved passages?
- answer_accuracy - does the answer reach the reference outcome? (AnswerAccuracy)
- answer_relevancy - does the answer address the question asked? (AnswerRelevancy)
- noise_sensitivity - how much do irrelevant passages distort the answer? (lower is better)

RAGAS lives in the opt-in evals group, so it is imported lazily inside
build_generation_scorer - this module stays importable under make check
without keys or the group installed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.agent.red_flags import EMERGENCY_BANNER
from app.rag.config import RagSettings, get_rag_settings

GENERATION_METRIC_NAMES: tuple[str, ...] = (
    "faithfulness",
    "answer_accuracy",
    "answer_relevancy",
    "noise_sensitivity",
)


def strip_emergency_banner(text: str) -> str:
    """Remove the fixed emergency-banner prefix before scoring.

    The banner is canned and ungrounded, so leaving it in would unfairly depress
    faithfulness and relevancy - only the model's own answer should be judged.
    """
    if text.startswith(EMERGENCY_BANNER):
        return text[len(EMERGENCY_BANNER) :]
    return text


class GenerationSample(BaseModel):
    """The normalized RAGAS inputs for one scored row."""

    model_config = ConfigDict(frozen=True)

    user_input: str
    response: str
    retrieved_contexts: list[str]
    reference: str


class GenerationScores(BaseModel):
    """The four generation metrics for one row (noise_sensitivity: lower is better)."""

    model_config = ConfigDict(frozen=True)

    faithfulness: float
    answer_accuracy: float
    answer_relevancy: float
    noise_sensitivity: float


class GenerationScorer:
    """Scores one GenerationSample across the four generation metrics.

    Constructed with the metric objects so the routing - which input goes to which
    metric - is unit-testable with fakes; build_generation_scorer wires the live
    RAGAS metrics.
    """

    def __init__(
        self,
        *,
        faithfulness: Any,
        answer_accuracy: Any,
        answer_relevancy: Any,
        noise_sensitivity: Any,
    ) -> None:
        self._faithfulness = faithfulness
        self._answer_accuracy = answer_accuracy
        self._answer_relevancy = answer_relevancy
        self._noise_sensitivity = noise_sensitivity

    async def ascore(self, sample: GenerationSample) -> GenerationScores:
        faithfulness = await self._faithfulness.ascore(
            user_input=sample.user_input,
            response=sample.response,
            retrieved_contexts=sample.retrieved_contexts,
        )
        answer_accuracy = await self._answer_accuracy.ascore(
            user_input=sample.user_input,
            response=sample.response,
            reference=sample.reference,
        )
        answer_relevancy = await self._answer_relevancy.ascore(
            user_input=sample.user_input,
            response=sample.response,
        )
        noise_sensitivity = await self._noise_sensitivity.ascore(
            user_input=sample.user_input,
            response=sample.response,
            reference=sample.reference,
            retrieved_contexts=sample.retrieved_contexts,
        )
        return GenerationScores(
            faithfulness=faithfulness.value,
            answer_accuracy=answer_accuracy.value,
            answer_relevancy=answer_relevancy.value,
            noise_sensitivity=noise_sensitivity.value,
        )


def build_generation_scorer(settings: RagSettings | None = None) -> GenerationScorer:
    """Wire the live RAGAS metrics against the Gateway judge LLM and embeddings.

    The judge uses AGENT_EVAL_JUDGE_MODEL when set (a distinct id avoids the
    model grading its own answers), falling back to gen_model.
    """
    from ragas.metrics.collections import (
        AnswerAccuracy,
        AnswerRelevancy,
        Faithfulness,
        NoiseSensitivity,
    )

    from evals.rag.judge import build_generator_embeddings, build_sync_judge_llm

    resolved = settings if settings is not None else get_rag_settings()
    judge = build_sync_judge_llm(resolved, model=resolved.agent_eval_judge_model)
    embeddings = build_generator_embeddings(resolved)
    return GenerationScorer(
        faithfulness=Faithfulness(llm=judge),
        answer_accuracy=AnswerAccuracy(llm=judge),
        answer_relevancy=AnswerRelevancy(llm=judge, embeddings=embeddings),
        noise_sensitivity=NoiseSensitivity(llm=judge, mode="relevant"),
    )
