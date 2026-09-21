"""Offline integration tests for the tutor's GTN retrieval path.

Every test here runs the real ``TeachingAssistantAgent`` -- real pydantic-ai
tool wiring, real ``GTNSearchDB`` -- against a fixture SQLite database built in
``tmp_path``, with a scripted model standing in for the LLM. Nothing reaches the
network: an autouse guard blocks socket access for the whole module.
"""

import socket
from pathlib import Path
from textwrap import dedent
from unittest import mock

import pytest

pytest.importorskip("pydantic_ai")

from pydantic_ai import capture_run_messages
from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models.function import FunctionModel

from galaxy.agents import GalaxyAgentDependencies
from galaxy.agents.gtn import GTNSearchDB
from galaxy.agents.gtn.build_database import (
    GTNDatabaseBuilder,
    Tutorial,
)
from galaxy.agents.teaching_assistant import TeachingAssistantAgent

GTN_BASE = "https://training.galaxyproject.org/training-material"


def _tutorial_url(topic: str, tutorial: str) -> str:
    return f"{GTN_BASE}/topics/{topic}/tutorials/{tutorial}/tutorial.html"


# Three tutorials that all mention "sequencing", so one topic query matches them
# all, but only one of which mentions Falco. Relevance deliberately runs opposite
# to difficulty so an easiest-first sort can't be mistaken for the search order.
FIXTURE_MARKDOWN = {
    ("introduction", "quality-control"): dedent("""\
        ---
        title: Quality Control of Raw Reads
        level: Introductory
        description: Inspect your reads before doing anything else
        time_estimation: 1H
        questions:
        - How do I tell whether my reads are usable?
        objectives:
        - Read a Falco quality report
        - Trim adapters from raw reads
        key_points:
        - Always inspect read quality before mapping
        ---

        # Quality Control

        Run Falco over the raw sequencing reads and read the per base quality plot.
        """),
    ("transcriptomics", "ref-based"): dedent("""\
        ---
        title: Reference based Transcriptome Analysis
        level: Intermediate
        description: Turn sequencing reads into a gene count matrix
        time_estimation: 3H
        questions:
        - How do I quantify gene expression?
        objectives:
        - Map reads to a reference genome
        - Count reads per gene
        key_points:
        - A spliced mapper is required for eukaryotic data
        ---

        # Reference based analysis

        Map sequencing reads with HISAT2 and count features with featureCounts.
        """),
    ("variant-analysis", "somatic-variants"): dedent("""\
        ---
        title: Somatic Variant Sequencing at Scale
        level: Advanced
        description: Call somatic variants from deep sequencing of tumour samples
        time_estimation: 6H
        questions:
        - How do I separate somatic from germline variants?
        objectives:
        - Call variants against a matched normal
        - Annotate the surviving calls
        key_points:
        - A matched normal is what makes a call somatic
        ---

        # Somatic variants

        Call variants from paired tumour and normal sequencing with VarScan.
        """),
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail loudly if anything in these tests tries to reach the network."""
    real_socket = socket.socket
    attempts: list[str] = []

    def forbidden(*args, **kwargs):
        # Recorded as well as raised: the tutor swallows GTN failures, so a
        # regression that reaches out would otherwise look like a clean degrade.
        attempts.append(repr(args))
        raise AssertionError("Tutor GTN tests must not touch the network")

    # asyncio's event loop needs its AF_UNIX self-pipe, so only IP families are blocked.
    def guarded_socket(family=socket.AF_INET, *args, **kwargs):
        if family in (socket.AF_INET, socket.AF_INET6):
            forbidden(family, *args)
        return real_socket(family, *args, **kwargs)

    monkeypatch.setattr(socket, "socket", guarded_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    yield
    assert attempts == [], f"Tutor GTN tests attempted network access: {attempts}"


@pytest.fixture
def markdown_db(tmp_path: Path) -> Path:
    """Build a GTN database the whole way from tutorial.md files on disk."""
    gtn_path = tmp_path / "training-material"
    for (topic, tutorial), text in FIXTURE_MARKDOWN.items():
        tutorial_dir = gtn_path / "topics" / topic / "tutorials" / tutorial
        tutorial_dir.mkdir(parents=True)
        (tutorial_dir / "tutorial.md").write_text(text, encoding="utf-8")
    db_path = tmp_path / "markdown_gtn.db"
    GTNDatabaseBuilder(gtn_path=gtn_path, output_path=db_path).build()
    return db_path


def _database_from_tutorials(tmp_path: Path, name: str, tutorials: list) -> Path:
    db_path = tmp_path / name
    builder = GTNDatabaseBuilder(gtn_path=tmp_path, output_path=db_path)
    builder.tutorials = tutorials
    builder.create_database()
    builder.insert_tutorials()
    builder.add_metadata()
    return db_path


def _make_deps(db_path, model_function, download_url: str | None = None) -> GalaxyAgentDependencies:
    config = mock.Mock()
    config.ai_api_key = "test-key"
    config.ai_model = "gpt-4o-mini"
    config.ai_api_base_url = "http://localhost:4000/v1/"
    config.inference_services = {}
    config.tutor_allow_tool_execution = False
    config.gtn_database_path = str(db_path) if db_path is not None else None
    # A file:// URL keeps a regression that re-downloads the database off the network.
    config.gtn_database_url = download_url or (f"file://{db_path}" if db_path is not None else None)

    user = mock.Mock()
    user.id = 1
    user.username = "test_learner"
    user.preferences = {}

    trans = mock.Mock()
    trans.app.config = config
    trans.user = user
    trans.get_history.return_value = None

    return GalaxyAgentDependencies(
        trans=trans,
        user=user,
        config=config,
        get_agent=mock.Mock(),
        model_factory=lambda: FunctionModel(model_function),
    )


def _tool_returns(messages, tool_name: str) -> list:
    return [
        part
        for message in messages
        for part in message.parts
        if part.part_kind == "tool-return" and part.tool_name == tool_name
    ]


def _searching_model(tool_name: str, query: str):
    """Script a model that calls ``tool_name`` once, then cites its first source."""
    argument = "query" if tool_name == "search_training_materials" else "topic"

    def model(messages, info):
        returns = _tool_returns(messages, tool_name)
        if not returns:
            return ModelResponse(parts=[ToolCallPart(tool_name, {argument: query}, "search-1")])
        content = returns[0].content
        sources = content.get("sources", []) if isinstance(content, dict) else []
        if not sources:
            return ModelResponse(parts=[TextPart("No tutorial could be retrieved for that.")])
        return ModelResponse(parts=[TextPart(f"Start here.\n\n[[tutorial:{sources[0]['id']}]]")])

    return model


async def _run(deps: GalaxyAgentDependencies, query: str):
    tutor = TeachingAssistantAgent(deps)
    with capture_run_messages() as messages:
        response = await tutor.process(query)
    return tutor, response, messages


async def test_markdown_tutorial_reaches_the_model_as_a_cited_source(markdown_db: Path):
    deps = _make_deps(markdown_db, _searching_model("search_training_materials", "Falco"))

    tutor, response, messages = await _run(deps, "How do I check my read quality?")

    assert tutor.gtn_db is not None
    returns = _tool_returns(messages, "search_training_materials")
    assert len(returns) == 1
    sources = returns[0].metadata["tutor_sources"]
    assert [s["url"] for s in sources] == [_tutorial_url("introduction", "quality-control")]
    assert [s["title"] for s in sources] == ["Quality Control of Raw Reads"]
    assert "Reference based Transcriptome Analysis" not in str(sources)
    assert "Somatic Variant Sequencing at Scale" not in str(sources)
    reference = f"[Quality Control of Raw Reads](<{_tutorial_url('introduction', 'quality-control')}>)"
    assert reference in response.content


async def test_suggest_tutorials_orders_matches_easiest_first(markdown_db: Path):
    deps = _make_deps(markdown_db, _searching_model("suggest_tutorials", "sequencing"))

    _, _, messages = await _run(deps, "Where should I start with sequencing?")

    # The fixtures are written so relevance ranking is the reverse of difficulty.
    by_relevance = [r.difficulty for r in GTNSearchDB(db_path=str(markdown_db)).search("sequencing", limit=8)]
    assert by_relevance == ["advanced", "intermediate", "introductory"]
    sources = _tool_returns(messages, "suggest_tutorials")[0].metadata["tutor_sources"]
    assert [s["title"] for s in sources] == [
        "Quality Control of Raw Reads",
        "Reference based Transcriptome Analysis",
        "Somatic Variant Sequencing at Scale",
    ]
    assert [s["difficulty"] for s in sources] == ["introductory", "intermediate", "advanced"]


async def test_query_matching_no_tutorial_cites_nothing(markdown_db: Path):
    deps = _make_deps(markdown_db, _searching_model("search_training_materials", "photosynthesis"))

    _, response, messages = await _run(deps, "Teach me about photosynthesis")

    returns = _tool_returns(messages, "search_training_materials")
    assert "No matching training materials found" in returns[0].content
    assert returns[0].metadata is None
    assert "training.galaxyproject.org/training-material" not in response.content


async def test_offsite_tutorial_url_is_dropped_from_the_sources(tmp_path: Path):
    db_path = _database_from_tutorials(
        tmp_path,
        "offsite_gtn.db",
        [
            Tutorial(
                topic="proteomics",
                tutorial="mirror-copy",
                title="Mirrored Proteomics Tutorial",
                description="Proteomics peptide identification",
                url="https://mirror.example.org/topics/proteomics/tutorials/mirror-copy/tutorial.html",
                difficulty="introductory",
                content="Identify peptides from proteomics spectra.",
                content_hash="mirror1",
            ),
            Tutorial(
                topic="proteomics",
                tutorial="canonical",
                title="Canonical Proteomics Tutorial",
                description="Proteomics peptide identification",
                url=_tutorial_url("proteomics", "canonical"),
                difficulty="introductory",
                content="Identify peptides from proteomics spectra.",
                content_hash="canon1",
            ),
        ],
    )
    deps = _make_deps(db_path, _searching_model("search_training_materials", "proteomics"))

    tutor, _, messages = await _run(deps, "Find me a proteomics tutorial")

    # The tutor's filter, not the FTS search, is what removes the mirror.
    assert len(GTNSearchDB(db_path=str(db_path)).search("proteomics", limit=5)) == 2
    sources = _tool_returns(messages, "search_training_materials")[0].metadata["tutor_sources"]
    assert [s["url"] for s in sources] == [_tutorial_url("proteomics", "canonical")]
    assert tutor.gtn_db is not None


async def test_only_offsite_matches_report_no_usable_references(tmp_path: Path):
    db_path = _database_from_tutorials(
        tmp_path,
        "all_offsite_gtn.db",
        [
            Tutorial(
                topic="proteomics",
                tutorial="mirror-copy",
                title="Mirrored Proteomics Tutorial",
                description="Proteomics peptide identification",
                url="https://mirror.example.org/topics/proteomics/tutorials/mirror-copy/tutorial.html",
                difficulty="introductory",
                content="Identify peptides from proteomics spectra.",
                content_hash="mirror1",
            )
        ],
    )
    deps = _make_deps(db_path, _searching_model("search_training_materials", "proteomics"))

    _, response, messages = await _run(deps, "Find me a proteomics tutorial")

    returns = _tool_returns(messages, "search_training_materials")
    assert "Search returned no usable tutorial references" in returns[0].content
    assert returns[0].metadata is None
    assert "mirror.example.org" not in response.content


async def test_missing_database_leaves_search_unavailable_without_a_download(tmp_path: Path):
    missing_db = tmp_path / "absent" / "gtn_search.db"
    missing_source = tmp_path / "also-absent.db"
    deps = _make_deps(
        missing_db,
        _searching_model("search_training_materials", "quality control"),
        download_url=f"file://{missing_source}",
    )

    tutor, _, messages = await _run(deps, "How do I check my read quality?")

    assert tutor.gtn_db is None
    returns = _tool_returns(messages, "search_training_materials")
    assert "Training material search is not available right now" in returns[0].content
    assert returns[0].metadata is None
    assert not missing_db.exists()
