import io
import json

import h5py
import numpy as np
import pytest
from h5grove.utils import get_array_stats

from galaxy.datatypes.binary import (
    _h5_incremental_stats,
    _h5_iter_slabs,
    _h5_normalize_selection,
    H5,
    MAX_STRUCTURED_CONTENT_BYTES,
)
from galaxy.exceptions import RequestParameterInvalidException

EMPTY_STATS = {
    "strict_positive_min": None,
    "positive_min": None,
    "min": None,
    "max": None,
    "mean": None,
    "std": None,
}


class FakeDataset:
    def __init__(self, file_name):
        self.file_name_ = file_name

    def get_file_name(self, sync_cache=True):
        return self.file_name_


def make_h5(path, builder):
    with h5py.File(path, "w", libver="latest") as f:
        builder(f)
    return FakeDataset(str(path))


def single_dataset_h5(path, data, name="big"):
    return make_h5(path, lambda f: f.create_dataset(name, data=data))


def stream_slabs(dataset, selection=None, name="big"):
    with h5py.File(dataset.get_file_name(), "r") as f:
        read_slices, result_shape = _h5_normalize_selection(f[name].shape, selection)
        chunks = list(_h5_iter_slabs(f[name], read_slices))
    joined = b"".join(np.ascontiguousarray(chunk).tobytes() for chunk in chunks)
    max_nbytes = max((chunk.nbytes for chunk in chunks), default=0)
    return joined, result_shape, max_nbytes


def compute_stats(dataset, selection=None, name="big"):
    with h5py.File(dataset.get_file_name(), "r") as f:
        read_slices, _ = _h5_normalize_selection(f[name].shape, selection)
        return _h5_incremental_stats(f[name], read_slices)


def structured_content(dataset, content_type, **kwargs):
    return H5().get_structured_content(dataset, content_type=content_type, **kwargs)


def assert_stats_equal(actual, expected):
    for key, expected_value in expected.items():
        if expected_value is None:
            assert actual[key] is None
        else:
            assert actual[key] == pytest.approx(expected_value, rel=1e-6, abs=1e-6)


def test_normalize_selection_multiaxis_mixed():
    read_slices, result_shape = _h5_normalize_selection((4, 8), "1:4,2:8:2")
    assert read_slices == [slice(1, 4, 1), slice(2, 8, 2)]
    assert result_shape == (3, 3)


def test_normalize_selection_trailing_axis_full():
    read_slices, result_shape = _h5_normalize_selection((4, 8), "2")
    assert read_slices == [slice(2, 3, 1), slice(0, 8, 1)]
    assert result_shape == (8,)


def test_normalize_selection_invalid_string_raises():
    with pytest.raises(RequestParameterInvalidException):
        _h5_normalize_selection((10,), "foo")


def test_normalize_selection_too_many_members_raises():
    with pytest.raises(RequestParameterInvalidException):
        _h5_normalize_selection((10,), "1,2")


def test_normalize_selection_out_of_bounds_index_raises():
    with pytest.raises(RequestParameterInvalidException):
        _h5_normalize_selection((10,), "10")


@pytest.mark.parametrize("selection", ["0:10:0", "0:10:-1", "::-2"])
def test_normalize_selection_non_positive_step_rejected(selection):
    with pytest.raises(RequestParameterInvalidException):
        _h5_normalize_selection((10,), selection)


def test_slabs_zero_length_axis(tmp_path):
    dataset = single_dataset_h5(tmp_path / "z.h5", np.zeros((10, 0), dtype=np.uint8))
    joined, _, max_nbytes = stream_slabs(dataset)
    assert joined == b""
    assert max_nbytes <= MAX_STRUCTURED_CONTENT_BYTES


def test_slabs_large_first_axis_with_step(tmp_path):
    data = np.arange(3_000_000, dtype=np.uint8)
    dataset = single_dataset_h5(tmp_path / "step.h5", data)
    joined, _, max_nbytes = stream_slabs(dataset, "0:3000000:2")
    assert max_nbytes <= MAX_STRUCTURED_CONTENT_BYTES
    assert joined == data[0:3000000:2].tobytes()


def test_slabs_1d_bounded_and_lossless(tmp_path):
    data = np.arange(2_500_000, dtype=np.uint8)
    dataset = single_dataset_h5(tmp_path / "d.h5", data)
    joined, _, max_nbytes = stream_slabs(dataset)
    assert max_nbytes <= MAX_STRUCTURED_CONTENT_BYTES
    assert joined == data.tobytes()


def test_slabs_wide_row_forces_trailing_recursion(tmp_path):
    data = np.arange(4 * 2_000_000, dtype=np.uint8).reshape(4, 2_000_000)
    dataset = single_dataset_h5(tmp_path / "wide.h5", data)
    joined, _, max_nbytes = stream_slabs(dataset)
    assert max_nbytes <= MAX_STRUCTURED_CONTENT_BYTES
    assert joined == data.tobytes()


def test_slabs_step_and_int_index(tmp_path):
    data = np.arange(10 * 8, dtype=np.int32).reshape(10, 8)
    dataset = single_dataset_h5(tmp_path / "s.h5", data)
    joined, result_shape, _ = stream_slabs(dataset, "0:10:2,3")
    assert result_shape == (5,)
    assert joined == data[0:10:2, 3].tobytes()


@pytest.mark.parametrize("flatten", [False, True])
def test_npy_streaming_roundtrip(tmp_path, flatten):
    data = np.arange(300 * 400, dtype=np.float32).reshape(300, 400)
    dataset = single_dataset_h5(tmp_path / "npy.h5", data)
    content, headers = structured_content(
        dataset, "data", path="/big", format="npy", flatten="true" if flatten else "false"
    )
    body = b"".join(content)
    assert int(headers["Content-Length"]) == len(body)
    loaded = np.load(io.BytesIO(body))
    expected = data.ravel() if flatten else data
    assert loaded.shape == expected.shape
    assert np.array_equal(loaded, expected)


def test_bin_streaming_exact_length(tmp_path):
    data = np.arange(2_000_000, dtype=np.uint8)
    dataset = single_dataset_h5(tmp_path / "bin.h5", data)
    content, headers = structured_content(dataset, "data", path="/big", format="bin")
    body = b"".join(content)
    assert len(body) == 2_000_000
    assert int(headers["Content-Length"]) == 2_000_000
    assert body == data.tobytes()


def test_csv_streaming_roundtrip(tmp_path):
    data = np.arange(300 * 500, dtype=np.float64).reshape(300, 500)
    dataset = single_dataset_h5(tmp_path / "csv.h5", data)
    content, headers = structured_content(dataset, "data", path="/big", format="csv")
    body = b"".join(content)
    assert headers["Content-Type"] == "text/csv"
    loaded = np.loadtxt(io.BytesIO(body), delimiter=",")
    assert loaded.shape == (300, 500)
    assert np.allclose(loaded, data)


def test_csv_rejects_more_than_two_dimensions(tmp_path):
    dataset = single_dataset_h5(tmp_path / "c3.h5", np.zeros((4, 4, 4), dtype=np.float64))
    with pytest.raises(RequestParameterInvalidException):
        structured_content(dataset, "data", path="/big", format="csv")


def test_csv_rejects_non_numeric(tmp_path):
    dataset = single_dataset_h5(tmp_path / "cs.h5", np.array([b"abc", b"def"], dtype="S3"))
    with pytest.raises(RequestParameterInvalidException):
        structured_content(dataset, "data", path="/big", format="csv")


def test_incremental_stats_float_with_nan_inf(tmp_path):
    rng = np.random.default_rng(0)
    data = rng.standard_normal(500_000).astype(np.float64)
    data[10] = np.nan
    data[20] = np.inf
    data[30] = -np.inf
    dataset = single_dataset_h5(tmp_path / "f.h5", data)
    assert_stats_equal(compute_stats(dataset), get_array_stats(data[np.isfinite(data)]))


def test_incremental_stats_int(tmp_path):
    data = np.arange(-100, 100, dtype=np.int64)
    dataset = single_dataset_h5(tmp_path / "i.h5", data)
    assert_stats_equal(compute_stats(dataset), get_array_stats(data))


def test_incremental_stats_all_nan(tmp_path):
    dataset = single_dataset_h5(tmp_path / "n.h5", np.full(1000, np.nan, dtype=np.float64))
    assert compute_stats(dataset) == EMPTY_STATS


def test_over_limit_json_data_rejected(tmp_path):
    dataset = single_dataset_h5(tmp_path / "big.h5", np.zeros(2_000_000, dtype=np.uint8))
    with pytest.raises(RequestParameterInvalidException):
        structured_content(dataset, "data", path="/big", format="json")


def test_over_limit_json_data_allowed_with_selection(tmp_path):
    data = np.arange(2_000_000, dtype=np.uint8) % 251
    dataset = single_dataset_h5(tmp_path / "big.h5", data)
    content, _ = structured_content(dataset, "data", path="/big", format="json", selection="0:100")
    assert json.loads(content) == data[0:100].tolist()


def test_invalid_selection_rejected(tmp_path):
    dataset = single_dataset_h5(tmp_path / "s.h5", np.zeros(100, dtype=np.uint8))
    with pytest.raises(RequestParameterInvalidException):
        structured_content(dataset, "data", path="/big", format="json", selection="foo")


def test_attribute_guard(tmp_path):
    def builder(f):
        ds = f.create_dataset("big", data=np.zeros(10, dtype=np.uint8))
        ds.attrs["huge"] = np.zeros(200_000, dtype=np.float64)

    dataset = make_h5(tmp_path / "a.h5", builder)
    with pytest.raises(RequestParameterInvalidException):
        structured_content(dataset, "attr", path="/big")


def test_group_guard(tmp_path, monkeypatch):
    monkeypatch.setattr("galaxy.datatypes.binary.MAX_STRUCTURED_CONTENT_CHILDREN", 3)

    def builder(f):
        group = f.create_group("g")
        for i in range(5):
            group.create_dataset(f"d{i}", data=np.zeros(1, dtype=np.uint8))

    dataset = make_h5(tmp_path / "g.h5", builder)
    with pytest.raises(RequestParameterInvalidException):
        structured_content(dataset, "meta", path="/g")


def test_vlen_over_limit_rejected(tmp_path):
    def builder(f):
        ds = f.create_dataset("v", (2000,), dtype=h5py.string_dtype())
        ds[...] = np.array(["x"] * 2000, dtype=object)

    dataset = make_h5(tmp_path / "v.h5", builder)
    with pytest.raises(RequestParameterInvalidException):
        structured_content(dataset, "data", path="/v", format="json")


def test_null_dataspace_data_json(tmp_path):
    dataset = make_h5(tmp_path / "e.h5", lambda f: f.create_dataset("empty", dtype="f8"))
    content, _ = structured_content(dataset, "data", path="/empty", format="json")
    assert json.loads(content) is None


def test_null_dataspace_stats(tmp_path):
    dataset = make_h5(tmp_path / "e.h5", lambda f: f.create_dataset("empty", dtype="f8"))
    content, _ = structured_content(dataset, "stats", path="/empty")
    assert json.loads(content) == EMPTY_STATS
