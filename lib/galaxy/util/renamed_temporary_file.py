"""Safely write file to temporary file and then move file into place."""
# Copied from https://stackoverflow.com/a/12007885.
import os
import tempfile


class RenamedTemporaryFile:
    """
    A temporary file object which will be renamed to the specified
    path on exit.
    """

    def __init__(self, final_path, **kwargs):
        """
        >>> dir = tempfile.mkdtemp()
        >>> with RenamedTemporaryFile(os.path.join(dir, 'test.txt'), mode="w") as out:
        ...     _ = out.write('bla')
        """
        tmpfile_dir = kwargs.pop("dir", None)

        # Put temporary file in the same directory as the location for the
        # final file so that an atomic move into place can occur.

        if tmpfile_dir is None:
            tmpfile_dir = os.path.dirname(final_path)

        self.tmpfile = tempfile.NamedTemporaryFile(dir=tmpfile_dir, delete=False, **kwargs)
        self.final_path = final_path

    def __getattr__(self, attr):
        """
        Delegate attribute access to the underlying temporary file object.
        """
        return getattr(self.tmpfile, attr)

    def __enter__(self):
        self.tmpfile.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.tmpfile.flush()
            self.tmpfile.__exit__(exc_type, exc_val, exc_tb)
            os.rename(self.tmpfile.name, self.final_path)
        else:
            self.tmpfile.__exit__(exc_type, exc_val, exc_tb)
        return False
