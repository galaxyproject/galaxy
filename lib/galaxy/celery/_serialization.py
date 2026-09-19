import json
from importlib import import_module
from uuid import UUID

from pydantic import BaseModel

SCHEMA_MODELS_PACKAGE_BASE = "galaxy.schema."


# https://stackoverflow.com/a/2020083
def fullname(o):
    klass = o.__class__
    module = klass.__module__
    if module == "builtins":
        return klass.__qualname__  # avoid outputs like 'builtins.str'
    return module + "." + klass.__qualname__


class SchemaEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return {
                "__type__": "__pydantic_object__",
                "__class__": fullname(obj),
                "__object__": obj.model_dump(mode="json"),
            }
        if isinstance(obj, UUID):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def schema_decoder(obj):
    if "__type__" in obj:
        if obj["__type__"] == "__pydantic_object__":
            clazz_str = obj["__class__"]
            assert (
                clazz_str.startswith(SCHEMA_MODELS_PACKAGE_BASE) and ".." not in clazz_str
            ), f"Invalid class str {clazz_str}"
            module_name, class_name = clazz_str.rsplit(".", 1)
            module = import_module(module_name)
            clazz = getattr(module, class_name)
            obj = clazz(**obj["__object__"])
            return obj

    return obj


# Encoder function
def schema_dumps(obj):
    return json.dumps(obj, cls=SchemaEncoder)


# Decoder function
def schema_loads(obj):
    return json.loads(obj, object_hook=schema_decoder)
