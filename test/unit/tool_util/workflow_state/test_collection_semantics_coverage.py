"""Cross-check connection_workflows/ fixtures against collection_semantics.yml
workflow_format_validation references.

Two directions:
1. Every workflow_format_validation.fixture points at a real .gxwf.yml file
   (also checked by semantics.check()).
2. Every .gxwf.yml fixture either is referenced by at least one semantics
   example or appears in KNOWN_ORPHANS below. This keeps new fixtures honest
   without forcing coverage for cases that are intentionally out-of-scope
   for collection_semantics.yml (e.g. gxformat2 passthrough plumbing that
   isn't a collection-algebra scenario).
"""

import glob
import os

from galaxy.model.dataset_collections.types.semantics import (
    connection_workflows_dir,
    load_examples,
    validate_workflow_format_validation_refs,
)

FIXTURES_DIR = connection_workflows_dir()

# Fixtures that don't correspond to a collection_semantics.yml example.
# Fixture-side concerns (tool-level passthroughs, multi-input plumbing,
# workflow chaining) that aren't about collection-type algebra sit here.
# Each entry must spell out *why* it's not promotable to a semantics example.
KNOWN_ORPHANS = {
    # Validator-internal: exercises the ``collection_type_source`` inspector
    # tool (a synthetic test tool whose output type is derived from the
    # input collection type at validation time). Tests retyping mechanics,
    # not a single semantic claim about a collection type.
    "ok_any_collection_accepts_list",
    # Plumbing: end-to-end map-over propagation across a 3-step dataset
    # chain. Exercises the workflow-graph engine's map-over forwarding,
    # not a single collection_semantics.yml claim.
    "ok_chain_map_over_propagates",
    # Two-tool chained example (split tool produces list:paired, consumer
    # takes paired). Promotion is blocked on a collection_semantics.yml
    # schema extension that supports multi-tool assumptions
    # (``tool1:``/``tool2:``). Track in HARDEN_PLAN follow-up.
    "ok_collection_output_with_map_over",
    # Validator-internal: same ``collection_type_source`` inspector path
    # as ok_any_collection_accepts_list — tests output-type extraction
    # mechanics rather than catalog semantics.
    "ok_collection_type_source",
    # Pure non-collection passthrough (dataset -> dataset). No collection
    # algebra in play; covered implicitly by every other ok_* fixture.
    "ok_dataset_to_dataset",
    # Validator-internal: exercises the ``structured_like`` output
    # modifier (an output whose type is structurally borrowed from a
    # named input). Tests validator retyping, not a catalog claim.
    "ok_structured_like",
    # Multi-input map-over composition: two list inputs both contribute
    # ``list`` → step map-over resolves to ``list``. Tests
    # ``_resolve_step_map_over`` aggregation across siblings, not a
    # single-input semantic claim.
    "ok_two_list_inputs_map_over",
    # Multi-input direct-match plumbing: paired -> paired slot (direct
    # match, no contribution) + dataset -> dataset slot (direct match,
    # no contribution) → no step-level map-over. Tests the
    # no-contribution path through ``_resolve_step_map_over``.
    "ok_paired_and_data_no_map_over",
    # Subworkflow plumbing: data passes through an inline subworkflow
    # unchanged (data_input -> inner cat -> exposed output -> outer cat).
    # Exercises subworkflow output resolution + downstream consumption,
    # not a single collection-algebra claim.
    "ok_subworkflow_passthrough",
    # Subworkflow type propagation: list:paired enters subworkflow,
    # paired-typed inner tool maps over list, exposed output becomes
    # ``list``, and outer step inherits that map-over. Exercises
    # subworkflow output retyping under map-over, not a single
    # catalog claim.
    "ok_subworkflow_list_propagation",
    # Map-over inside subworkflow: outer feeds ``list`` into a
    # subworkflow whose inner tool expects a dataset; inner maps over,
    # exposed output is ``list``, outer list-typed slot consumes it
    # directly. Exercises map-over arising inside a subworkflow.
    "ok_subworkflow_map_over",
    # Pure dataset chain: input -> gx_data -> gx_data, no collections.
    # Exercises multi-step output forwarding through dataset slots, not
    # a single collection-algebra claim.
    "ok_simple_chain_dataset",
    # sample_sheet collection -> data(multiple=true) reduction. The
    # validator normalizes sample_sheet to list-like for reduction.
    # Tests the multi-data-input fall-through, not a catalog claim
    # about sample_sheet (the catalog claims live under SAMPLE_SHEET_*
    # examples covered by algebra).
    "ok_sample_sheet_to_multi_data",
    # Inline user-defined-tool (UDT) fixtures. Each defines its tool
    # inline via ``class: GalaxyUserTool`` (or ``GalaxyWorkflow``) rather
    # than referencing a ``tool_id``; they exercise inline tool/subworkflow
    # resolution in the connection graph. The collection algebra in each is
    # mundane and already covered by built-in-tool examples — the catalog
    # has no vocabulary for inline tool definitions, so these stay orphans.
    # dataset -> inline UDT -> dataset; data->data passthrough algebra.
    "ok_udt_to_regular_dataset",
    # regular tool -> inline UDT dataset input; data->data passthrough.
    "ok_regular_to_udt_dataset",
    # inline UDT -> inline UDT dataset chain; data->data forwarding.
    "ok_udt_chain",
    # list collection into an inline UDT's data_collection(list) input;
    # direct list->list match, no map-over.
    "ok_udt_collection_input",
    # list mapped over an inline UDT's scalar data input; scalar output
    # promoted to list (BASIC_MAPPING algebra, inline-tool variant).
    "ok_udt_map_over_list",
    # inline UDT nested in an inline subworkflow; data passthrough +
    # subworkflow output resolution, not a catalog claim.
    "ok_udt_in_subworkflow",
    # inline UDT dataset output into a list-required consumer; locks
    # consumer-side error attribution for a reduction mismatch.
    "fail_udt_dataset_to_collection_consumer",
    # paired collection into an inline UDT's list-collection input;
    # incompatible-feed rejection, inline-tool variant.
    "fail_paired_to_udt_list_collection",
}

# Examples intentionally covered by neither ``tests.algebra`` nor
# ``tests.workflow_format_validation``. Each entry is the reason the example
# is out of scope for those two coverage modes; the example still lives in
# tool_runtime / workflow_runtime / workflow_editor coverage.
EXPECTED_NEITHER = {
    # Runtime-only: mixed dataset + collection input; validity claim is
    # about runtime mapping behavior, not pure type algebra.
    "BASIC_MAPPING_INCLUDING_SINGLE_DATASET",
    # Runtime-only: two-input peer zip-match; validity claim is about
    # runtime structure matching of linked inputs, not type algebra.
    "BASIC_MAPPING_TWO_INPUTS_WITH_IDENTICAL_STRUCTURE",
}


def _all_fixture_stems() -> set[str]:
    paths = glob.glob(os.path.join(FIXTURES_DIR, "*.gxwf.yml"))
    return {os.path.basename(p)[: -len(".gxwf.yml")] for p in paths}


def _referenced_fixture_stems() -> set[str]:
    stems = set()
    for ex in load_examples():
        if ex.tests and ex.tests.workflow_format_validation and ex.tests.workflow_format_validation.fixture:
            stems.add(ex.tests.workflow_format_validation.fixture)
    return stems


def test_workflow_format_validation_fixtures_exist():
    errors = validate_workflow_format_validation_refs(load_examples())
    assert errors == [], errors


def test_all_fixtures_referenced_or_flagged_orphan():
    all_stems = _all_fixture_stems()
    referenced = _referenced_fixture_stems()
    unreferenced = all_stems - referenced - KNOWN_ORPHANS
    assert not unreferenced, (
        f"Fixtures without a collection_semantics.yml workflow_format_validation "
        f"entry and not in KNOWN_ORPHANS: {sorted(unreferenced)}. Either add a "
        f"`workflow_format_validation: {{fixture: <stem>}}` block to a matching "
        f"example or add the stem to KNOWN_ORPHANS with a reason."
    )


def test_orphan_allowlist_entries_exist():
    all_stems = _all_fixture_stems()
    stale = KNOWN_ORPHANS - all_stems
    assert not stale, f"KNOWN_ORPHANS lists missing fixtures: {sorted(stale)}"


def test_expected_neither_classification_is_accurate():
    """Every example is covered by algebra, a fixture, or is in EXPECTED_NEITHER.

    Catches both directions: a new "neither" example forces an explicit
    classification decision, and an EXPECTED_NEITHER entry that gains
    coverage gets flagged so the allowlist stays honest.
    """
    neither = set()
    labels = set()
    for ex in load_examples():
        labels.add(ex.label)
        has_algebra = bool(ex.tests and ex.tests.algebra)
        has_fixture = bool(ex.tests and ex.tests.workflow_format_validation)
        if not has_algebra and not has_fixture:
            neither.add(ex.label)

    unexpected = neither - EXPECTED_NEITHER
    assert not unexpected, (
        f"Examples without algebra or workflow_format_validation coverage "
        f"and not in EXPECTED_NEITHER: {sorted(unexpected)}. Either add a "
        f"`tests.algebra` or `tests.workflow_format_validation` block or "
        f"add the label to EXPECTED_NEITHER with a reason."
    )
    now_covered = EXPECTED_NEITHER & (labels - neither)
    assert not now_covered, (
        f"Labels in EXPECTED_NEITHER that now have algebra or fixture "
        f"coverage: {sorted(now_covered)}. Remove them from EXPECTED_NEITHER."
    )
    missing = EXPECTED_NEITHER - labels
    assert not missing, f"EXPECTED_NEITHER references labels not in collection_semantics.yml: {sorted(missing)}"
