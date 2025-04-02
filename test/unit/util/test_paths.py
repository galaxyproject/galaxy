import ntpath
import os
import posixpath

from galaxy.util import in_directory


def test_in_directory(tmp_path):
    safe_dir = os.path.join(tmp_path, "user")
    os.mkdir(safe_dir)
    good_file = os.path.join(safe_dir, "1")
    with open(good_file, "w") as f:
        f.write("hello")
    assert in_directory(good_file, safe_dir)

    assert not in_directory("/other/file/is/here.txt", safe_dir)

    unsafe_link = os.path.join(safe_dir, "2")
    os.symlink("/other/file/bad.fasta", unsafe_link)
    assert not in_directory(unsafe_link, safe_dir)

    # Test local_path_module parameter
    if os.path == posixpath:
        assert in_directory(good_file, safe_dir, local_path_module=ntpath)
    elif os.path == ntpath:
        assert in_directory(good_file, safe_dir, local_path_module=posixpath)
