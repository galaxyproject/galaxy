"""Routing dataset: (query, expected handoff target) for the QueryRouterAgent.

Seeded from ~/.claude/plans/galaxy-agents/test_agents_live.py and the
TEST_QUERIES in test/unit/app/test_agents.py. Cases marked
requires_galaxy=True need a running Galaxy session and are skipped by default.
"""

from typing import (
    Any,
)

from pydantic_evals import (
    Case,
    Dataset,
)


def _case(
    name: str,
    query: str,
    expected: str,
    description: str,
    requires_galaxy: bool = False,
) -> Case[str, str, dict[str, Any]]:
    return Case(
        name=name,
        inputs=query,
        expected_output=expected,
        metadata={"description": description, "requires_galaxy": requires_galaxy},
    )


ROUTING_CASES: list[Case[str, str, dict[str, Any]]] = [
    # Direct router responses
    _case("greeting", "Hi, what can you help me with?", "router", "General greeting"),
    _case(
        "upload_basics",
        "How do I upload a file to Galaxy?",
        "router",
        "Basic Galaxy usage",
    ),
    _case(
        "tool_discovery_rnaseq",
        "What tools are available for RNA-seq analysis?",
        "tool_recommendation",
        "Tool discovery -- hand off to tool_recommendation",
    ),
    _case("citation", "How do I cite Galaxy in my paper?", "router", "Citation request"),
    _case(
        "off_topic_weather",
        "What's the weather like today?",
        "router",
        "Off-topic -- router declines",
    ),
    # Error analysis handoff
    _case(
        "oom_137",
        "My job failed with exit code 137 and stderr shows 'Killed'. What happened?",
        "error_analysis",
        "OOM kill -- exit 137",
    ),
    _case(
        "command_not_found",
        "I got 'command not found: samtools' in my job stderr. How do I fix this?",
        "error_analysis",
        "Missing tool error",
    ),
    _case(
        "bwa_oom",
        "Why did my BWA job fail? The log shows 'out of memory'",
        "error_analysis",
        "Memory error",
    ),
    # Custom tool handoff
    _case(
        "tool_create_fasta_lines",
        "Create a Galaxy tool that counts lines in a FASTA file",
        "custom_tool",
        "Tool creation request",
    ),
    _case(
        "tool_wrap_seqtk",
        "Build a wrapper for the seqtk command line tool",
        "custom_tool",
        "Tool wrapper request",
    ),
    # History analyzer handoff (requires Galaxy)
    _case(
        "history_summary",
        "Summarize my current history",
        "history_analyzer",
        "History summary",
        requires_galaxy=True,
    ),
    _case(
        "history_question",
        "What analysis did I perform in my RNA-seq history?",
        "history_analyzer",
        "History question",
        requires_galaxy=True,
    ),
    _case(
        "methods_section",
        "Generate a methods section for my analysis",
        "history_analyzer",
        "Methods generation",
        requires_galaxy=True,
    ),
    _case(
        "tool_versions_used",
        "What tools and versions did I use?",
        "history_analyzer",
        "Tool usage question",
        requires_galaxy=True,
    ),
    # Edge cases: ambiguous, multi-intent, implicit, off-topic. The point of
    # these is to expose router-prompt weaknesses, so some of the expected
    # answers are debatable on purpose.
    _case(
        "edge_greeting_then_align",
        "Hi! How do I align reads to a reference?",
        "tool_recommendation",
        "Greeting wrapper around a tool-discovery question",
    ),
    _case(
        "edge_implicit_failure",
        "My analysis broke last night, no idea what happened.",
        "error_analysis",
        "No 'error' / 'exit code' keywords but it is a failure question",
    ),
    _case(
        "edge_align_intent",
        "I need to align reads to a reference. What should I use?",
        "tool_recommendation",
        "Tool selection by analysis intent",
    ),
    _case(
        "edge_qc_intent",
        "What's a good tool for FASTQ quality check?",
        "tool_recommendation",
        "Tool selection by quality-check intent",
    ),
    _case(
        "edge_wrap_explicit",
        "Wrap fastp for me as a Galaxy tool.",
        "custom_tool",
        "Explicit wrap request -- custom_tool, not tool_recommendation",
    ),
    _case(
        "edge_implicit_bwa_failure",
        "My BWA run didn't finish.",
        "error_analysis",
        "Implicit failure -- no 'failed' / 'error' keyword",
    ),
    _case(
        "edge_workflow_meta",
        "Should I use a workflow or just run tools one at a time?",
        "router",
        "Meta question about Galaxy usage -- router answers directly",
    ),
    _case(
        "edge_off_topic_python",
        "What's the syntax for Python decorators?",
        "router",
        "Off-topic dev question -- router should decline",
    ),
    _case(
        "edge_multi_intent",
        "Make a samtools sort tool and explain how to use it.",
        "custom_tool",
        "Multi-intent: tool creation is the primary action",
    ),
    _case(
        "edge_very_short",
        "help",
        "router",
        "One-word query -- router asks for clarification",
    ),
    # Staining quantification use-case prompts -- a representative
    # histological staining quantification flow ending with Omero export.
    # See evals/datasets/staining_quantification.py for content-quality
    # rubrics on the same set; these cases only score the routing decision.
    _case(
        "stain_quantification_intro",
        (
            "The datasets in my history are brightfield RGB images from a "
            "histological staining experiment. I'd like to quantify stain "
            "components from those images. What's a good way to do this?"
        ),
        "tool_recommendation",
        "Opening prompt; tool_recommendation also surfaces IWC workflows once agent-ops-iwc-reintroduce lands.",
    ),
    _case(
        "import_iwc_workflow",
        "Import a histological staining workflow from IWC.",
        "tool_recommendation",
        "tool_recommendation owns IWC search (search_iwc_workflows) and emits a WORKFLOW_IMPORT action for the surfaced workflow; no in-app agent calls import_workflow_from_iwc directly.",
    ),
    _case(
        "omero_upload_guidance",
        "How can I upload this data to Omero?",
        "router",
        "Router-direct guidance on Omero file source / connection setup.",
    ),
    _case(
        "history_sanity_check",
        "Look at my history -- did I miss anything in this analysis?",
        "history",
        "Post-run sanity check on the user's history.",
        requires_galaxy=True,
    ),
    _case(
        "summarize_to_page",
        "Summarize this analysis and save it as a Galaxy Page.",
        "history",
        "History agent owns Page creation.",
        requires_galaxy=True,
    ),
    _case(
        "custom_tool_quantify_brown",
        "Generate a Galaxy tool that counts brown pixels in a TIFF image.",
        "custom_tool",
        "Explicit custom_tool request -- writing a tool wrapper, not running an existing one.",
    ),
    _case(
        "recommend_iwc_workflow",
        "Recommend an IWC workflow for histological staining quantification.",
        "tool_recommendation",
        "Recommendation-style IWC ask -- discovery phrasing routes to tool_recommendation, which searches IWC and surfaces an importable workflow.",
    ),
]


def routing_dataset(
    include_galaxy_required: bool = False,
    only: list[str] | None = None,
) -> Dataset[str, str, dict[str, Any]]:
    """Build the routing Dataset.

    Args:
        include_galaxy_required: include cases that need a running Galaxy session.
        only: if given, restrict to cases whose name is in this list.
    """
    cases = ROUTING_CASES
    if not include_galaxy_required:
        cases = [c for c in cases if not (c.metadata or {}).get("requires_galaxy")]
    if only:
        wanted = set(only)
        cases = [c for c in cases if c.name in wanted]
    return Dataset(name="routing", cases=cases)
