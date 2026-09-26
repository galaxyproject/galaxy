"""Regenerate the IWC catalog fixture from what iwc.galaxyproject.org serves.

    python test/integration/curated_workflows/sync_iwc_catalog.py

Downloads the live manifest, projects it the same way the refresh task does,
keeps the handful of workflows listed below, and writes the file the task
would have written, so the integration tests serve real catalog rows rather
than hand-built ones. Re-run it whenever ``CURATED_PROJECTION_VERSION`` changes
(Galaxy ignores a projection of any other version) or IWC drifts far enough
that the fixture no longer looks like the real thing, then review the diff.
"""

import json
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, "lib")))

from galaxy.workflow import (
    curated,
    iwc_manifest,
)

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iwc_catalog", "iwc_workflows.json")

# Picked to cover several collections, one workflow in two collections, one in
# none, and a spread of update times and tags.
SELECTED_IWC_IDS = [
    "ploidy-aware-genotype-calling-main",
    "average-bigwig-between-replicates-main",
    "rnaseq-de-main",
    "bacterial-genome-assembly-main",
    "assembly-with-flye-main",
    "functional-annotation-of-sequences-main",
]

# An integration Galaxy loads only the upload tool, so no real IWC workflow can
# run there. These stand in for workflows that would, which is what lets the
# tests see the runnable-first ordering at all.
RUNNABLE_IWC_IDS = {"rnaseq-de-main", "functional-annotation-of-sequences-main"}
RUNNABLE_TOOL_IDS = ["upload1"]


def main() -> None:
    projected = {entry["id"]: entry for entry in curated.project_manifest(iwc_manifest.download_manifest(timeout=60))}
    missing = [iwc_id for iwc_id in SELECTED_IWC_IDS if iwc_id not in projected]
    if missing:
        sys.exit(f"No longer in the IWC manifest, pick replacements: {', '.join(missing)}")
    # The tests sort on update_time and compare missing tools against tool_ids, so an entry
    # without either (no date upstream, or a subworkflow that can't be resolved offline) would
    # break them rather than exercise anything.
    incomplete = [
        iwc_id
        for iwc_id in SELECTED_IWC_IDS
        if projected[iwc_id]["update_time"] is None or projected[iwc_id]["tool_ids"] is None
    ]
    if incomplete:
        sys.exit(f"Missing an update time or tool ids, pick replacements: {', '.join(incomplete)}")
    entries = []
    for iwc_id in SELECTED_IWC_IDS:
        entry = projected[iwc_id]
        if iwc_id in RUNNABLE_IWC_IDS:
            entry = {**entry, "tool_ids": RUNNABLE_TOOL_IDS}
        entries.append(entry)
    os.makedirs(os.path.dirname(FIXTURE_PATH), exist_ok=True)
    with open(FIXTURE_PATH, "w") as fh:
        # Same payload as ``curated.write_projection``, indented so a re-sync diffs cleanly.
        json.dump({"version": curated.CURATED_PROJECTION_VERSION, "workflows": entries}, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"Wrote {len(entries)} workflows to {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
