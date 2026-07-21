"""Deterministic post-answer verification: a monitor, not a gate.

Spec 010 promised a verifier that upholds "never an uncited health claim." This is
its honest, deterministic form. It checks two structural defects the system prompt
is meant to prevent, without a judge model -- so there is no circular "grade the
answer with the very metric it was optimized against" problem that sank the
LLM-critic version:

- prompt_echo: a substantial verbatim line of the system prompt surfaced in the
  answer, i.e. the model leaked its own instructions. This is a prompt-injection
  exfiltration signal and pairs with the injection eval and the untrusted-content
  fences.
- grounded_claim_uncited: a retrieval tool ran and fed context into the answer, the
  answer is substantive and is not an off-topic refusal, yet it cites nothing.

It is deliberately HIGH-RECALL and NON-BLOCKING. grounded_claim_uncited can fire on
a legitimate abstention ("I couldn't find this, please ask your vet"), a false
positive we accept rather than ever hard-block a health answer on a heuristic.
Violations are logged and ride the LangSmith trace; they never alter the response.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.agent.prompt import OFF_TOPIC_MESSAGE

# Tools whose output is meant to be cited. If one ran and nothing was cited, the
# answer either stood on ungrounded ground or abstained.
_RETRIEVAL_TOOLS = frozenset({"retrieve_vet_corpus", "web_search", "lookup_pet_food"})

# A prompt line must be at least this long to count as an echo, so incidental
# short overlaps ("your dog") never trip the leak check.
_MIN_ECHO_LINE_LENGTH = 60

# Below this length an uncited answer reads as a refusal or a one-line abstention,
# not a health claim, so we do not flag it.
_SUBSTANTIVE_ANSWER_LENGTH = 200

_OFF_TOPIC_FINGERPRINT = " ".join(OFF_TOPIC_MESSAGE.split()).lower().split(":")[0]


class AnswerVerification(BaseModel):
    """The verdict for one answer: ok when no structural defect was detected."""

    model_config = ConfigDict(frozen=True)

    ok: bool
    flags: tuple[str, ...]


def _is_refusal(answer_text: str) -> bool:
    return _OFF_TOPIC_FINGERPRINT in " ".join(answer_text.split()).lower()


def _echoes_system_prompt(answer_text: str, system_prompt: str) -> bool:
    haystack = " ".join(answer_text.split())
    for line in system_prompt.splitlines():
        candidate = line.strip()
        if len(candidate) >= _MIN_ECHO_LINE_LENGTH and " ".join(candidate.split()) in haystack:
            return True
    return False


def verify_answer(
    *,
    answer_text: str,
    tool_calls: list[str],
    has_citations: bool,
    system_prompt: str,
) -> AnswerVerification:
    """Flag structural defects in an assembled answer (see module docstring)."""
    flags: list[str] = []
    if _echoes_system_prompt(answer_text, system_prompt):
        flags.append("prompt_echo")
    used_retrieval = any(tool in _RETRIEVAL_TOOLS for tool in tool_calls)
    if (
        used_retrieval
        and not has_citations
        and not _is_refusal(answer_text)
        and len(answer_text) >= _SUBSTANTIVE_ANSWER_LENGTH
    ):
        flags.append("grounded_claim_uncited")
    return AnswerVerification(ok=not flags, flags=tuple(flags))
