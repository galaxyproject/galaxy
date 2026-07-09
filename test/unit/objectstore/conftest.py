import pytest
from fsspec.implementations.memory import MemoryFileSystem


@pytest.fixture
def clean_memory_fs():
    # MemoryFileSystem shares one process-global store across instances; isolate each test.
    MemoryFileSystem.store.clear()
    MemoryFileSystem.pseudo_dirs[:] = [""]
    yield
    MemoryFileSystem.store.clear()
    MemoryFileSystem.pseudo_dirs[:] = [""]
