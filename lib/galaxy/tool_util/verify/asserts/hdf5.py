import io

try:
    import h5py
except ImportError:
    h5py = None

from ._types import (
    Annotated,
    AssertionParameter,
    OutputBytes,
)

IMPORT_MISSING_MESSAGE = "h5 assertion requires unavailable optional dependency h5py"

Key = Annotated[str, AssertionParameter("HDF5 attribute to check value of.")]
Value = Annotated[str, AssertionParameter("Expected value of HDF5 attribute to check.")]
Keys = Annotated[str, AssertionParameter("HDF5 attributes to check value of as a comma-separated string.")]


def _assert_h5py():
    if h5py is None:
        raise Exception(IMPORT_MISSING_MESSAGE)


def assert_has_h5_attribute(output_bytes: OutputBytes, key: Key, value: Value) -> None:
    """Asserts HDF5 output contains the specified ``value`` for an attribute (``key``), e.g.

    ```xml
    <has_h5_attribute key="nchroms" value="15" />
    ```
    """
    _assert_h5py()
    output_temp = io.BytesIO(output_bytes)
    with h5py.File(output_temp, "r", locking=False) as h5:
        local_attrs = h5.attrs
        assert (
            key in local_attrs and str(local_attrs[key]) == value
        ), f"Not a HDF5 file or H5 attributes do not match:\n\t{[(key, str(value)) for key, value in local_attrs.items()]}\n\n\t({key} : {value})"


# TODO the function actually queries groups. so the function and argument name are misleading
def assert_has_h5_keys(output_bytes: OutputBytes, keys: Keys) -> None:
    """Asserts the specified HDF5 output has the given keys."""
    _assert_h5py()
    h5_keys = sorted([k.strip() for k in keys.strip().split(",")])
    output_temp = io.BytesIO(output_bytes)
    local_keys = []

    def append_keys(key):
        local_keys.append(key)
        return None

    with h5py.File(output_temp, "r", locking=False) as f:
        f.visit(append_keys)
        missing = 0
        for key in h5_keys:
            if key not in local_keys:
                missing += 1
        assert missing == 0, f"Not a HDF5 file or H5 keys missing:\n\t{local_keys}\n\t{h5_keys}"
