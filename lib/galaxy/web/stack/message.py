"""Web Application Stack worker messaging
"""
from __future__ import absolute_import

import json
import logging


log = logging.getLogger(__name__)


class ApplicationStackMessageEncoder(json.JSONEncoder):
    def encode(self, o):
        if isinstance(o, AttributeDict):
            return o.serialize(self)
        return json.JSONEncoder.encode(self, o)


class ApplicationStackMessage(dict):
    def __init__(self, target=None, params=None, **kwargs):
        """Any extra kwargs override values in params
        """
        self['target'] = target
        self['params'] = params or {}
        for k, v in kwargs.items():
            self['params'][k] = v

    #@classmethod
    #def from_string(cls, s)
    #    #kwargs['object_hook'] = ApplicationStackMessage
    #    d = json.loads(s)
    #    return cls(json.loads(s, *args, **kwargs))

    def validate(self):
        assert self['target'] is not None, "Missing 'target' parameter"

    def serialize(self, encoder):
        #return json.JSONEncoder.encode(encoder, ApplicationStackMessage.clean(self))
        self.validate()
        return json.JSONEncoder.encode(encoder, self)

    def dumps(self, *args, **kwargs):
        #kwargs['cls'] = AttributeStackMessageEncoder
        return json.dumps(self, *args, **kwargs)

    def dump(self, fp, *args, **kwargs):
        #raise Exception("This isn't using the Encoder, what gives?")
        #kwargs['cls'] = AttributeStackMessageEncoder
        return json.dump(self, fp, *args, **kwargs)

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

    #property
    #def class(self):
    #    return globals()[self['cls']]

    def encode(self):
        self['__classname__'] = self.__class__.__name__
        return json.dumps(self)


# when we add additional messages this should become generalized and subclassed
class JobHandlerMessage(ApplicationStackMessage):
    target = 'job_handler'

    def __init__(self, target=None, params=None, **kwargs):
        super(JobHandlerMessage, self).__init__(params=params, **kwargs)
        self['target'] = self.target

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
