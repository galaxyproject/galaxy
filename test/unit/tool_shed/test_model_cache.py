import os

from pydantic import (
    BaseModel,
    ConfigDict,
)

from tool_shed.managers.model_cache import (
    hash_model,
    ModelCache,
)


class Moo(BaseModel):
    foo: int


class MooLike(BaseModel):
    model_config = ConfigDict(title="Moo")
    foo: int


class NewMoo(BaseModel):
    model_config = ConfigDict(title="Moo")
    foo: int
    new_prop: str


def test_hash():
    hash_moo_1 = hash_model(Moo)
    hash_moo_2 = hash_model(Moo)
    assert hash_moo_1 == hash_moo_2


def test_hash_by_value():
    hash_moo_1 = hash_model(Moo)
    hash_moo_like = hash_model(MooLike)
    assert hash_moo_1 == hash_moo_like


def test_hash_different_on_updates():
    hash_moo_1 = hash_model(Moo)
    hash_moo_new = hash_model(NewMoo)
    assert hash_moo_1 != hash_moo_new


def cache_dict(tmp_path):
    model_cache = ModelCache(tmp_path)
    assert not model_cache.has_cached_entry_for(Moo, "moo", "1.0")
    assert None is model_cache.get_cache_entry_for(Moo, "moo", "1.0")
    model_cache.insert_cache_entry_for(Moo(foo=4), "moo", "1.0")
    moo = model_cache.get_cache_entry_for(Moo, "moo", "1.0")
    assert moo
    assert moo.foo == 4
    assert model_cache.has_cached_entry_for(Moo, "moo", "1.0")


def _directory_created_after_exists_check(monkeypatch, directory):
    real_exists = os.path.exists
    monkeypatch.setattr(os.path, "exists", lambda path: False if path == directory else real_exists(path))


def test_cache_directory_created_concurrently(tmp_path, monkeypatch):
    cache_directory = str(tmp_path / "model_cache")
    os.makedirs(cache_directory)
    _directory_created_after_exists_check(monkeypatch, cache_directory)
    ModelCache(cache_directory)


def test_entry_directory_created_concurrently(tmp_path, monkeypatch):
    model_cache = ModelCache(str(tmp_path))
    entry_directory = os.path.dirname(model_cache._cache_target(Moo, "moo", "1.0"))
    os.makedirs(entry_directory)
    _directory_created_after_exists_check(monkeypatch, entry_directory)
    model_cache.insert_cache_entry_for(Moo(foo=4), "moo", "1.0")
    assert model_cache.get_cache_entry_for(Moo, "moo", "1.0") == Moo(foo=4)
