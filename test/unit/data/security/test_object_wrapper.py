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
    VALID_CHARACTERS,
    wrap_with_safe_string,
)


class Foo:
    pass


class Bar:
    pass


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


class TestSafeStringWrapper:

    def test_do_not_set_attrs_of_type_instancestate(self):
        wrapper = SafeStringWrapper(Foo())

        wrapper.foo = 42
        assert wrapper.foo == 42  # attr set normally

        state = sqlalchemy.inspect(model.Tag())  # any declaratively maped class will do
        assert type(state) == InstanceState

        wrapper.bad_foo = state
        with pytest.raises(AttributeError):
            wrapper.bad_foo  # attr of type sqlalchemy.orm.state.InstanceState not set
