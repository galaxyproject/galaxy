from galaxy.util.search import (
    parse_filters,
    parse_filters_structured,
)


def test_parse_filters():
    result = parse_filters("moo cow", {})
    assert result[0] is None
    assert result[1] == "moo cow"

    result = parse_filters("moo:mooterm cow", {"moo": "mookey"})
    filters = result[0]
    assert filters
    assert filters[0][0] == "mookey"
    assert filters[0][1] == "mooterm"
    assert result[1] == "cow"

    result = parse_filters("moo:'moo term' cow", {"moo": "mookey"})
    filters = result[0]
    assert filters
    assert filters[0][0] == "mookey"
    assert filters[0][1] == "moo term"
    assert result[1] == "cow"

    result = parse_filters("""moo:"moo term" cow""", {"moo": "mookey"})
    filters = result[0]
    assert filters
    assert filters[0][0] == "mookey"
    assert filters[0][1] == "moo term"
    assert result[1] == "cow"

    result = parse_filters("cow moo:'moo term'", {"moo": "mookey"})
    filters = result[0]
    assert filters
    assert filters[0][0] == "mookey"
    assert filters[0][1] == "moo term"
    assert result[1] == "cow"

    result = parse_filters("cow moo:'moo term' other side", {"moo": "mookey"})
    filters = result[0]
    assert filters
    assert filters[0][0] == "mookey"
    assert filters[0][1] == "moo term"
    assert result[1] == "cow other side"


def test_parse_filters_structured():
    result = parse_filters_structured("cow moo:moo other side", {"moo": "mookey"}, preserve_quotes=True)
    filters = result.filter_terms
    assert filters
    assert filters[0].quoted is False
    text_terms = result.text_terms
    assert len(text_terms) == 3
    assert text_terms[0].text == "cow"
    assert text_terms[0].quoted is False
    assert text_terms[1].text == "other"
    assert text_terms[1].quoted is False
    assert text_terms[2].text == "side"
    assert text_terms[2].quoted is False

    result = parse_filters_structured("cow moo:'moo' other side", {"moo": "mookey"}, preserve_quotes=True)
    filters = result.filter_terms
    assert filters
    assert filters[0].quoted is True
    text_terms = result.text_terms
    assert len(text_terms) == 3
    assert text_terms[0].text == "cow"
    assert text_terms[0].quoted is False
    assert text_terms[1].text == "other"
    assert text_terms[1].quoted is False
    assert text_terms[2].text == "side"
    assert text_terms[2].quoted is False

    result = parse_filters_structured("""cow moo:"moo" other side""", {"moo": "mookey"}, preserve_quotes=True)
    filters = result.filter_terms
    assert filters
    assert filters[0].quoted is True

    result = parse_filters_structured("cow moo:'moo term' other side", {"moo": "mookey"}, preserve_quotes=True)
    filters = result.filter_terms
    assert filters
    assert filters[0].filter == "mookey"
    assert filters[0].text == "moo term"
    assert filters[0].quoted is True
    assert " ".join(t.text for t in result.text_terms) == "cow other side"

    result = parse_filters_structured("cow 'other side' foo", {"moo": "mookey"}, preserve_quotes=True)
    text_terms = result.text_terms
    assert len(text_terms) == 3
    assert text_terms[0].text == "cow"
    assert text_terms[0].quoted is False
    assert text_terms[1].text == "other side"
    assert text_terms[1].quoted is True
    assert text_terms[2].text == "foo"
    assert text_terms[2].quoted is False
