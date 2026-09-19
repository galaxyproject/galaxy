from galaxy.util.search import (
    filter_terms,
    FilteredTerm,
    parse_filters,
    parse_filters_structured,
    RawTextTerm,
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


def test_filter_terms_drops_short_raw_terms():
    parsed = parse_filters_structured("Copy of Genomic Assembly and analysis", {})
    filtered = filter_terms(parsed, min_raw_term_length=4, max_raw_terms=None)
    kept = [t.text for t in filtered.terms]
    assert kept == ["Copy", "Genomic", "Assembly", "analysis"]


def test_filter_terms_preserves_quoted_raw_terms():
    parsed = parse_filters_structured("'ab' Copy 'de'", {})
    filtered = filter_terms(parsed, min_raw_term_length=4, max_raw_terms=None)
    assert [(t.text, t.quoted) for t in filtered.terms] == [
        ("ab", True),
        ("Copy", False),
        ("de", True),
    ]


def test_filter_terms_preserves_filtered_terms_of_any_length():
    parsed = parse_filters_structured("tag:ab user:cd Copy", {"tag": "tag", "user": "user"})
    filtered = filter_terms(parsed, min_raw_term_length=4, max_raw_terms=None)
    kinds = [(t.__class__.__name__, t.text) for t in filtered.terms]
    # Both filtered terms are preserved even though their text is shorter than 4;
    # "Copy" (4) is preserved too.
    assert ("FilteredTerm", "ab") in kinds
    assert ("FilteredTerm", "cd") in kinds
    assert ("RawTextTerm", "Copy") in kinds


def test_filter_terms_caps_raw_terms_only():
    parsed = parse_filters_structured(
        "tag:foo Copy Genomic Assembly analysis shared user nedflanders extra1 extra2",
        {"tag": "tag"},
    )
    filtered = filter_terms(parsed, min_raw_term_length=4, max_raw_terms=3)
    raw = [t.text for t in filtered.terms if isinstance(t, RawTextTerm)]
    filt = [t.text for t in filtered.terms if isinstance(t, FilteredTerm)]
    assert raw == ["Copy", "Genomic", "Assembly"]
    assert filt == ["foo"]


def test_filter_terms_defaults():
    # Default behaviour: 4-char min length, 7-term cap on raw terms.
    parsed = parse_filters_structured(
        "Copy of Genomic Assembly and analysis - RDH shared by user nedflanders",
        {},
    )
    filtered = filter_terms(parsed)
    kept = [t.text for t in filtered.terms]
    # of, and, -, RDH, by dropped for length; everything else survives.
    assert kept == ["Copy", "Genomic", "Assembly", "analysis", "shared", "user", "nedflanders"]
