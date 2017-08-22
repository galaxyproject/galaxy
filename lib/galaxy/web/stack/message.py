"""Web Application Stack worker messaging
"""
from __future__ import absolute_import

import json
import logging


log = logging.getLogger(__name__)


class ApplicationStackMessageDispatcher(object):
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
        del self.__funcs[name]

    @property
    def handler_count(self):
        return len(self.__funcs)

    def dispatch(self, msg_str):
        msg = decode(msg_str)
        try:
            msg.validate()
        except AssertionError as exc:
            log.error('Invalid message received: %s, error: %s', msg_str, exc)
            return
        if msg.target not in self.__funcs:
            log.error("Received message with target '%s' but no functions were registered with that name. Params were: %s", msg.target, msg.params)
        else:
            self.__funcs[msg.target](msg)


class ApplicationStackMessage(dict):
    target = None

    def __init__(self, target=None, params=None, **kwargs):
        self['target'] = target or self.__class__.target
        self['params'] = params or {}
        for k, v in kwargs.items():
            self['params'][k] = v

    def validate(self):
        assert self['target'] is not None, "Missing 'target' parameter"

    @property
    def target(self):
        return self['target']

    @target.setter
    def set_target(self, target):
        self['target'] = target

    @property
    def params(self):
        return self['params']

    @params.setter
    def set_params(self, params):
        self['params'] = params

    def encode(self):
        self['__classname__'] = self.__class__.__name__
        return json.dumps(self)


# TODO: when additional messages are added we should refactor and improve validation and param/task separation (but not all msgs may use task)
class JobHandlerMessage(ApplicationStackMessage):
    target = 'job_handler'

    def validate(self):
        super(JobHandlerMessage, self).validate()
        for param in ('task', 'job_id'):
            assert param in self['params'], "Missing required parameter '%s'" % param

    @property
    def task(self):
        return self['params']['task']

    @property
    def params(self):
        d = self['params'].copy()
        del d['task']
        return d


def decode(msg_str):
    d = json.loads(msg_str)
    cls = d.pop('__classname__')
    return globals()[cls](**d)
