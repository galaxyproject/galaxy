"""SQLAlchemy models for Social Auth"""
import base64
import six
import json

try:
    import transaction
except ImportError:
    transaction = None

from sqlalchemy.types import PickleType, Text

class JSONPickler(object):
    """JSON pickler wrapper around json lib since SQLAlchemy invokes
    dumps with extra positional parameters"""

    @classmethod
    def dumps(cls, value, *args, **kwargs):
        """Dumps the python value into a JSON string"""
        return json.dumps(value)

    @classmethod
    def loads(cls, value):
        """Parses the JSON string and returns the corresponding python value"""
        return json.loads(value)


# JSON type field
class JSONType(PickleType):
    impl = Text

    def __init__(self, *args, **kwargs):
        kwargs['pickler'] = JSONPickler
        super(JSONType, self).__init__(*args, **kwargs)
