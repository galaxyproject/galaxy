from numbers import Number

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import InstanceState

from galaxy import model
from galaxy import util
from galaxy.security.object_wrapper import (
    __DONT_SANITIZE_TYPES__,
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


def test_dont_sanitize_types():
    """Verify const values."""
    assert __DONT_SANITIZE_TYPES__ == (
        Number, bool, type(None), type(NotImplemented), type(Ellipsis), bytearray)


def test_do_not_set_attrs_of_type_instancestate():
    wrapper = SafeStringWrapper(Foo())

    wrapper.foo = 42
    assert wrapper.foo == 42  # attr set normally

    state = inspect(model.Tag())  # any declaratively maped class will do
    assert type(state) == InstanceState

    wrapper.bad_foo = state
    with pytest.raises(AttributeError):
        wrapper.bad_foo  # attr of type sqlalchemy.orm.state.InstanceState not set


def test_do_not_wrap_no_wrap_classes():
    """ Do not wrap instances of classes passed in no_wrap_classes."""
    obj = Foo()
    result = wrap_with_safe_string(obj)
    assert result is not obj
    assert isinstance(result, SafeStringWrapper)

    result = wrap_with_safe_string(obj, no_wrap_classes=Foo)
    assert result is obj

    result = wrap_with_safe_string(obj, no_wrap_classes=Bar)
    assert result is not obj
    assert isinstance(result, SafeStringWrapper)


def test_do_not_wrap_safestringwrapper():
    """ Do not wrap SafeStringWrapper: only wrap one layer."""
    obj = SafeStringWrapper(None)
    result = wrap_with_safe_string(obj)
    assert result is obj


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
