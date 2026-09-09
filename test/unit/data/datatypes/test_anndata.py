import pytest

from galaxy.datatypes.binary import Anndata
from .util import get_dataset


@pytest.mark.parametrize(
    ("filename", "expected_version"),
    [
        ("adata_0_6_small.h5ad", ""),
        ("adata_0_7_4_small.h5ad", ""),
        ("adata_noX.h5ad", "0.1.0"),
        ("adata_unk.h5ad", ""),
        ("adata_unk2.h5ad", ""),
        ("pbmc3k_tiny.h5ad", ""),
    ],
)
def test_set_meta_sets_anndata_spec_version(filename, expected_version):
    with get_dataset(filename) as dataset:
        dataset.metadata.shape = (-1, -1)
        dataset.metadata.obs_names = []
        Anndata().set_meta(dataset=dataset)
        assert dataset.metadata.anndata_spec_version == expected_version
