from galaxy.objectstore import (
    BaseUserObjectStoreResolver,
    build_object_store_from_config,
    DistributedObjectStore,
    serialize_static_object_store_config,
)
from galaxy.objectstore.templates.models import (
    DiskObjectStoreConfiguration,
    ObjectStoreConfiguration,
)
from galaxy.objectstore.unittest_utils import (
    app_config,
    Config,
)
from .test_objectstore import MockDataset

DISTRIBUTED_TEST_CONFIG_YAML = """
type: distributed
backends:
   - id: files1
     type: disk
     weight: 1
     files_dir: "${temp_directory}/files1"
     extra_dirs:
     - type: temp
       path: "${temp_directory}/tmp1"
     - type: job_work
       path: "${temp_directory}/job_working_directory1"
"""
TEST_URI = "user_objects://1"


class MockUserObjectStoreResolver(BaseUserObjectStoreResolver):
    def __init__(self, tmpdir):
        test_dir = tmpdir / "files"
        test_dir.mkdir()
        self.test_dir = test_dir
        self._app_config = app_config(tmpdir)

    def resolve_object_store_uri_config(self, uri: str) -> ObjectStoreConfiguration:
        assert uri == TEST_URI
        files_dir = self.test_dir / "moo"
        files_dir.mkdir(exist_ok=True)
        configuration = DiskObjectStoreConfiguration(
            type="disk",
            files_dir=str(files_dir),
        )
        return configuration


def test_serialize_and_repopulate(tmp_path):
    resolver = MockUserObjectStoreResolver(tmp_path.resolve())
    with Config(DISTRIBUTED_TEST_CONFIG_YAML, user_object_store_resolver=resolver) as (directory, object_store):
        dataset = MockDataset(id=1)
        dataset.object_store_id = TEST_URI
        object_store.create(dataset)
        assert object_store.exists(dataset)

        object_store_uris = {TEST_URI}
        as_dict = serialize_static_object_store_config(object_store, object_store_uris)
        rehydrated_object_store = build_object_store_from_config(None, config_dict=as_dict)

        assert isinstance(rehydrated_object_store, DistributedObjectStore)
        assert TEST_URI in rehydrated_object_store.backends

        assert rehydrated_object_store.exists(dataset)
