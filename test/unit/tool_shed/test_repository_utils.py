from tool_shed.util.repository_content_util import upload_tar
from tool_shed.webapp.model import (
    Repository,
    User,
)
from ._util import (
    repository_fixture,
    TEST_DATA_FILES,
    TestToolShedApp,
)


def test_create_repository(shed_app: TestToolShedApp, new_user: User):
    name = "testname"
    manager = shed_app.hgweb_config_manager
    entry = None
    entry_name = f"repos/{new_user.username}/{name}"
    try:
        entry = manager.get_entry(entry_name)
    except Exception:
        pass
    assert not entry
    repository_fixture(shed_app, new_user, name)
    entry = manager.get_entry(entry_name)
    assert entry


def test_upload_tar(shed_app: TestToolShedApp, new_repository: Repository):
    tar_resource = TEST_DATA_FILES.joinpath("convert_chars/convert_chars.tar")
    old_tip = new_repository.tip()
    upload_ok, _, _, alert, dirs_removed, files_removed = upload_tar(
        shed_app,
        "localhost",
        new_repository.user.username,
        new_repository,
        tar_resource,
        None,
        "Commit Message",
    )
    assert upload_ok
    assert alert == ""
    assert dirs_removed == 0
    assert files_removed == 0
    new_tip = new_repository.tip()
    assert old_tip != new_tip
    changesets = new_repository.get_changesets_for_setting_metadata(shed_app)
    assert len(changesets) == 1
    for change in changesets:
        ctx = new_repository.hg_repo[change]
        assert str(ctx) == new_tip
