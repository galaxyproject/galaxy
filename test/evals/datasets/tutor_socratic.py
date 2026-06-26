"""Tutor (Socratic) dataset: does the teaching assistant guide rather than just answer?

Each case is a learner query sent to the teaching_assistant agent. What counts as a
good response depends on the situation:

- Most queries: respond Socratically -- acknowledge the goal, ask a focused leading
  question or offer a hint before the full answer, and point at real GTN training
  material instead of inventing tutorials.
- Some queries: just tell them -- an explicit "just tell me", clear frustration, or a
  simple factual lookup. Coaching there obstructs rather than helps.

Scored two ways:
- MustMention (deterministic): keyword(s) essential for the case (used sparingly,
  mostly for the direct-answer cases).
- LLMJudge (fuzzy): a per-case rubric encoding the expected pedagogical behavior.
"""

from typing import (
    Any,
    Optional,
)

from pydantic_ai.models import Model
from pydantic_evals import (
    Case,
    Dataset,
)
from pydantic_evals.evaluators import (
    LLMJudge,
    OutputConfig,
)

_PROTO_CASES: list[dict[str, Any]] = [
    {
        "name": "rnaseq_open_ended",
        "query": "How do I do RNA-seq analysis in Galaxy?",
        "mode": "socratic",
        "must_mention": [],
        "expectation": (
            "The topic is broad and the learner's goal is unclear. A good tutor asks a focused "
            "clarifying question (about their organism, data, or the specific step they're on) "
            "and/or points to a relevant GTN tutorial, rather than dumping an entire pipeline."
        ),
    },
    {
        "name": "failed_job_guided_diagnosis",
        "query": "My HISAT2 job failed. Can you help me understand why?",
        "mode": "socratic",
        "must_mention": [],
        "expectation": (
            "A good tutor guides the learner to inspect the failure themselves first -- asking "
            "what the job's error or stderr says, or which inputs were used -- before naming a "
            "cause, so the learner builds debugging skill instead of just receiving a fix."
        ),
    },
    {
        "name": "explicit_just_tell_me",
        "query": "Just tell me which tool runs FastQC. I'm in a hurry.",
        "mode": "direct",
        "must_mention": ["FastQC"],
        "expectation": (
            "The learner explicitly asked for a direct answer and signalled time pressure. A good "
            "tutor recognizes this and answers directly (naming FastQC) instead of asking a "
            "leading question."
        ),
    },
    {
        "name": "factual_lookup",
        "query": "What does a FASTQ file contain?",
        "mode": "direct",
        "must_mention": [],
        "expectation": (
            "This is a simple factual question. A good tutor answers it directly and correctly; a "
            "brief reflective follow-up is fine, but withholding the answer behind a question "
            "would be unhelpful."
        ),
    },
    {
        "name": "frustration_support",
        "query": "I've tried three times and I still can't get my reads to map. This is impossible.",
        "mode": "socratic",
        "must_mention": [],
        "expectation": (
            "The learner is frustrated. A good tutor is supportive and lowers the cognitive load -- "
            "offering a concrete next step or a worked example -- rather than adding friction with "
            "another open-ended question."
        ),
    },
    {
        "name": "no_fabricated_tutorial",
        "query": "Is there a Galaxy tutorial on single-cell ATAC-seq?",
        "mode": "socratic",
        "must_mention": [],
        "expectation": (
            "A good tutor only points to training material it actually found via search and does "
            "not invent a tutorial title or URL. If unsure, it says it will look or that it could "
            "not find one."
        ),
    },
    {
        "name": "concept_before_steps",
        "query": "Why do I need to trim adapters before alignment?",
        "mode": "socratic",
        "must_mention": [],
        "expectation": (
            "A conceptual 'why' question. A good tutor builds the learner's understanding -- asking "
            "what they think adapters are, or explaining the reasoning -- rather than only naming a "
            "trimming tool."
        ),
    },
]


_RUBRIC_TEMPLATE = """\
You are reviewing a response from a teaching-assistant agent whose job is to help
users LEARN to use Galaxy, not just to hand them answers.

For this case, the expected pedagogical behavior is:
{expectation}

Score the response between 0.0 and 1.0 on how well it matches that expectation. A
high score requires all of:
1. The response fits the expected mode for this situation -- guide with a question or
   hint when coaching is appropriate; answer directly when the learner asked for that
   or the question is simply factual.
2. It does not fabricate tool names, tutorial titles, or URLs.
3. It is supportive and moves the learner forward rather than stalling them.

Return a number; no commentary.
"""


_REGRESSION_RUBRIC = """\
You are reviewing a teaching-assistant response to a learner question that a real
user previously rated unhelpful.

Score the response between 0.0 and 1.0 on whether it is now a genuinely helpful tutor
response: it engages the learner's actual question, guides or answers appropriately,
and does not fabricate tool names, tutorial titles, or URLs.

Return a number; no commentary.
"""


def _judge(rubric: str, judge_model: Optional[Model]) -> tuple:
    if judge_model is None:
        return ()
    return (
        LLMJudge(
            rubric=rubric,
            model=judge_model,
            include_input=True,
            score=OutputConfig(evaluation_name="LLMJudge"),
            assertion=False,
        ),
    )


def tutor_socratic_dataset(
    judge_model: Optional[Model] = None,
    only: Optional[list[str]] = None,
    extra_queries: Optional[list[str]] = None,
) -> Dataset[str, str, dict[str, Any]]:
    """Build the tutor_socratic Dataset.

    If judge_model is given, attaches a per-case LLMJudge whose rubric embeds the
    expected pedagogical behavior for that case.

    extra_queries appends regression cases -- typically real learner questions whose
    tutor answer was downvoted (see TutorAnalyticsManager.get_downvoted_tutor_queries),
    judged against a generic "is this now a helpful tutor response" rubric so known-bad
    cases don't quietly regress.
    """
    cases: list[Case[str, str, dict[str, Any]]] = []
    for proto in _PROTO_CASES:
        if only and proto["name"] not in only:
            continue
        cases.append(
            Case(
                name=proto["name"],
                inputs=proto["query"],
                expected_output=None,
                metadata={
                    "must_mention": proto["must_mention"],
                    "mode": proto["mode"],
                    "expectation": proto["expectation"],
                },
                evaluators=_judge(_RUBRIC_TEMPLATE.format(expectation=proto["expectation"]), judge_model),
            )
        )
    for i, query in enumerate(extra_queries or [], start=1):
        cases.append(
            Case(
                name=f"regression_{i}",
                inputs=query,
                expected_output=None,
                metadata={"must_mention": [], "mode": "regression"},
                evaluators=_judge(_REGRESSION_RUBRIC, judge_model),
            )
        )
    return Dataset(name="tutor_socratic", cases=cases)
