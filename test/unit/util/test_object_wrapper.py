from galaxy.util.object_wrapper import (
    __DONT_SANITIZE_TYPES__,
    get_no_wrap_classes,
    SafeStringWrapper,
    wrap_with_safe_string,
)


class Foo:
    pass


class Bar:
    pass


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

    def test_default_no_wrap_classes(self):
        """ If no arg supplied, use default."""
        expected = list(__DONT_SANITIZE_TYPES__) + [SafeStringWrapper]
        classes = get_no_wrap_classes()
        assert set(classes) == set(expected)

    def test_no_wrap_classes_one_arg(self):
        """ One class passed."""
        expected = list(__DONT_SANITIZE_TYPES__) + [SafeStringWrapper] + [Foo]
        classes = get_no_wrap_classes(no_wrap_classes=Foo)
        assert set(classes) == set(expected)

    def test_no_wrap_classes_multiple_arg_as_list(self):
        """ Multiple classses passed as a list."""
        arg = [Foo, Bar]
        expected = list(__DONT_SANITIZE_TYPES__) + [SafeStringWrapper] + [Foo, Bar]
        classes = get_no_wrap_classes(no_wrap_classes=arg)
        assert set(classes) == set(expected)

    def test_no_wrap_classes_multiple_arg_as_tuple(self):
        """ Multiple classses passed as a tuple."""
        arg = (Foo, Bar)
        expected = list(__DONT_SANITIZE_TYPES__) + [SafeStringWrapper] + [Foo, Bar]
        classes = get_no_wrap_classes(no_wrap_classes=arg)
        assert set(classes) == set(expected)
