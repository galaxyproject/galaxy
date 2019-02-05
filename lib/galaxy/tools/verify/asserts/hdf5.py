import io

import h5py


def assert_has_attr(output_bytes, name, value):
    """Asserts the specified HDF5 output has a given key-value pair as HDF5
    attribute"""
    output_temp = io.BytesIO(output_bytes)
    local_attrs = h5py.File(output_temp, 'r').attrs
    assert name in local_attrs and str(local_attrs[name]) == value, (
        "Not a HDF5 file or H5 attributes do not match:\n\t%s\n\n\t(%s : %s)" % (local_attrs.items(), name, value))

def assert_has_keys(output_bytes, keys):
    """ Asserts the specified HDF5 output has exactly the given keys."""
    keys = [k.strip() for k in keys.strip().split(',')]
    h5_keys = sorted(keys)
    output_temp = io.BytesIO(output_bytes)
    local_keys = sorted(list(h5py.File(output_temp, 'r').keys()))
    assert local_keys == h5_keys, "Not a HDF5 file or H5 keys do not match:\n\t%s\n\t%s" % (local_keys, h5_keys)
