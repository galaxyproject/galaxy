from galaxy import util


def test_strip_control_characters():
    s = '\x00bla'
    assert util.strip_control_characters(s) == 'bla'


def test_strip_control_characters_nested():
    s = '\x00bla'
    stripped_s = 'bla'
    l = [s]
    t = (s, 'blub')
    d = {42: s}
    assert util.strip_control_characters_nested(l)[0] == stripped_s
    assert util.strip_control_characters_nested(t)[0] == stripped_s
    assert util.strip_control_characters_nested(d)[42] == stripped_s
