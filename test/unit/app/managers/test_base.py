from galaxy.managers.base import combine_lists


class NotFalsy:
    """Class requires explicit check for None"""

    def __bool__(self):
        raise Exception("not implemented")


def test_combine_lists():
    foo, bar = NotFalsy(), NotFalsy()
    assert combine_lists(foo, None) == [foo]
    assert combine_lists(None, foo) == [foo]
    assert combine_lists(foo, bar) == [foo, bar]
    assert combine_lists([foo, bar], None) == [foo, bar]
    assert combine_lists(None, [foo, bar]) == [foo, bar]
    assert combine_lists(None, None) == []
