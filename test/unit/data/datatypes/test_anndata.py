import json

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


@pytest.mark.parametrize(
    ("filename", "expected_shape"),
    [
        ("adata_0_6_small.h5ad", (10, 10)),
        ("adata_0_6_small2.h5ad", (50, 50)),
        ("adata_0_7_4_small.h5ad", (50, 100)),
        ("adata_unk.h5ad", (50, 100)),
    ],
)
def test_set_meta_shape_from_sparse_x(filename, expected_shape):
    """A sparse ``X`` keeps its dimensions in HDF5 attributes.

    h5py returns those as a numpy array of numpy integers, which are not JSON
    serializable, so they have to be converted before being stored as metadata.
    """
    with get_dataset(filename) as dataset:
        dataset.metadata.shape = (-1, -1)
        dataset.metadata.obs_names = []
        Anndata().set_meta(dataset=dataset)
        assert dataset.metadata.shape == expected_shape
        assert all(type(dim) is int for dim in dataset.metadata.shape)
        json.dumps(dataset.metadata.shape)


def test_set_meta_shape_from_dense_x():
    """A dense ``X`` is an h5py dataset, whose ``shape`` is already plain ints."""
    with get_dataset("pbmc3k_tiny.h5ad") as dataset:
        dataset.metadata.shape = (-1, -1)
        dataset.metadata.obs_names = []
        Anndata().set_meta(dataset=dataset)
        assert all(type(dim) is int for dim in dataset.metadata.shape)
        json.dumps(dataset.metadata.shape)
