import time
from pathlib import Path

import pytest

from galaxy.exceptions import (
    MessageException,
    ObjectNotFound,
)
from galaxy.short_term_storage import (
    ShortTermStorageConfiguration,
    ShortTermStorageManager,
    ShortTermStorageServeCancelledInformation,
    ShortTermStorageServeCompletedInformation,
    ShortTermStorageTargetSecurity,
    storage_context,
)

TEST_FILENAME = "moo.txt"
TEST_MIME_TYPE = "text/plain"
TEST_SLEEP_DURATION = 0.25


def test_typical_usage(tmpdir):
    config = ShortTermStorageConfiguration(short_term_storage_directory=tmpdir)
    manager = ShortTermStorageManager(config=config)
    security = ShortTermStorageTargetSecurity(
        user_id=12,
    )
    short_term_storage_target = manager.new_target(
        TEST_FILENAME,
        TEST_MIME_TYPE,
        security=security,
    )
    assert short_term_storage_target
    assert not manager.is_ready(short_term_storage_target)
    with open(short_term_storage_target.raw_path, "w") as f:
        f.write("Moo Cow!!!")

    # exercise recovering target from request id...
    short_term_storage_target = manager.recover_target(short_term_storage_target.request_id)

    manager.finalize(short_term_storage_target)
    assert manager.is_ready(short_term_storage_target)
    serve_info = manager.get_serve_info(short_term_storage_target)
    assert serve_info
    assert isinstance(serve_info, ShortTermStorageServeCompletedInformation)
    assert serve_info.security.user_id == 12
    with serve_info.target.path.open() as f:
        assert f.read() == "Moo Cow!!!"


def test_cancel_with_message_exception(tmpdir):
    config = ShortTermStorageConfiguration(short_term_storage_directory=tmpdir)
    manager = ShortTermStorageManager(config=config)
    short_term_storage_target = manager.new_target(
        TEST_FILENAME,
        TEST_MIME_TYPE,
    )
    assert short_term_storage_target
    assert not manager.is_ready(short_term_storage_target)
    exception = MessageException("moo cow")
    manager.cancel(short_term_storage_target, exception=exception)
    assert manager.is_ready(short_term_storage_target)
    serve_info = manager.get_serve_info(short_term_storage_target)
    assert serve_info
    assert isinstance(serve_info, ShortTermStorageServeCancelledInformation)
    exc = serve_info.message_exception
    assert exc.err_code.code == 0


def test_cancel_with_arbitrary_exception(tmpdir):
    config = ShortTermStorageConfiguration(short_term_storage_directory=tmpdir)
    manager = ShortTermStorageManager(config=config)
    short_term_storage_target = manager.new_target(
        TEST_FILENAME,
        TEST_MIME_TYPE,
    )
    assert short_term_storage_target
    assert not manager.is_ready(short_term_storage_target)
    exception_raised = False
    try:
        with storage_context(short_term_storage_target.request_id, manager):
            raise Exception("Moo Cow...")
    except Exception:
        exception_raised = True
    assert exception_raised
    assert manager.is_ready(short_term_storage_target)
    serve_info = manager.get_serve_info(short_term_storage_target)
    assert serve_info
    assert isinstance(serve_info, ShortTermStorageServeCancelledInformation)
    exc = serve_info.message_exception
    assert exc.status_code == 500
    assert exc.err_code.code == 500001
    assert "Moo Cow..." in str(exc)


def test_cleanup(tmpdir):
    config = ShortTermStorageConfiguration(
        short_term_storage_directory=tmpdir,
        maximum_storage_duration=TEST_SLEEP_DURATION / 10,
    )
    manager = ShortTermStorageManager(config=config)
    short_term_storage_target = manager.new_target(
        TEST_FILENAME,
        TEST_MIME_TYPE,
    )
    short_term_storage_target.path.touch()
    assert short_term_storage_target.path.exists()
    time.sleep(TEST_SLEEP_DURATION)
    manager.cleanup()
    assert not short_term_storage_target.path.exists()


def test_cleanup_no_op_if_duration_not_reached(tmpdir):
    config = ShortTermStorageConfiguration(
        short_term_storage_directory=tmpdir,
        maximum_storage_duration=100,
    )
    manager = ShortTermStorageManager(config=config)
    short_term_storage_target = manager.new_target(
        TEST_FILENAME,
        TEST_MIME_TYPE,
    )
    short_term_storage_target.path.touch()
    assert short_term_storage_target.path.exists()
    time.sleep(TEST_SLEEP_DURATION)
    manager.cleanup()
    assert short_term_storage_target.path.exists()


def test_cleanup_if_metadata_not_found(tmpdir):
    config = ShortTermStorageConfiguration(
        short_term_storage_directory=tmpdir,
        maximum_storage_duration=100,
    )
    manager = ShortTermStorageManager(config=config)
    short_term_storage_target = manager.new_target(
        TEST_FILENAME,
        TEST_MIME_TYPE,
    )
    short_term_storage_target.path.touch()
    # Force metadata file deletion only
    parent_directory_path = Path(short_term_storage_target.path.parent)
    for metadata_file_path in parent_directory_path.glob("*.json"):
        metadata_file_path.unlink()
    assert short_term_storage_target.path.exists()

    manager.cleanup()
    # If the metadata is lost, the target will be deleted
    assert not short_term_storage_target.path.exists()


def test_serve_non_existent_raises_object_not_found(tmpdir):
    config = ShortTermStorageConfiguration(
        short_term_storage_directory=tmpdir,
        maximum_storage_duration=TEST_SLEEP_DURATION / 10,
    )
    manager = ShortTermStorageManager(config=config)
    short_term_storage_target = manager.new_target(
        TEST_FILENAME,
        TEST_MIME_TYPE,
    )
    short_term_storage_target.path.touch()
    assert short_term_storage_target.path.exists()
    serve_info = manager.get_serve_info(short_term_storage_target)
    assert serve_info
    time.sleep(TEST_SLEEP_DURATION)
    manager.cleanup()
    assert not short_term_storage_target.path.exists()
    with pytest.raises(ObjectNotFound):
        manager.get_serve_info(short_term_storage_target)
