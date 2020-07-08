import sys

import pytest
from Cheetah.NameMapper import NotFound

from galaxy.util.template import fill_template

SIMPLE_TEMPLATE = """#for item in $a_list:
    echo $item
    #end for
"""
FILLED_SIMPLE_TEMPLATE = """    echo 1
    echo 2
"""
LIST_COMPREHENSION_TEMPLATE = """#for $i in [1]:
#set $v = [str(_) for _ in [1] if _ == $i]
echo $v[0]
#end for
"""
DICT_COMPREHENSION_TEMPLATE = """#for $i in [1]:
#set $v = {_:_ for _ in [1] if _ == $i}
echo $v[$i]
#end for
"""
SET_COMPR_TEMPLATE = """#for $i in [1]:
#set $v = {_ for _ in [1] if _ == $i}
echo $v.pop()
#end for
"""
GEN_EXPR_TEMPLATE = """#for $i in [1]:
#set $v = list(_ for _ in [1] if _ == $i)
echo $v[0]
#end for
"""
TWO_TO_THREE_TEMPLATE = """#set $a = [x for x in {'a': '1'}.iterkeys()][0]
#set $b = [x for x in {'a': '1'}.iteritems()][0][0]
#set $c = [x for x in {'a': '1'}.itervalues()][0]
$a $b $c"""


def test_fill_simple_template():
    template_str = str(fill_template(SIMPLE_TEMPLATE, {'a_list': [1, 2]}))
    assert template_str == FILLED_SIMPLE_TEMPLATE


def test_fill_list_comprehension_template():
    if sys.version_info.major > 2:
        with pytest.raises(NotFound):
            fill_template(LIST_COMPREHENSION_TEMPLATE, retry=0)
    else:
        template_str = fill_template(LIST_COMPREHENSION_TEMPLATE, retry=0)
        assert template_str == 'echo 1\n'


def test_fill_list_comprehension_template_2():
    template_str = fill_template(LIST_COMPREHENSION_TEMPLATE, python_template_version='2', retry=1)
    assert template_str == 'echo 1\n'


def test_fill_dict_comprehension():
    with pytest.raises(NotFound):
        fill_template(DICT_COMPREHENSION_TEMPLATE, retry=1)


def test_set_comprehension():
    with pytest.raises(NotFound):
        fill_template(SET_COMPR_TEMPLATE, retry=1)


def test_gen_expr():
    with pytest.raises(NotFound):
        fill_template(GEN_EXPR_TEMPLATE, retry=1)


def test_fix_template_two_to_three():
    template_str = fill_template(TWO_TO_THREE_TEMPLATE, python_template_version='2', retry=1)
    assert template_str == 'a a 1'
