# Ordered property classes stolen from Kris Kowal of Ask a Wizard
# http://askawizard.blogspot.com/2008/10/ordered-properties-python-saga-part-5.html
from itertools import count
next_counter = count().next

class OrderedProperty(object):
    def __init__(self, *args, **kws):
        self._creation_counter = next_counter()
        super(OrderedProperty, self).__init__(*args, **kws)

class OrderedMetaclass(type):
    def __init__(self, name, bases, attys):
        super(OrderedMetaclass, self).__init__(name, bases, attys)
        self._creation_counter = next_counter()
        self._ordered_properties = sorted(
            (
                (name, value)
                for base in reversed(self.__mro__)
                for name, value in base.__dict__.items()
                if isinstance(value, OrderedProperty)
                or isinstance(value, OrderedMetaclass)
            ),
            key = lambda (name, property): property._creation_counter,
        )

class OrderedClass(object):
    __metaclass__ = OrderedMetaclass
