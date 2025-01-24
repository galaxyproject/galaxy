import sys

import pytest
from Cheetah.NameMapper import NotFound

from galaxy.util.template import fill_template

# In Python 3.12 calling `locals()`` inside a comprehension now includes
# variables from outside the comprehension, see
# https://docs.python.org/dev/whatsnew/3.12.html#pep-709-comprehension-inlining
PY312_OR_LATER = sys.version_info[:2] >= (3, 12)

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

INVALID_CHEETAH_SYNTAX = """#if 1 <> 1
1 is not 1
#else
1 is 1
#end if"""


def test_fill_simple_template():
    template_str = str(fill_template(SIMPLE_TEMPLATE, {"a_list": [1, 2]}))
    assert template_str == FILLED_SIMPLE_TEMPLATE


def test_fill_list_comprehension_template():
    if PY312_OR_LATER:
        template_str = fill_template(LIST_COMPREHENSION_TEMPLATE, retry=0)
        assert template_str == "echo 1\n"
    else:
        with pytest.raises(NotFound):
            fill_template(LIST_COMPREHENSION_TEMPLATE, retry=0)


def test_fill_list_comprehension_template_2():
    template_str = fill_template(LIST_COMPREHENSION_TEMPLATE, python_template_version="2", retry=1)
    assert template_str == "echo 1\n"


def test_fill_dict_comprehension():
    if PY312_OR_LATER:
        template_str = fill_template(DICT_COMPREHENSION_TEMPLATE, retry=1)
        assert template_str == "echo 1\n"
    else:
        with pytest.raises(NotFound):
            fill_template(DICT_COMPREHENSION_TEMPLATE, retry=1)


def test_set_comprehension():
    if PY312_OR_LATER:
        template_str = fill_template(SET_COMPR_TEMPLATE, retry=1)
        assert template_str == "echo 1\n"
    else:
        with pytest.raises(NotFound):
            fill_template(SET_COMPR_TEMPLATE, retry=1)


def test_gen_expr():
    with pytest.raises(NotFound):
        fill_template(GEN_EXPR_TEMPLATE, retry=1)


def test_fix_template_two_to_three():
    template_str = fill_template(TWO_TO_THREE_TEMPLATE, python_template_version="2", retry=1)
    assert template_str == "a a 1"


def test_fix_template_invalid_cheetah():
    template_str = fill_template(INVALID_CHEETAH_SYNTAX, python_template_version="2", retry=1)
    assert template_str == "1 is 1\n"
