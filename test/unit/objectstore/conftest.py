import pytest


@pytest.fixture
def clean_memory_fs():
    # Imported lazily so this conftest doesn't require fsspec when the objectstore package
    # is tested in isolation (only the tests that use this fixture need fsspec).
    from fsspec.implementations.memory import MemoryFileSystem

    # MemoryFileSystem shares one process-global store across instances; isolate each test.
    MemoryFileSystem.store.clear()
    MemoryFileSystem.pseudo_dirs[:] = [""]
    yield
    MemoryFileSystem.store.clear()
    MemoryFileSystem.pseudo_dirs[:] = [""]
