"""Parser tests for the repository data-table bundle model.

These build :class:`RepositoryDataTables` from real fixture repositories (no mocks)
under ``repositories/`` and assert the assembled cross-file model.
"""

import os

from galaxy.tool_util.data.bundles.repository import (
    build_repository_data_tables,
    ConsumerRef,
    RepositoryDataTables,
)
from galaxy.tool_util.parser.factory import get_tool_source

REPOS = os.path.join(os.path.dirname(__file__), "repositories")
FETCH_REPO = os.path.join(REPOS, "fetch_genome_dbkeys_all_fasta")
BROKEN_REPO = os.path.join(REPOS, "broken_rows")

FETCH_DM_CONF = os.path.join(FETCH_REPO, "data_manager_conf.xml")
FETCH_DM_CONF_NESTED = os.path.join(FETCH_REPO, "data_manager_conf_nested_tool.xml")
FETCH_TABLE_TEST_CONF = os.path.join(FETCH_REPO, "tool_data_table_conf.xml.test")
FETCH_CONSUMER = os.path.join(FETCH_REPO, "tools", "consume_all_fasta.xml")

SAMPLE_FALLBACK_REPO = os.path.join(REPOS, "sample_fallback")
MISSING_LOC_REPO = os.path.join(REPOS, "missing_loc")


def _consumer_sources(*paths):
    return [(path, get_tool_source(config_file=path)) for path in paths]


def test_manager_side_reuses_processor_description():
    model = build_repository_data_tables(FETCH_REPO, data_manager_conf=FETCH_DM_CONF)
    assert len(model.managers) == 1
    manager = model.managers[0]
    assert manager.id == "fetch_genome_all_fasta_dbkeys"
    # Output names come from the (macro-expanded) wrapper's <outputs>.
    assert "out_file" in manager.tool_output_names
    # Reused manager-side model exposes declared tables + output_ref mapping.
    assert manager.processor.data_table_names == ["all_fasta", "__dbkeys__"]
    output_refs = manager.processor.output_ref_by_data_table
    assert output_refs["all_fasta"]["path"] == "out_file"
    assert output_refs["__dbkeys__"]["len_path"] == "out_file"
    assert manager.source.path == FETCH_DM_CONF
    assert manager.source.line is not None


def test_configured_tables_from_test_conf():
    model = build_repository_data_tables(FETCH_REPO, tool_data_table_confs=[FETCH_TABLE_TEST_CONF])
    assert model.configured_table_names == frozenset({"all_fasta", "__dbkeys__"})

    all_fasta = model.table("all_fasta")
    assert all_fasta is not None
    assert all_fasta.columns == {"value": 0, "dbkey": 1, "name": 2, "path": 3}
    assert all_fasta.largest_index == 3
    assert all_fasta.separator == "\t"
    assert all_fasta.comment_char == "#"


def test_loc_assets_resolved_and_clean():
    model = build_repository_data_tables(FETCH_REPO, tool_data_table_confs=[FETCH_TABLE_TEST_CONF])
    by_table = {loc.table_name: loc for loc in model.loc_assets}
    # dbkeys.loc has one valid 3-field row; all_fasta.loc is empty. Both resolve, neither errors.
    assert by_table["__dbkeys__"].found is True
    assert by_table["__dbkeys__"].is_sample is False
    assert by_table["__dbkeys__"].errors == ()
    assert by_table["all_fasta"].found is True
    assert by_table["all_fasta"].errors == ()


def test_consumer_references_scanned():
    model = build_repository_data_tables(FETCH_REPO, consumer_tool_sources=_consumer_sources(FETCH_CONSUMER))
    assert len(model.consumers) == 1
    consumer = model.consumers[0]
    assert isinstance(consumer, ConsumerRef)
    assert consumer.table_name == "all_fasta"
    assert consumer.kind == "from_data_table"
    assert consumer.tool_id == "consume_all_fasta"
    assert consumer.source.path == FETCH_CONSUMER


def test_full_bundle_is_internally_consistent():
    model = build_repository_data_tables(
        FETCH_REPO,
        data_manager_conf=FETCH_DM_CONF,
        tool_data_table_confs=[FETCH_TABLE_TEST_CONF],
        consumer_tool_sources=_consumer_sources(FETCH_CONSUMER),
    )
    assert isinstance(model, RepositoryDataTables)
    configured = model.configured_table_names
    # Every manager-produced and consumer-referenced table is locally configured in this repo.
    for manager in model.managers:
        for table_name in manager.processor.data_table_names:
            assert table_name in configured
    for consumer in model.consumers:
        assert consumer.table_name in configured


def test_nested_tool_element_form_resolves_outputs():
    # The shed/guid <data_manager><tool file="..."/></data_manager> form must resolve
    # the wrapper's outputs just like the tool_file attribute form.
    model = build_repository_data_tables(FETCH_REPO, data_manager_conf=FETCH_DM_CONF_NESTED)
    assert len(model.managers) == 1
    manager = model.managers[0]
    assert manager.tool_file == "data_manager/data_manager_fetch_genome_all_fasta_dbkeys.xml"
    assert "out_file" in manager.tool_output_names


def test_sample_conf_loc_reports_found_and_is_sample():
    # A missing production loc that resolves via .sample fallback is found but sample-backed;
    # step-2 checks must use `found and not is_sample`, not `found` alone.
    conf = os.path.join(SAMPLE_FALLBACK_REPO, "tool_data_table_conf.xml.sample")
    model = build_repository_data_tables(SAMPLE_FALLBACK_REPO, tool_data_table_confs=[conf])
    foo = {loc.table_name: loc for loc in model.loc_assets}["foo"]
    assert foo.found is True
    assert foo.is_sample is True
    assert foo.path.endswith("foo.loc.sample")


def test_missing_loc_reports_not_found():
    conf = os.path.join(MISSING_LOC_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(MISSING_LOC_REPO, tool_data_table_confs=[conf])
    absent = {loc.table_name: loc for loc in model.loc_assets}["absent"]
    assert absent.found is False
    # No parse runs on an unfound file, so empty errors here is not "clean".
    assert absent.errors == ()


def test_broken_loc_rows_are_captured():
    conf = os.path.join(BROKEN_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(BROKEN_REPO, tool_data_table_confs=[conf])
    broken = {loc.table_name: loc for loc in model.loc_assets}["broken"]
    assert broken.found is True
    # Short row (2 fields) and wrong-separator row (comma-joined) are both too short for index 2.
    assert len(broken.errors) == 2
    assert all("invalid" in message for message in broken.errors)
