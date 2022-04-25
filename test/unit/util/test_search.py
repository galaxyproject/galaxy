from galaxy.util.search import parse_filters


def test_parse_filters():
    result = parse_filters("moo cow", {})
    assert result[0] is None
    assert result[1] == "moo cow"

    result = parse_filters("moo:mooterm cow", {"moo": "mookey"})
    assert result[0][0][0] == "mookey"
    assert result[0][0][1] == "mooterm"
    assert result[1] == "cow"

    result = parse_filters("moo:'moo term' cow", {"moo": "mookey"})
    assert result[0][0][0] == "mookey"
    assert result[0][0][1] == "moo term"
    assert result[1] == "cow"

    result = parse_filters("""moo:"moo term" cow""", {"moo": "mookey"})
    assert result[0][0][0] == "mookey"
    assert result[0][0][1] == "moo term"
    assert result[1] == "cow"

    result = parse_filters("cow moo:'moo term'", {"moo": "mookey"})
    assert result[0][0][0] == "mookey"
    assert result[0][0][1] == "moo term"
    assert result[1] == "cow"

    result = parse_filters("cow moo:'moo term' other side", {"moo": "mookey"})
    assert result[0][0][0] == "mookey"
    assert result[0][0][1] == "moo term"
    assert result[1] == "cow other side"
