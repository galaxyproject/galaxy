"""Seed a Galaxy history with mid-state data for the staining quantification
eval use case.

Creates a history populated with the shape of data the use case's later
prompts assume:

- one or more brightfield RGB inputs (stub TIFFs)
- a region-of-interest mask
- a color-deconvolution output
- a tabular quantification result with per-ROI intensity summaries

The contents are structurally correct but synthetic -- the agents reason
about the history's shape, not the pixel values. Swap in real images for
demo rehearsals.

Used by:
- ``test/integration/test_live_evals.py`` as a fixture for the pytest
  live-eval runner.
- Standalone runs against a real Galaxy to set up the demo history in
  seconds.

Standalone usage (against a running Galaxy):

    python test/evals/seed_staining_quantification_history.py \\
        --galaxy-url http://localhost:8080 \\
        --galaxy-api-key <key>

In-test usage:

    from evals.seed_staining_quantification_history import seed_demo_history
    history_id = seed_demo_history(dataset_populator)
"""

import argparse
import io
import sys
from typing import (
    Any,
    Optional,
)

HISTORY_NAME = "Staining quantification (eval fixture)"

# Stub TIFF bytes -- structurally correct minimal TIFF header. The agents only
# need to see that the dataset exists with the right file type / extension.
# Real demo runs swap these for actual staining images.
_STUB_TIFF = (
    b"II*\x00\x08\x00\x00\x00"  # little-endian TIFF magic + IFD offset
    b"\x00\x00"  # zero IFD entries
    b"\x00\x00\x00\x00"  # next IFD offset = 0
)

_QUANTIFICATION_CSV = """region_id\tarea_pixels\tmean_intensity_brown\tmean_intensity_blue\tpct_positive
1\t12450\t142.3\t98.1\t41.2
2\t8230\t168.7\t72.4\t58.9
3\t15670\t121.5\t110.8\t29.4
"""

_HISTORY_ANNOTATION = (
    "Histological staining quantification flow. Brightfield RGB inputs "
    "(slide_01, slide_02) -> ROI mask -> color deconvolution isolating "
    "the brown stain channel -> per-ROI intensity / area quantification. "
    "Final output: staining_quantification_per_roi.tabular with per-region "
    "area_pixels, mean_intensity_brown, mean_intensity_blue, and pct_positive."
)


def seed_demo_history(dataset_populator: Any) -> str:
    """Create the demo history and seed it via the given DatasetPopulator.

    Returns the new history's id. The DatasetPopulator interface is the same
    one Galaxy integration tests use; pass either the test's
    ``self.dataset_populator`` or a fresh ``DatasetPopulator`` built from a
    ``GalaxyInteractor``.
    """
    history_id = dataset_populator.new_history(name=HISTORY_NAME)

    # Binary uploads need to go through the file-upload path (the populator's
    # default path does ``"://" in content`` to detect URLs, which fails on
    # bytes). Wrapping in BytesIO triggers the ``hasattr(content, "read")``
    # branch instead.
    def _tiff_blob() -> io.BytesIO:
        return io.BytesIO(_STUB_TIFF)

    dataset_populator.new_dataset(
        history_id,
        content=_tiff_blob(),
        file_type="tiff",
        name="slide_01_brightfield.tiff",
        to_posix_lines=False,
        auto_decompress=False,
        wait=True,
    )
    dataset_populator.new_dataset(
        history_id,
        content=_tiff_blob(),
        file_type="tiff",
        name="slide_02_brightfield.tiff",
        to_posix_lines=False,
        auto_decompress=False,
        wait=True,
    )
    dataset_populator.new_dataset(
        history_id,
        content=_tiff_blob(),
        file_type="tiff",
        name="rois.tiff",
        to_posix_lines=False,
        auto_decompress=False,
        wait=True,
    )
    dataset_populator.new_dataset(
        history_id,
        content=_tiff_blob(),
        file_type="tiff",
        name="deconvolved_brown_channel.tiff",
        to_posix_lines=False,
        auto_decompress=False,
        wait=True,
    )
    dataset_populator.new_dataset(
        history_id,
        content=_QUANTIFICATION_CSV,
        file_type="tabular",
        name="staining_quantification_per_roi.tabular",
        wait=True,
    )

    # History-level annotation gives the agent a context summary even before
    # it dives into per-dataset metadata -- without this, prompts like
    # "draft a post about my analysis" can't ground their output on anything
    # more specific than the history name.
    dataset_populator.update_history(history_id, {"annotation": _HISTORY_ANNOTATION})

    return history_id


def _standalone_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--galaxy-url", required=True, help="Base URL of the running Galaxy.")
    parser.add_argument("--galaxy-api-key", required=True, help="API key for the user to seed for.")
    args = parser.parse_args(argv)

    from typing import cast

    from galaxy.tool_util.verify.interactor import GalaxyInteractorApi
    from galaxy_test.base.api import ApiTestInteractor
    from galaxy_test.base.populators import DatasetPopulator

    interactor = GalaxyInteractorApi(
        galaxy_url=args.galaxy_url,
        master_api_key=args.galaxy_api_key,
        api_key=args.galaxy_api_key,
    )
    # DatasetPopulator's interactor protocol is satisfied by both
    # GalaxyInteractorApi (used here for standalone runs) and
    # ApiTestInteractor (used by the pytest fixture), but the populator's
    # signature only names the test type. Cast at this boundary.
    populator = DatasetPopulator(cast(ApiTestInteractor, interactor))
    history_id = seed_demo_history(populator)
    print(f"Seeded history '{HISTORY_NAME}' at id {history_id}")
    return 0


if __name__ == "__main__":
    sys.exit(_standalone_main())
