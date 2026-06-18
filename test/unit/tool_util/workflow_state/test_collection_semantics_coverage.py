"""Cross-check connection_workflows/ fixtures against collection_semantics.yml
workflow_format_validation references.

Two directions:
1. Every workflow_format_validation.fixture points at a real .gxwf.yml file
   (also checked by semantics.check()).
2. Every top-level .gxwf.yml fixture is referenced by at least one semantics
   example (or appears in KNOWN_ORPHANS below). Validator-only regression
   fixtures that aren't collection-algebra scenarios live in
   connection_workflows/standalone/ and are deliberately not scanned here —
   directory membership is their classification. Top-level placement is the
   forcing function: a fixture put here must back a semantics example.
"""

import glob
import os

from galaxy.model.dataset_collections.types.semantics import (
    connection_workflows_dir,
    load_examples,
    validate_workflow_format_validation_refs,
)

FIXTURES_DIR = connection_workflows_dir()

# Top-level fixtures that are collection-algebra scenarios but can't yet be
# referenced by a semantics example. Validator-only regression fixtures are NOT
# listed here — they live in connection_workflows/standalone/ and aren't scanned
# (directory membership is their classification). This allowlist is reserved for
# genuine blocked promotions; each entry must spell out *why* it can't be wired.
KNOWN_ORPHANS = {
    # Two-tool chained example (split tool produces list:paired, consumer
    # takes paired). Promotion is blocked on a collection_semantics.yml
    # schema extension that supports multi-tool assumptions
    # (``tool1:``/``tool2:``). Track in HARDEN_PLAN follow-up.
    "ok_collection_output_with_map_over",
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
