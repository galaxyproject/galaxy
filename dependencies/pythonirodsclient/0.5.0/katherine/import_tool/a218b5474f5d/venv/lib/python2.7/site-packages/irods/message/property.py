from base64 import b64encode, b64decode

from irods.message.ordered import OrderedProperty, OrderedMetaclass, OrderedClass


class MessageProperty(OrderedProperty):

    def __get__(self, obj, cls):
        return obj._values[self.name]

    def __set__(self, obj, value):
        obj._values[self.name] = value

    def dub(self, name):
        self.name = name
        return self

    def pack(self, value):
        values = []
        values.append("<%s>" % self.name)
        values.append(self.format(value))
        values.append("</%s>" % self.name)
        return "".join(values)

    def unpack(self, els):
        if len(els):
            el = els[0]
            return self.parse(el.text)
        return None


class IntegerProperty(MessageProperty):

    def format(self, value):
        return str(value)

    def parse(self, value):
        return int(value)


class LongProperty(MessageProperty):

    def format(self, value):
        return str(value)

    def parse(self, value):
        return int(value)


class BinaryProperty(MessageProperty):

    def __init__(self, length):
        self.length = length
        super(BinaryProperty, self).__init__()

    def format(self, value):
        return b64encode(value)

    def parse(self, value):
        return b64decode(value)


class StringProperty(MessageProperty):

    def __init__(self, length=None):
        self.length = length
        super(StringProperty, self).__init__()

    def format(self, value):
        if isinstance(value, unicode):
            return value.encode('utf-8')
        return value

    def parse(self, value):
        if isinstance(value, str):
            return value.decode('utf-8')
        return value


class ArrayProperty(MessageProperty):

    def __init__(self, property):
        self.property = property
        super(ArrayProperty, self).__init__()

    def pack(self, values):
        self.property.dub(self.name)
        return "".join([self.property.pack(v) for v in values])

    def unpack(self, els):
        return [self.property.unpack([el]) for el in els]


class SubmessageProperty(MessageProperty):

    def __init__(self, message_cls):
        self.message_cls = message_cls
        super(SubmessageProperty, self).__init__()

    def pack(self, value):
        return value.pack()

    def unpack(self, els):
        if len(els):
            el = els[0]
            msg = self.message_cls()
            msg.unpack(el)
            return msg
        return None
