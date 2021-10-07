import math
from collections import UserDict
from numbers import Number
from types import (
    BuiltinFunctionType,
    BuiltinMethodType,
    CodeType,
    FrameType,
    FunctionType,
    GeneratorType,
    GetSetDescriptorType,
    MemberDescriptorType,
    MethodType,
    ModuleType,
    TracebackType,
)

import pytest
import sqlalchemy
from sqlalchemy.orm import InstanceState

from galaxy import model
from galaxy import util
from galaxy.security import object_wrapper
from galaxy.security.object_wrapper import (
    __DONT_SANITIZE_TYPES__,
    __WRAP_MAPPINGS__,
    __WRAP_NO_SUBCLASS__,
    __WRAP_SEQUENCES__,
    __WRAP_SETS__,
    CallableSafeStringWrapper,
    get_class_and_name_for_wrapping,
    get_no_wrap_classes,
    MAPPED_CHARACTERS,
    SafeStringWrapper,
    unwrap,
    VALID_CHARACTERS,
    wrap_with_safe_string,
)


@pytest.fixture(scope='module')
def default_no_wrap_types():
    return list(__DONT_SANITIZE_TYPES__) + [SafeStringWrapper]


def test_valid_characters():
    expected = util.VALID_CHARACTERS.copy()
    expected.add('@')
    assert VALID_CHARACTERS == expected


def test_mapped_characters():
    expected = util.MAPPED_CHARACTERS.copy()
    del expected['@']
    assert MAPPED_CHARACTERS == expected


def test_type_groups():
    """Verify const values."""
    # don't wrap or sanitize types
    assert __DONT_SANITIZE_TYPES__ == (
        Number, bool, type(None), type(NotImplemented), type(Ellipsis), bytearray)
    # wrap but don't subclass types
    assert __WRAP_NO_SUBCLASS__ == (
        ModuleType, range, slice, TracebackType, FrameType, GetSetDescriptorType, MemberDescriptorType,
        FunctionType, MethodType, GeneratorType, CodeType, BuiltinFunctionType, BuiltinMethodType)
    # wrap contents but not the containser: sequence types
    assert __WRAP_SEQUENCES__ == (tuple, list,)
    assert __WRAP_SETS__ == (set, frozenset,)
    # wrap contents but not the containser: mapping types
    assert __WRAP_MAPPINGS__ == (dict, UserDict,)


def test_do_not_wrap_safestringwrapper():
    """ Do not wrap SafeStringWrapper: only wrap one layer."""
    obj = SafeStringWrapper(None)
    result = wrap_with_safe_string(obj)
    assert result is obj


def test_do_not_wrap_no_wrap_classes():
    """ Do not wrap instances of classes passed in no_wrap_classes."""
    obj = Foo()
    result = wrap_with_safe_string(obj)
    # obj is wrapped
    assert result is not obj
    assert isinstance(result, SafeStringWrapper)

    result = wrap_with_safe_string(obj, no_wrap_classes=Foo)
    # obj is not wrapped because it is in no_wrap_classes
    assert result is obj

    result = wrap_with_safe_string(obj, no_wrap_classes=Bar)
    # obj is wrapped, because it is not in no_wrap_classes
    assert result is not obj
    assert isinstance(result, SafeStringWrapper)


def test_wrap_dont_subclass(monkeypatch):
    patched = __WRAP_NO_SUBCLASS__ + (Foo,)  # Add Foo to wrap-no-subclass types
    monkeypatch.setattr(object_wrapper, '__WRAP_NO_SUBCLASS__', patched)

    result = wrap_with_safe_string(Foo())
    # Foo is in __WRAP_NO_SUBCLASS__, so result is wrapped, but not subclass of Foo
    assert isinstance(result, SafeStringWrapper) and not isinstance(result, Foo)

    result = wrap_with_safe_string(Bar())
    # Bar is not in __WRAP_NO_SUBCLASS__, so result is wrapped, and is subclass of Bar
    assert isinstance(result, SafeStringWrapper) and isinstance(result, Bar)


def test_wrap_sequence():
    sequences = [Foo(), Bar(), (Foo(),), {Bar()}]  # Foo, Bar, tuple w/Foo, set w/Bar

    result = wrap_with_safe_string(sequences)
    assert isinstance(result, list)  # container was not wrapped
    assert len(result) == 4
    # items were recursively wrapped
    assert isinstance(result[0], SafeStringWrapper)
    assert isinstance(result[1], SafeStringWrapper)
    assert isinstance(result[2], tuple)  # container was not wrapped
    assert isinstance(result[2][0], SafeStringWrapper)
    assert isinstance(result[3], set)  # container was not wrapped
    assert isinstance(result[3].pop(), SafeStringWrapper)


def test_wrap_mapping():
    mapping = {Foo(): Bar()}

    result = wrap_with_safe_string(mapping)
    assert isinstance(result, dict)  # container was not wrapped
    assert len(result) == 1
    key, value = result.popitem()
    assert isinstance(key, SafeStringWrapper)  # key was wrapped
    assert isinstance(value, SafeStringWrapper)  # value was wrapped


def test_safe_class():

    class IAmCallable:
        def __call__(self):  # this makes it a Callable
            pass

    # An instance of IAmCallable is a Callable, so expect CallableSafeStringWrapper
    result = wrap_with_safe_string(IAmCallable())
    assert isinstance(result, CallableSafeStringWrapper)

    # An instance of Foo is not in __CALLABLE_TYPES__, so it's just SafeStringWrapper
    result = wrap_with_safe_string(Foo())
    assert isinstance(result, SafeStringWrapper) and not isinstance(result, CallableSafeStringWrapper)


class TestGetNoWrapClasses:
    """Test get_no_wrap_classes() with different arguments."""

    def test_default_no_wrap_classes(self, default_no_wrap_types):
        """ If no arg supplied, use default."""
        expected = default_no_wrap_types
        classes = get_no_wrap_classes()
        assert set(classes) == set(expected)

    def test_no_wrap_classes_one_arg(self, default_no_wrap_types):
        """ One class passed."""
        expected = default_no_wrap_types + [Foo]
        classes = get_no_wrap_classes(no_wrap_classes=Foo)
        assert set(classes) == set(expected)

    def test_no_wrap_classes_multiple_arg_as_list(self, default_no_wrap_types):
        """ Multiple classses passed as a list."""
        expected = default_no_wrap_types + [Foo, Bar]
        classes = get_no_wrap_classes(no_wrap_classes=[Foo, Bar])
        assert set(classes) == set(expected)

    def test_no_wrap_classes_multiple_arg_as_tuple(self, default_no_wrap_types):
        """ Multiple classses passed as a tuple."""
        expected = default_no_wrap_types + [Foo, Bar]
        classes = get_no_wrap_classes(no_wrap_classes=(Foo, Bar))
        assert set(classes) == set(expected)


def test_wrapped_class_name():
    obj = Foo()
    # If this module is renamed, edit its name ('test_object_wrapper') in the expected string
    expected = 'SafeStringWrapper(test_object_wrapper.Foo)'
    class_, class_name = get_class_and_name_for_wrapping(obj, SafeStringWrapper)
    assert class_ is Foo
    assert class_name == expected


def test_wrapper_class_is_reused():
    foo1 = Foo()
    foo2 = Foo()
    bar1 = Bar()
    result1 = wrap_with_safe_string(foo1)
    result2 = wrap_with_safe_string(foo2)
    result3 = wrap_with_safe_string(bar1)
    assert result1.__class__ is result2.__class__  # both are wrappers for instances of the same class: reused
    assert result1.__class__ is not result3.__class__  # wrappers for instances of different classes: not reused


def test_unwrap():
    foo, bar = Foo(), Bar()
    foo.b = bar
    wrapped_foo = wrap_with_safe_string(foo)

    assert foo is not wrapped_foo
    assert bar is not wrapped_foo.b
    assert foo is unwrap(wrapped_foo)
    assert bar is unwrap(wrapped_foo.b)


class TestSafeStringWrapper:

    def test_constants(self):
        assert SafeStringWrapper.__NO_WRAP_NAMES__ == [
            '__safe_string_wrapper_function__', '__class__', 'unsanitized']

    def test_do_not_set_attrs_of_type_instancestate(self):
        wrapper = SafeStringWrapper(Foo())

        wrapper.foo = 42
        assert wrapper.foo == 42  # attr set normally

        state = sqlalchemy.inspect(model.Tag())  # any declaratively maped class will do
        assert type(state) == InstanceState

        wrapper.bad_foo = state
        with pytest.raises(AttributeError):
            wrapper.bad_foo  # attr of type sqlalchemy.orm.state.InstanceState not set

    def test__str__and__repr___(self):
        foo = 'a<\va'  # valid char + mapped char + illegal char + valid char
        wrapped_foo = wrap_with_safe_string(foo)
        assert str(wrapped_foo) == 'a__lt__Xa'  # sanitized str(foo)
        assert repr(wrapped_foo).startswith('SafeStringWrapper(str) object at')
        assert repr(wrapped_foo).endswith('on: __sq__a__lt__Xx0ba__sq__')  # sanitized repr(foo)

    def test__lt__(self):
        foo, bar = 'a', 'b'
        wrapped_foo = wrap_with_safe_string(foo)
        wrapped_bar = wrap_with_safe_string(bar)
        assert foo < bar and wrapped_foo < wrapped_bar

    def test__le__(self):
        foo, bar = 'a', 'b'
        wrapped_foo = wrap_with_safe_string(foo)
        wrapped_bar = wrap_with_safe_string(bar)
        assert foo <= bar and wrapped_foo <= wrapped_bar

        foo, bar = 'a', 'a'
        wrapped_foo = wrap_with_safe_string(foo)
        wrapped_bar = wrap_with_safe_string(bar)
        assert foo <= bar and wrapped_foo <= wrapped_bar

    def test__eq__(self):
        foo, bar = 'a', 'a'
        wrapped_foo = wrap_with_safe_string(foo)
        wrapped_bar = wrap_with_safe_string(bar)
        assert foo == bar and wrapped_foo == wrapped_bar

    def test__ne__(self):
        foo, bar = 'a', 'b'
        wrapped_foo = wrap_with_safe_string(foo)
        wrapped_bar = wrap_with_safe_string(bar)
        assert foo != bar and wrapped_foo != wrapped_bar

    def test__gt__(self):
        foo, bar = 'b', 'a'
        wrapped_foo = wrap_with_safe_string(foo)
        wrapped_bar = wrap_with_safe_string(bar)
        assert foo > bar and wrapped_foo > wrapped_bar

    def test__ge__(self):
        foo, bar = 'b', 'a'
        wrapped_foo = wrap_with_safe_string(foo)
        wrapped_bar = wrap_with_safe_string(bar)
        assert foo >= bar and wrapped_foo >= wrapped_bar

        foo, bar = 'a', 'a'
        wrapped_foo = wrap_with_safe_string(foo)
        wrapped_bar = wrap_with_safe_string(bar)
        assert foo >= bar and wrapped_foo >= wrapped_bar

    def test__hash__(self):
        foo = 'a'
        wrapped_foo = wrap_with_safe_string(foo)
        assert hash(foo) == hash(wrapped_foo)

    def test__bool__(self):
        foo = 'a'
        wrapped_foo = wrap_with_safe_string(foo)
        assert bool(foo) == bool(wrapped_foo)

    def test__len__(self):
        foo = 'abc'
        wrapped_foo = wrap_with_safe_string(foo)
        assert len(foo) == len(wrapped_foo)


class TestNumericTypesMethods:
    # See https://docs.python.org/3/reference/datamodel.html?highlight=__xor__#emulating-numeric-types
    # Not covered:
    #   __matmul__ (not implemented)
    #   in-place methods (return is None, so they are irrelevant for wrapping)

    def test_numeric_method_return_values_are_correct(self):
        # Test ensures that when we overwrite a numeric method, we don't screw up its core function.
        # For each method, we compare 3 expressions where the method under test is called on
        # (1) IntWrapper, (2) IntWRapper wrapped w/SafeStringWrapper, (3) literal value.
        # Thus, we verify both the correctness of the overridden method in SafeStringWrapper,
        # as well as the method in IntWrapper that simply delegates the call to the wrapped value.
        # (See comment in IntWrapper definition.)
        m, n = 2, 3
        foo = IntWrapper(m)
        wrapped_foo = wrap_with_safe_string(foo)

        # Binary arithmetic operations
        assert foo + n == wrapped_foo + n == m + n
        assert foo - n == wrapped_foo - n == m - n
        assert foo * n == wrapped_foo * n == m * n
        assert foo / n == wrapped_foo / n == m / n
        assert foo // n == wrapped_foo // n == m // n
        assert foo % n == wrapped_foo % n == m % n
        assert divmod(foo, n) == divmod(wrapped_foo, n) == divmod(m, n)
        assert foo ** n == wrapped_foo ** n == m ** n
        assert foo << n == wrapped_foo << n == m << n
        assert foo >> n == wrapped_foo >> n == m >> n
        assert foo & n == wrapped_foo & n == n & m

        # Binary arithmetic operations with reflected (swapped) operands
        assert n + foo == n + wrapped_foo == n + m
        assert n - foo == n - wrapped_foo == n - m
        assert n * foo == n * wrapped_foo == n * m
        assert n / foo == n / wrapped_foo == n / m
        assert n // foo == n // wrapped_foo == n // m
        assert n % foo == n % wrapped_foo == n % m
        assert divmod(n, foo) == divmod(n, wrapped_foo) == divmod(n, m)
        assert n ** foo == n ** wrapped_foo == n ** m
        assert n << foo == n << wrapped_foo == n << m
        assert n >> foo == n >> wrapped_foo == n >> m
        assert n & foo == n & wrapped_foo == n & m
        assert n ^ foo == n ^ wrapped_foo == n ^ m
        assert n | foo == n | wrapped_foo == n | m

        # Unary arithmetic operations
        assert -foo == -wrapped_foo == -m
        assert +foo == +wrapped_foo == +m
        assert abs(foo) == abs(wrapped_foo) == abs(m)
        assert ~foo == ~wrapped_foo == ~m

        # Misc.
        assert complex(foo) == complex(wrapped_foo) == complex(m)
        assert int(foo) == int(wrapped_foo) == int(m)
        assert float(foo) == float(wrapped_foo) == float(m)
        assert foo.__index__() == wrapped_foo.__index__() == m.__index__()
        assert round(foo) == round(wrapped_foo) == round(m)
        assert math.trunc(foo) == math.trunc(wrapped_foo) == math.trunc(m)
        assert math.floor(foo) == math.floor(wrapped_foo) == math.floor(m)
        assert math.ceil(foo) == math.ceil(wrapped_foo) == math.ceil(m)

    def test_numeric_method_return_values_are_sanitized(self):
        # Test verifies that return values from numeric methods are wrapped.
        foo = IllegalReturnValueSimulator()
        wrapped_foo = wrap_with_safe_string(foo)

        # Binary arithmetic operations

        # __add__
        assert not is_sanitized(foo + 1)
        assert is_sanitized(wrapped_foo + 1)

        # __sub__
        assert not is_sanitized(foo - 1)
        assert is_sanitized(wrapped_foo - 1)

        # __mul__
        assert not is_sanitized(foo * 1)
        assert is_sanitized(wrapped_foo * 1)

        # __truediv__
        assert not is_sanitized(foo / 1)
        assert is_sanitized(wrapped_foo / 1)

        # __floordiv__
        assert not is_sanitized(foo // 1)
        assert is_sanitized(wrapped_foo // 1)

        # __mod__
        assert not is_sanitized(foo % 1)
        assert is_sanitized(wrapped_foo % 1)

        # __divmod__
        assert not is_sanitized(divmod(foo, 1))
        assert is_sanitized(divmod(wrapped_foo, 1))

        # __pow__
        assert not is_sanitized(foo ** 1)
        assert is_sanitized(wrapped_foo ** 1)

        # __lshift__
        assert not is_sanitized(foo << 1)
        assert is_sanitized(wrapped_foo << 1)

        # __rshift__
        assert not is_sanitized(foo >> 1)
        assert is_sanitized(wrapped_foo >> 1)

        # __and__
        assert not is_sanitized(foo & 1)
        assert is_sanitized(wrapped_foo & 1)

        # __xor__
        assert not is_sanitized(foo ^ 1)
        assert is_sanitized(wrapped_foo ^ 1)

        # __or__
        assert not is_sanitized(foo | 1)
        assert is_sanitized(wrapped_foo | 1)

        # Binary arithmetic operations with reflected (swapped) operands

        # __radd__
        assert not is_sanitized(1 + foo)
        assert is_sanitized(1 + wrapped_foo)

        # __rsub__
        assert not is_sanitized(1 - foo)
        assert is_sanitized(1 - wrapped_foo)

        # __rmul__
        assert not is_sanitized(1 * foo)
        assert is_sanitized(1 * wrapped_foo)

        # __rtruediv__
        assert not is_sanitized(1 / foo)
        assert is_sanitized(1 / wrapped_foo)

        # __rfloordiv__
        assert not is_sanitized(1 // foo)
        assert is_sanitized(1 // wrapped_foo)

        # __rmod__
        assert not is_sanitized(1 % foo)
        assert is_sanitized(1 % wrapped_foo)

        # __rdivmod__
        assert not is_sanitized(divmod(1, foo))
        assert is_sanitized(divmod(1, wrapped_foo))

        # __rpow__
        assert not is_sanitized(1 ** foo)
        assert is_sanitized(1 ** wrapped_foo)

        # __rlshift__
        assert not is_sanitized(1 << foo)
        assert is_sanitized(1 << wrapped_foo)

        # __rrshift__
        assert not is_sanitized(1 >> foo)
        assert is_sanitized(1 >> wrapped_foo)

        # __rand__
        assert not is_sanitized(1 & foo)
        assert is_sanitized(1 & wrapped_foo)

        # __rxor__
        assert not is_sanitized(1 ^ foo)
        assert is_sanitized(1 ^ wrapped_foo)

        # __ror__
        assert not is_sanitized(1 | foo)
        assert is_sanitized(1 | wrapped_foo)

        # Unary arithmetic operations

        # __neg__
        assert not is_sanitized(-foo)
        assert is_sanitized(-wrapped_foo)

        # __pos__
        assert not is_sanitized(+foo)
        assert is_sanitized(+wrapped_foo)

        # __abs__
        assert not is_sanitized(abs(foo))
        assert is_sanitized(abs(wrapped_foo))

        # __invert__
        assert not is_sanitized(~foo)
        assert is_sanitized(~wrapped_foo)

        # Misc.
        # The following 8 tests DO verify that an invalid return value
        # produced by these methods DOES get sanitized when wrapped in a
        # SafeStringWrapper. However, these tests do NOT call the corresponding
        # methods in SafeStringWrapper (which happens due to overwritten
        # attribute access). Those methods are verified by the previous test,
        # but only for correctness of returned values. The problem is that if
        # we delete these methods from SafeStringWrapper, all tests will still
        # pass (implementations on the base classes will be called, and return
        # values will be sanitized. Thus, none of these tests verify that
        # overriding these 8 methods is needed.
        # TODO: Find a use case justifying these methods and add tests.

        # __complex__
        assert not is_sanitized(foo.__complex__())
        assert is_sanitized(wrapped_foo.__complex__())

        # __int__
        assert not is_sanitized(foo.__int__())
        assert is_sanitized(wrapped_foo.__int__())

        # __float__
        assert not is_sanitized(foo.__float__())
        assert is_sanitized(wrapped_foo.__float__())

        # __index__
        assert not is_sanitized(foo.__index__())
        assert is_sanitized(wrapped_foo.__index__())

        # __round__
        assert not is_sanitized(foo.__round__())
        assert is_sanitized(wrapped_foo.__round__())

        # __trunc__
        assert not is_sanitized(foo.__trunc__())
        assert is_sanitized(wrapped_foo.__trunc__())

        # __floor__
        assert not is_sanitized(foo.__floor__())
        assert is_sanitized(wrapped_foo.__floor__())

        # __ceil__
        assert not is_sanitized(foo.__ceil__())
        assert is_sanitized(wrapped_foo.__ceil__())


class Foo:
    pass


class Bar:
    pass


class IntWrapper:
    # Wraps an integer value. This class is needed to test special methods that require an
    # integer or numeric value: a literal numeric value would not be wrapped by SafeStringWrapper.
    # NOTE: __add__ can use string values which would be wrapped; it's included here for consistency.
    def __init__(self, number):
        self.number = number

    # Binary arithmetic operations

    def __add__(self, other):
        return self.number + other

    def __sub__(self, other):
        return self.number - other

    def __mul__(self, other):
        return self.number * other

    def __truediv__(self, other):
        return self.number / other

    def __floordiv__(self, other):
        return self.number // other

    def __mod__(self, other):
        return self.number % other

    def __divmod__(self, other):
        return divmod(self.number, other)

    def __pow__(self, *other):
        return pow(self.number, *other)

    def __lshift__(self, other):
        return self.number << other

    def __rshift__(self, other):
        return self.number >> other

    def __and__(self, other):
        return self.number.__and__(other)

    def __xor__(self, other):
        return self.number.__xor__(other)

    def __or__(self, other):
        return self.number.__or__(other)

    # Binary arithmetic operations with reflected (swapped) operands

    def __radd__(self, other):
        return other + self.number

    def __rsub__(self, other):
        return other - self.number

    def __rmul__(self, other):
        return other * self.number

    def __rtruediv__(self, other):
        return other / self.number

    def __rfloordiv__(self, other):
        return other // self.number

    def __rmod__(self, other):
        return other % self.number

    def __rdivmod__(self, other):
        return divmod(other, self.number)

    def __rpow__(self, other):
        # As per python docs: "ternary pow() will not try calling __rpow__()
        # (the coercion rules would become too complicated)."
        return other ** self.number

    def __rlshift__(self, other):
        return other << self.number

    def __rrshift__(self, other):
        return other >> self.number

    def __rand__(self, other):
        return other & self.number

    def __rxor__(self, other):
        return other ^ self.number

    def __ror__(self, other):
        return other | self.number

    # Unary arithmetic operations

    def __neg__(self):
        return -self.number

    def __pos__(self):
        return +self.number

    def __abs__(self):
        return abs(self.number)

    def __invert__(self):
        return ~self.number

    # Misc.

    def __complex__(self):
        return complex(self.number)

    def __int__(self):
        return int(self.number)

    def __float__(self):
        return float(self.number)

    def __index__(self):
        return self.number.__index__()

    def __round__(self):
        return round(self.number)

    def __trunc__(self):
        return math.trunc(self.number)

    def __floor__(self):
        return math.floor(self.number)

    def __ceil__(self):
        return math.ceil(self.number)


class IllegalReturnValueSimulator:
    # Wraps dunder methods. Returns the same string value regardless of method.
    # The value consists of a valid character, a character that requies escaping,
    # and an illegal character.

    # This is needed to test that the return value of a method is sanitized. By
    # forcing the return of a value that would require sanitizing, we can check
    # whether it was sanitized or not. Returning a real value (e.g. the sum of 2
    # operands for __add__) would bypass wrapping (because we don't wrap a
    # number), so it would be impossible to verify that the return value is
    # wrapped when needed.

    # The value used here ('a<\v'), when wrapped, becomes 'a__lt__x'.

    # Do NOT refactor/add indirection: methods must return a literal so that
    # attribute access methods are not called.

    # Binary arithmetic operations

    def __add__(self, other):
        return 'a<\v'

    def __sub__(self, other):
        return 'a<\v'

    def __mul__(self, other):
        return 'a<\v'

    def __truediv__(self, other):
        return 'a<\v'

    def __floordiv__(self, other):
        return 'a<\v'

    def __mod__(self, other):
        return 'a<\v'

    def __divmod__(self, other):
        return 'a<\v'

    def __pow__(self, *other):
        return 'a<\v'

    def __lshift__(self, other):
        return 'a<\v'

    def __rshift__(self, *other):
        return 'a<\v'

    def __and__(self, *other):
        return 'a<\v'

    def __xor__(self, *other):
        return 'a<\v'

    def __or__(self, *other):
        return 'a<\v'

    # Binary arithmetic operations with reflected (swapped) operands

    def __radd__(self, other):
        return 'a<\v'

    def __rsub__(self, other):
        return 'a<\v'

    def __rmul__(self, other):
        return 'a<\v'

    def __rtruediv__(self, other):
        return 'a<\v'

    def __rfloordiv__(self, other):
        return 'a<\v'

    def __rmod__(self, other):
        return 'a<\v'

    def __rdivmod__(self, other):
        return 'a<\v'

    def __rpow__(self, *other):
        return 'a<\v'

    def __rlshift__(self, other):
        return 'a<\v'

    def __rrshift__(self, *other):
        return 'a<\v'

    def __rand__(self, *other):
        return 'a<\v'

    def __rxor__(self, *other):
        return 'a<\v'

    def __ror__(self, *other):
        return 'a<\v'

    # Unary arithmetic operations

    def __neg__(self):
        return 'a<\v'

    def __pos__(self):
        return 'a<\v'

    def __abs__(self):
        return 'a<\v'

    def __invert__(self):
        return 'a<\v'

    # Misc.

    def __complex__(self):
        return 'a<\v'

    def __int__(self):
        return 'a<\v'

    def __float__(self):
        return 'a<\v'

    def __index__(self):
        return 'a<\v'

    def __round__(self):
        return 'a<\v'

    def __trunc__(self):
        return 'a<\v'

    def __floor__(self):
        return 'a<\v'

    def __ceil__(self):
        return 'a<\v'


def is_sanitized(value):
    """ Returns True if wrapping value doesn't change it."""
    wrapped = wrap_with_safe_string(value)
    # We must check type equality because __eq__ on wrapped value is overwritten.
    return type(value) == type(wrapped) and value == wrapped
