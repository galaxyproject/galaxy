import io

try:
    import h5py
except ImportError:
    h5py = None

IMPORT_MISSING_MESSAGE = "h5 assertion requires unavailable optional dependency h5py"


def _assert_h5py():
    if h5py is None:
        raise Exception(IMPORT_MISSING_MESSAGE)


def assert_has_h5_attribute(output_bytes: bytes, key: str, value: str) -> None:
    """Asserts the specified HDF5 output has a given key-value pair as HDF5
    attribute"""
    _assert_h5py()
    output_temp = io.BytesIO(output_bytes)
    with h5py.File(output_temp, "r", locking=False) as h5:
        local_attrs = h5.attrs
        assert (
            key in local_attrs and str(local_attrs[key]) == value
        ), f"Not a HDF5 file or H5 attributes do not match:\n\t{list(local_attrs.items())}\n\n\t({key} : {value})"


# TODO the function actually queries groups. so the function and argument name are misleading
def assert_has_h5_keys(output_bytes: bytes, keys: str) -> None:
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
