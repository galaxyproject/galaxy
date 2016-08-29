# http://askawizard.blogspot.com/2008/10/ordered-properties-python-saga-part-5.html
from struct import unpack, pack
import xml.etree.ElementTree as ET

from irods.message.ordered import OrderedProperty, OrderedMetaclass, OrderedClass


class MessageMetaclass(OrderedMetaclass):

    def __init__(self, name, bases, attys):
        super(MessageMetaclass, self).__init__(name, bases, attys)
        for name, property in self._ordered_properties:
            property.dub(name)


class Message(OrderedClass):
    __metaclass__ = MessageMetaclass

    def __init__(self, *args, **kwargs):
        super(Message, self).__init__()
        self._values = {}
        for (name, _) in self._ordered_properties:
            if name in kwargs:
                self._values[name] = kwargs[name]

    def pack(self):
        values = []
        values.append("<%s>" % self.__class__._name)
        for (name, property) in self._ordered_properties:
            if name in self._values:
                values.append(property.pack(self._values[name]))
        values.append("</%s>" % self.__class__._name)
        return "".join(values)

    def unpack(self, root):
        for (name, property) in self._ordered_properties:
            self._values[name] = property.unpack(root.findall(name))
