"""Router tool-use dataset: did the router call its fast-path tools when it should?

The router has a small set of read-only ``@agent.tool`` callables for
inventory/availability queries (search_tools, search_workflows,
list_histories, list_workflows, get_user_info, get_server_info,
get_history_summary). When asked "is FastQC installed?" or "what histories
do I have?", the router should *call those tools* rather than write a
generic essay about how the user can find tools themselves.

This dataset captures the latter failure mode -- it's the regression
target for https://github.com/galaxyproject/galaxy/pull/21661#issuecomment-4367167981
where gpt-oss-120b answered Neoform's "Can you see which tools are
installed on this server?" with a 2000-token essay listing UI navigation
methods, despite having ``search_tools`` available as a tool.

Scored with ``ToolCallMatch`` -- pass if the model invoked at least one
of the expected fast-path tools. We don't constrain args (a sensible query
string is good enough) and don't grade the final answer here; the goal is
"did the model use the capability it was given." Recommendation quality
lives in the tool_recommendation dataset; routing/handoff quality lives in
the routing dataset.
"""

from typing import (
    Any,
    Optional,
)

from pydantic_evals import (
    Case,
    Dataset,
)

_PROTO_CASES: list[dict[str, Any]] = [
    {
        "name": "neoform_what_tools_installed",
        "query": "Can you see which tools are installed on this server?",
        "expected_tool_calls": ["search_tools", "get_server_info"],
        "description": (
            "Direct regression for PR #21661 comment 4367167981. The model "
            "should call search_tools (or get_server_info as a fallback "
            "for capability discovery) instead of writing a how-to essay."
        ),
    },
    {
        "name": "is_fastqc_installed",
        "query": "Is FastQC installed on this Galaxy?",
        "expected_tool_calls": ["search_tools"],
        "description": "Specific tool availability lookup -- canonical search_tools use case.",
    },
    {
        "name": "do_we_have_bwa",
        "query": "Do we have BWA available?",
        "expected_tool_calls": ["search_tools"],
        "description": "Same shape as FastQC; checks the model recognizes 'do we have X' as inventory.",
    },
    {
        "name": "show_trim_adapter_tools",
        "query": "Show me tools matching 'trim adapters'.",
        "expected_tool_calls": ["search_tools"],
        "description": "Explicit search request -- should map directly to search_tools.",
    },
    {
        "name": "rnaseq_workflow_available",
        "query": "Do I have any RNA-seq workflows?",
        "expected_tool_calls": ["search_workflows", "list_workflows"],
        "description": "Workflow inventory; either search or list is acceptable.",
    },
    {
        "name": "list_my_workflows",
        "query": "What workflows do I have stored?",
        "expected_tool_calls": ["list_workflows", "search_workflows"],
        "description": "Bare list request -- list_workflows is the natural fit.",
    },
    {
        "name": "what_histories_do_i_have",
        "query": "What histories do I have?",
        "expected_tool_calls": ["list_histories"],
        "description": "Canonical list_histories trigger.",
    },
    {
        "name": "galaxy_version",
        "query": "What version of Galaxy am I on?",
        "expected_tool_calls": ["get_server_info"],
        "description": "Server metadata lookup -- should call get_server_info, not guess.",
    },
    {
        "name": "who_am_i",
        "query": "Who am I logged in as?",
        "expected_tool_calls": ["get_user_info"],
        "description": "User identity lookup.",
    },
    {
        "name": "am_i_admin",
        "query": "Am I an admin user on this Galaxy?",
        "expected_tool_calls": ["get_user_info"],
        "description": "Admin-flag check; the get_user_info docstring promises this field.",
    },
]


def router_tool_use_dataset(
    only: Optional[list[str]] = None,
) -> Dataset[str, Any, dict[str, Any]]:
    """Build the router_tool_use Dataset.

    Each Case carries ``expected_tool_calls`` (a list of acceptable tool
    names) in its metadata for ToolCallMatch to score against the captured
    tool-call list.
    """
    cases: list[Case[str, Any, dict[str, Any]]] = []
    for proto in _PROTO_CASES:
        if only and proto["name"] not in only:
            continue
        cases.append(
            Case(
                name=proto["name"],
                inputs=proto["query"],
                expected_output=None,
                metadata={
                    "expected_tool_calls": proto["expected_tool_calls"],
                    "description": proto["description"],
                },
            )
        )
    return Dataset(name="router_tool_use", cases=cases)
