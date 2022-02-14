"""Web Application Stack worker messaging."""

import json
import logging
import types
from typing import (
    Optional,
    Tuple,
)

log = logging.getLogger(__name__)


class ApplicationStackMessageDispatcher:
    def __init__(self):
        self.__funcs = {}

    def __func_name(self, func, name):
        if not name:
            name = func.__name__
        return name

    def register_func(self, func, name=None):
        name = self.__func_name(func, name)
        self.__funcs[name] = func

    def deregister_func(self, func=None, name=None):
        name = self.__func_name(func, name)
        try:
            del self.__funcs[name]
        except KeyError:
            pass

    @property
    def handler_count(self):
        return len(self.__funcs)

    def dispatch(self, msg_str):
        msg = decode(msg_str)
        try:
            msg.validate()
        except AssertionError as exc:
            log.error("Invalid message received: %s, error: %s", msg_str, exc)
            return
        if msg.target not in self.__funcs:
            log.error(
                "Received message with target '%s' but no functions were registered with that name. Params were: %s",
                msg.target,
                msg.params,
            )
        else:
            self.__funcs[msg.target](msg)


class ApplicationStackMessage(dict):
    default_handler = None
    _validate_kwargs = ("target",)

    def __init__(self, target=None, **kwargs):
        self["target"] = target
        self._merge_class_tuples()

    def _merge_class_tuples(self):
        """Locates any class-level tuples beginning with a single (but not double) underscore in the MRO and creates a
        property on the instance with the same name (without the leading underscore) that will return the union of
        those tuples.
        """
        names = set()
        for cls in reversed(self.__class__.mro()):
            names.update(
                [x for x in dir(cls) if x.startswith("_") and not x.startswith("__") and type(getattr(cls, x)) == tuple]
            )
        for name in names:
            setattr(self.__class__, name.lstrip("_"), property(lambda self, name=name: self._get_list_from_mro(name)))

    def _get_list_from_mro(self, name):
        """Locate all class-level tuples with the given `name` in the MRO and return their union."""
        r = set()
        for cls in reversed(self.__class__.mro()):
            r.update(getattr(cls, name, []))
        return r

    def _validate_items(self, obj, items, name):
        for item in items:
            assert item in obj, f"Missing '{item}' message {name}"

    def validate(self):
        self._validate_items(self, self.validate_kwargs, "argument")

    def encode(self):
        self["__classname__"] = self.__class__.__name__
        return json.dumps(self)

    def bind_default_handler(self, obj, name):
        """Bind the default handler method to `obj` as attribute `name`.

        This could also be implemented as a mixin class.
        """
        assert self.default_handler is not None, f"{self.__class__.__name__} has no default handler method, cannot bind"
        setattr(obj, name, types.MethodType(self.default_handler, obj))
        log.debug(
            "Bound default message handler '%s.%s' to %s",
            self.__class__.__name__,
            self.default_handler.__name__,
            getattr(obj, name),
        )

    @property
    def target(self) -> Optional[str]:
        return self["target"]

    @target.setter  # type: ignore[attr-defined]
    def set_target(self, target):
        self["target"] = target


class ParamMessage(ApplicationStackMessage):
    _validate_kwargs = ("params",)
    _validate_params: Tuple[str, ...] = ()
    _exclude_params: Tuple[str, ...] = ()

    def __init__(self, target=None, params=None, **kwargs):
        super().__init__(target=target)
        self["params"] = params or {}
        for k, v in kwargs.items():
            self["params"][k] = v

    def validate(self):
        super().validate()
        self._validate_items(self["params"], self.validate_params, "parameters")

    @property
    def params(self):
        d = self["params"].copy()
        for key in self.exclude_params:
            d.pop(key, None)
        return d

    @params.setter
    def params(self, params):
        self["params"] = params


class TaskMessage(ParamMessage):
    _validate_params = ("task",)
    _exclude_params = ("task",)

    @staticmethod
    def default_handler(self, msg):
        """Can be bound to an instance of any class that has message handling methods named like `_handle_{task}_method`"""
        name = f"_handle_{msg.task}_msg"
        assert name in dir(self), "{cls} has no method _handle_{task}_msg, cannot handle message: {msg}".format(
            cls=self.__class__.__name__, task=msg.task, msg=msg
        )
        getattr(self, f"_handle_{msg.task}_msg")(**msg.params)

    @property
    def task(self):
        return self["params"]["task"]


class JobHandlerMessage(TaskMessage):
    target = "job_handler"
    _validate_params = ("job_id",)


class WorkflowSchedulingMessage(TaskMessage):
    target = "workflow_scheduling"
    _validate_params = ("workflow_invocation_id",)


def decode(msg_str):
    d = json.loads(msg_str)
    cls = d.pop("__classname__")
    return globals()[cls](**d)
