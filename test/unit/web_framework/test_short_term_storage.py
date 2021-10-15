import time

from galaxy.exceptions import MessageException
from galaxy.web.short_term_storage import (
    ShortTermStorageConfiguration,
    ShortTermStorageManager,
    ShortTermStorageServeCancelledInformation,
    ShortTermStorageServeCompletedInformation,
    ShortTermStorageTargetSecurity,
)

TEST_FILENAME = "moo.txt"
TEST_MIME_TYPE = "text/plain"


def test_typical_usage(tmpdir):
    config = ShortTermStorageConfiguration(
        short_term_storage_directory=tmpdir
    )
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


def test_cancel_with_exception(tmpdir):
    config = ShortTermStorageConfiguration(
        short_term_storage_directory=tmpdir
    )
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


def test_cleanup(tmpdir):
    config = ShortTermStorageConfiguration(
        short_term_storage_directory=tmpdir,
        maximum_storage_duration=1,
    )
    manager = ShortTermStorageManager(config=config)
    short_term_storage_target = manager.new_target(
        TEST_FILENAME,
        TEST_MIME_TYPE,
    )
    short_term_storage_target.path.touch()
    assert short_term_storage_target.path.exists()
    time.sleep(2)
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
    time.sleep(2)
    manager.cleanup()
    assert short_term_storage_target.path.exists()
