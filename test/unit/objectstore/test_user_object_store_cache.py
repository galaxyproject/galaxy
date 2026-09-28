from galaxy.objectstore import (
    BaseUserObjectStoreResolver,
    DiskObjectStore,
    UserObjectStoreCache,
)
from galaxy.objectstore.templates.models import (
    DiskObjectStoreConfiguration,
    ObjectStoreConfiguration,
)
from galaxy.objectstore.unittest_utils import (
    app_config,
    Config,
    MockConfig,
)
from .test_objectstore import MockDataset
from .test_serializing_user_object_stores import (
    DISTRIBUTED_TEST_CONFIG_YAML,
    TEST_URI,
)


class RecordingDiskObjectStore(DiskObjectStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shutdowns = 0
        self.soft_shutdowns = 0

    def shutdown(self):
        self.shutdowns += 1
        super().shutdown()

    def soft_shutdown(self):
        self.soft_shutdowns += 1


class ChangingUserObjectStoreResolver(BaseUserObjectStoreResolver):
    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        self.version = 1
        self._app_config = app_config(tmpdir)
        self.built: list[RecordingDiskObjectStore] = []
        self.during_next_build = None

    def resolve_object_store_uri_config(self, uri: str) -> ObjectStoreConfiguration:
        files_dir = self.tmpdir / f"{uri.split('://', 1)[1]}-v{self.version}"
        files_dir.mkdir(exist_ok=True)
        return DiskObjectStoreConfiguration(type="disk", files_dir=str(files_dir))

    def object_store_from_config(self, object_store_configuration: ObjectStoreConfiguration):
        store = RecordingDiskObjectStore(
            MockConfig(str(self.tmpdir), "unused.yml", store_by="uuid"), object_store_configuration.model_dump()
        )
        self.built.append(store)
        if self.during_next_build:
            during_build, self.during_next_build = self.during_next_build, None
            during_build()
        return store


def test_user_object_store_constructed_once_for_repeated_calls(tmp_path):
    resolver = ChangingUserObjectStoreResolver(tmp_path.resolve())
    with Config(DISTRIBUTED_TEST_CONFIG_YAML, user_object_store_resolver=resolver) as (_, object_store):
        dataset = MockDataset(id=1)
        dataset.object_store_id = TEST_URI
        object_store.create(dataset)
        for _ in range(5):
            assert object_store.exists(dataset)
            object_store.size(dataset)
            object_store.get_filename(dataset)
            object_store.is_private(dataset)
        assert len(resolver.built) == 1


def test_user_object_store_rebuilt_when_configuration_changes(tmp_path):
    resolver = ChangingUserObjectStoreResolver(tmp_path.resolve())
    with Config(DISTRIBUTED_TEST_CONFIG_YAML, user_object_store_resolver=resolver) as (_, object_store):
        dataset = MockDataset(id=1)
        dataset.object_store_id = TEST_URI
        object_store.create(dataset)
        first_store = object_store._resolve_backend(TEST_URI)

        resolver.version = 2
        second_store = object_store._resolve_backend(TEST_URI)
        assert second_store is not first_store
        assert (first_store.soft_shutdowns, first_store.shutdowns) == (1, 0)
        assert not object_store.exists(dataset)
        assert object_store._resolve_backend(TEST_URI) is second_store

        object_store.shutdown()
        assert (second_store.soft_shutdowns, second_store.shutdowns) == (0, 1)


def test_user_object_store_cache_evicts_least_recently_used(tmp_path):
    resolver = ChangingUserObjectStoreResolver(tmp_path.resolve())
    cache = UserObjectStoreCache(resolver, maxsize=2)
    cache.get("user_objects://a")
    cache.get("user_objects://b")
    store_a, store_b = resolver.built
    cache.get("user_objects://a")
    cache.get("user_objects://c")
    assert store_b.soft_shutdowns == 1
    assert store_a.soft_shutdowns == 0
    assert cache.get("user_objects://a") is store_a


def test_concurrently_built_duplicate_is_discarded(tmp_path):
    resolver = ChangingUserObjectStoreResolver(tmp_path.resolve())
    cache = UserObjectStoreCache(resolver)
    resolver.during_next_build = lambda: cache.get(TEST_URI)
    store = cache.get(TEST_URI)
    duplicate, winner = resolver.built
    assert store is winner
    assert (duplicate.soft_shutdowns, duplicate.shutdowns) == (0, 1)
    assert (winner.soft_shutdowns, winner.shutdowns) == (0, 0)
    assert cache.get(TEST_URI) is winner
