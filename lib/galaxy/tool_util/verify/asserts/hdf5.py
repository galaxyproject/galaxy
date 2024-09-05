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
    local_attrs = h5py.File(output_temp, "r").attrs
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

    h5py.File(output_temp, "r").visit(append_keys)
    missing = 0
    for key in h5_keys:
        if key not in local_keys:
            missing += 1
    assert missing == 0, f"Not a HDF5 file or H5 keys missing:\n\t{local_keys}\n\t{h5_keys}"

def assert_has_h5ad_group_entry(output_bytes: bytes, group: str, entry: str) -> None:
    """Asserts the specified HDF5 group has a given entry-value pair."""
    _assert_h5py()
    h5_entries = sorted([e.strip() for e in entry.strip().split(",")])
    output_temp = io.BytesIO(output_bytes)
    
    with h5py.File(output_temp, "r") as h5file:
        if group not in list(h5file.keys()):
            raise KeyError(f"group '{group}' not found in HDF5 file.")
        
        group = list(h5file[group].keys())
        
    missing=0
    for entry in h5_entries:
        if entry not in group:
            missing+=1
    
    assert (
        missing == 0
    ), f"Expected entries '{h5_entries}' for group '{group}' in h5ad file does not match.\n\n\Found: {h5_entries}"