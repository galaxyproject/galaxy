import json
import os
from typing import (
    Any,
    Dict,
    Optional,
    Type,
    TypeVar,
)

from pydantic import BaseModel

from galaxy.util.hash_util import md5_hash_str

RAW_CACHED_JSON = Dict[str, Any]


def hash_model(model_class: Type[BaseModel]) -> str:
    return md5_hash_str(json.dumps(model_class.model_json_schema()))


MODEL_HASHES: Dict[Type[BaseModel], str] = {}


M = TypeVar("M", bound=BaseModel)


def ensure_model_has_hash(model_class: Type[BaseModel]) -> None:
    if model_class not in MODEL_HASHES:
        MODEL_HASHES[model_class] = hash_model(model_class)


class ModelCache:
    _cache_directory: str

    def __init__(self, cache_directory: str):
        if not os.path.exists(cache_directory):
            os.makedirs(cache_directory)
        self._cache_directory = cache_directory

    def _cache_target(self, model_class: Type[M], tool_id: str, tool_version: str) -> str:
        ensure_model_has_hash(model_class)
        # consider breaking this into multiple directories...
        cache_target = os.path.join(self._cache_directory, MODEL_HASHES[model_class], tool_id, tool_version)
        return cache_target

    def get_cache_entry_for(self, model_class: Type[M], tool_id: str, tool_version: str) -> Optional[M]:
        cache_target = self._cache_target(model_class, tool_id, tool_version)
        if not os.path.exists(cache_target):
            return None
        with open(cache_target) as f:
            return model_class.model_validate(json.load(f))

    def has_cached_entry_for(self, model_class: Type[M], tool_id: str, tool_version: str) -> bool:
        cache_target = self._cache_target(model_class, tool_id, tool_version)
        return os.path.exists(cache_target)

    def insert_cache_entry_for(self, model_object: M, tool_id: str, tool_version: str) -> None:
        cache_target = self._cache_target(model_object.__class__, tool_id, tool_version)
        parent_directory = os.path.dirname(cache_target)
        if not os.path.exists(parent_directory):
            os.makedirs(parent_directory)
        with open(cache_target, "w") as f:
            json.dump(model_object.dict(), f)
