import errno
import os
import tempfile
import time
from enum import Enum
from io import (
    BytesIO,
    StringIO,
)
from pathlib import Path
from typing import Dict
from urllib.parse import urlsplit

import pytest

from galaxy import util
from galaxy.util.json import safe_loads

SECTION_XML = """<?xml version="1.0" ?>
<section id="fasta_fastq_manipulation" name="Fasta Fastq Manipulation" version="">
    <tool file="toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/fb1313d79396/seq_filter_by_id/tools/seq_filter_by_id/seq_filter_by_id.xml" guid="toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/seq_filter_by_id/0.2.5">
        <tool_shed>
            toolshed.g2.bx.psu.edu
        </tool_shed>
    </tool>
</section>
"""


def test_strip_control_characters():
    s = "\x00bla"
    assert util.strip_control_characters(s) == "bla"


def test_stream_to_path(tmp_path):
    destination = tmp_path / "streamed"

    assert util.stream_to_path(BytesIO(b"streamed content"), destination) == destination
    assert destination.read_bytes() == b"streamed content"


def test_stream_to_open_named_file_compatibility(tmp_path):
    destination = tmp_path / "streamed"
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT)

    assert util.stream_to_open_named_file(BytesIO(b"streamed content"), fd, destination) == destination
    assert destination.read_bytes() == b"streamed content"
    with pytest.raises(OSError):
        os.fstat(fd)


def test_parse_xml_string():
    section = util.parse_xml_string(SECTION_XML)
    _verify_section(section)


def test_parse_xml_file():
    with tempfile.NamedTemporaryFile(mode="w") as tmp:
        tmp.write(SECTION_XML)
        tmp.flush()
        section = util.parse_xml(tmp.name).getroot()
    _verify_section(section)


def _verify_section(section):
    tool = next(iter(section))
    assert sorted(tool.items()) == [
        (
            "file",
            "toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/fb1313d79396/seq_filter_by_id/tools/seq_filter_by_id/seq_filter_by_id.xml",
        ),
        ("guid", "toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/seq_filter_by_id/0.2.5"),
    ]
    assert next(iter(tool)).text == "toolshed.g2.bx.psu.edu"


def test_xml_to_string():
    section = util.parse_xml_string(SECTION_XML)
    s = util.xml_to_string(section)
    assert len(s.split("\n")) == 1


def test_xml_to_string_pretty():
    section = util.parse_xml_string(SECTION_XML)
    s = util.xml_to_string(section, pretty=True)
    PRETTY = """<?xml version="1.0" ?>
<section id="fasta_fastq_manipulation" name="Fasta Fastq Manipulation" version="">
    <tool file="toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/fb1313d79396/seq_filter_by_id/tools/seq_filter_by_id/seq_filter_by_id.xml" guid="toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/seq_filter_by_id/0.2.5">
        <tool_shed>toolshed.g2.bx.psu.edu</tool_shed>
    </tool>
</section>"""
    assert s == PRETTY


def test_parse_xml_enoent():
    with tempfile.NamedTemporaryFile() as temp:
        path = temp.name
    with pytest.raises(IOError) as excinfo:
        util.parse_xml(path)
    assert excinfo.value.errno == errno.ENOENT


def test_clean_multiline_string():
    x = util.clean_multiline_string("""
        a
        b
        c
""")
    assert x == "a\nb\nc\n"


def test_iter_start_of_lines():
    assert list(util.iter_start_of_line(StringIO("\n1\n\n12\n123\n1234\n"), 1)) == ["\n", "1", "\n", "1", "1", "1"]


def test_safe_loads():
    d: Dict[str, str] = {}
    rval = safe_loads(d)
    assert rval == d
    assert rval is not d
    rval["foo"] = "bar"
    assert "foo" not in d
    s = '{"foo": "bar"}'
    assert safe_loads(s) == {"foo": "bar"}


def test_in_packages(monkeypatch):
    util_path = Path(util.__file__).parent
    assert util.in_packages() == (not str(util_path).endswith("lib/galaxy/util"))


def test_galaxy_directory(monkeypatch):
    galaxy_dir = util.galaxy_directory()
    assert os.path.isabs(galaxy_dir)
    assert os.path.isfile(os.path.join(galaxy_dir, "run.sh"))


def test_listify() -> None:
    assert util.listify(None) == []
    assert util.listify(False) == []
    assert util.listify(True) == [True]
    assert util.listify("foo") == ["foo"]
    assert util.listify("foo, bar") == ["foo", " bar"]
    assert util.listify("foo, bar", do_strip=True) == ["foo", "bar"]
    list_ = [1, 2, 3]
    assert util.listify(list_) is list_
    assert util.listify((1, 2, 3)) == [1, 2, 3]
    s = {1, 2, 3}
    assert util.listify(s) == [s]
    d = {"a": 1, "b": 2, "c": 3}
    assert util.listify(d) == [d]
    o = object()
    assert util.listify(o) == [o]


def test_enum_values():
    class Stuff(str, Enum):
        A = "a"
        C = "c"
        B = "b"

    assert util.enum_values(Stuff) == ["a", "c", "b"]


DOI_VALID_VALUES = [
    "https://doi.org/10.1234/42",
    "doi.org/10.1234/42",
    "doi:10.1234/42",
    "doi:10.1234567890/42",  # longer prefix
    "doi:10.1234/42ab:%&*$//crazy-suffix/%/&/",
    "doi:10.1234/aa",
]


@pytest.mark.parametrize("input", DOI_VALID_VALUES)
def test_validate_doi_pass(input):
    assert util.validate_doi(input)


DOI_INVALID_VALUES = [
    "http://doi.org/10.1234/42",
    "invalid:10.1234/42",
    "doi:11.1234/42",
    "doi:101234/42",
    "doi:10. 1234/42",
    "doi:10.abc/42",
    "doi:10.1234/ 42",
    "doi:10.1234/42/a b",
]


@pytest.mark.parametrize("input", DOI_INVALID_VALUES)
def test_validate_doi_fail(input):
    assert not util.validate_doi(input)


def test_validate_doi_fail_too_long():
    long_suffix = "a" * (util.DOI_MAX_LENGTH - 12)
    doi = f"doi:10.1000/{long_suffix}"
    assert util.validate_doi(doi)
    assert not util.validate_doi(doi + "a")  # Increase length by 1 past max limit


@pytest.mark.parametrize(
    "input_name,expected_output",
    [
        # Existing documented behavior
        ("My Cool Object", "My-Cool-Object"),
        ("!My Cool Object!", "My-Cool-Object"),
        ("Hello\u20a9\u25ce\u0491\u029f\u217e", "Hello"),
        # Additional edge cases
        ("simple", "simple"),
        ("UPPERCASE", "UPPERCASE"),  # Note: lowercase applied separately
        ("with-dash", "with-dash"),
        ("with spaces", "with-spaces"),
        ("  multiple   spaces  ", "-multiple-spaces"),
        ("trailing!", "trailing"),
        ("!leading", "leading"),
        ("special@#$chars", "specialchars"),
        ("parentheses(test)", "parenthesestest"),
        ("Rincewind (Ankh-Morpork)", "Rincewind-Ankh-Morpork"),
    ],
)
def test_ready_name_for_url(input_name, expected_output):
    """Test that ready_name_for_url correctly sanitizes names for URL use."""
    assert util.ready_name_for_url(input_name) == expected_output


@pytest.mark.parametrize(
    "target,expected_substring",
    [
        ("normal.txt", 'filename="normal.txt"'),
        ("file.gz ", 'filename="file.gz"'),
        (" file.gz", 'filename="file.gz"'),
        (" file.gz ", 'filename="file.gz"'),
        ("Galaxy102-[name].fastqsanger.gz ", 'filename="Galaxy102-[name].fastqsanger.gz"'),
    ],
)
def test_to_content_disposition(target, expected_substring):
    result = util.to_content_disposition(target)
    assert result.startswith("attachment; ")
    assert expected_substring in result
    # Ensure no trailing whitespace in the header value
    assert result == result.strip()


@pytest.mark.parametrize(
    "text,expected",
    [
        ("https://user:secret@example.org/a.bed", "https://example.org/a.bed"),
        ("http://user:secret@example.org:8080/a.bed?x=1", "http://example.org:8080/a.bed?x=1"),
        ("ftp://user:secret@ftp.example.org/pub/a.bed", "ftp://ftp.example.org/pub/a.bed"),
        ("https://token@example.org/a.bed", "https://example.org/a.bed"),
        ("https://user:p@ss@word@example.org/a.bed", "https://example.org/a.bed"),
        ("https://us%40er:p%40ss@example.org/a.bed", "https://example.org/a.bed"),
        ("https://user:secret@[::1]:8080/", "https://[::1]:8080/"),
        ("https://user:secret@example.org", "https://example.org"),
        (
            "404 Client Error: Not Found for url: https://user:p%40ss@example.org/a.bed (https://user:p@ss@example.org/a.bed)",
            "404 Client Error: Not Found for url: https://example.org/a.bed (https://example.org/a.bed)",
        ),
        ("Invalid uri [s3://key:secret@bucket/a.bed]", "Invalid uri [s3://bucket/a.bed]"),
        ("https://example.org/a.bed", "https://example.org/a.bed"),
        ("https://example.org/a@b.bed?mail=me@example.org", "https://example.org/a@b.bed?mail=me@example.org"),
        ("https://example.org/a.bed contact admin@example.org", "https://example.org/a.bed contact admin@example.org"),
        ("Contact admin@example.org", "Contact admin@example.org"),
        ("", ""),
    ],
)
def test_strip_url_userinfo(text, expected):
    assert util.strip_url_userinfo(text) == expected


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://user:sec ret@example.org/a.bed", "https://example.org/a.bed"),
        ("https://user:se[cret@example.org/a.bed", "https://example.org/a.bed"),
        ("https://user:se?cret@example.org/a.bed", "https://example.org/a.bed"),
        ("https://user:se#cret@example.org", "https://example.org"),
        ("https://user:p@ss word@example.org", "https://example.org"),
        ("https://user:secret@[::1]:8080/a.bed", "https://[::1]:8080/a.bed"),
        ("https://example.org/a@b.bed?mail=me@example.org", "https://example.org/a@b.bed?mail=me@example.org"),
        ("example.org/a.bed", "example.org/a.bed"),
        ("", ""),
    ],
)
def test_url_without_userinfo(url, expected):
    assert util.url_without_userinfo(url) == expected


def test_strip_url_userinfo_known_url_with_whitespace():
    url = "https://user:sec ret@example.org/a.bed"
    text = f"URL contains unencoded characters (e.g. spaces): {url}. ({url}) for url: https://user:sec%20ret@example.org/a.bed"
    stripped = util.strip_url_userinfo(text, [url])
    assert "user" not in stripped
    assert "sec" not in stripped
    assert stripped.count("https://example.org/a.bed") == 3


def test_strip_url_userinfo_known_url_is_prefix_of_another():
    urls = ["https://user:sec ret@example.org/a", "https://user:sec ret@example.org/a.bed"]
    stripped = util.strip_url_userinfo(f"{urls[0]} {urls[1]}", urls)
    assert stripped == "https://example.org/a https://example.org/a.bed"


def test_strip_url_userinfo_trimmed_known_url_with_whitespace():
    url = " unknownscheme://user:sec ret@example.org/a "
    text = f"Could not find handler for URI [{url.strip()}] ({url})"
    expected = "Could not find handler for URI [unknownscheme://example.org/a] ( unknownscheme://example.org/a )"
    assert util.strip_url_userinfo(text, [url]) == expected


def test_strip_url_userinfo_known_url_without_urlsplit_removed_characters():
    url = "https://user:sec\tret word@example.org/a"
    stripped = util.strip_url_userinfo("https://user:secret word@example.org/a", [url])
    assert stripped == "https://example.org/a"


@pytest.mark.parametrize("url", ["https://user:se?cret@example.org/a.bed", "https://user:se#cret@example.org/a.bed"])
def test_strip_url_userinfo_known_url_with_query_or_fragment_character(url):
    stripped = util.strip_url_userinfo(f"Invalid URL '{url}': No host supplied", [url])
    assert stripped == "Invalid URL 'https://example.org/a.bed': No host supplied"


def test_strip_url_userinfo_known_userinfo_without_scheme():
    # urlparse() quotes the netloc of a URL it rejects without the "://" before it.
    url = "ftp://user:secret@exa／mple.org/a"
    text = f"netloc 'user:secret@exa／mple.org' contains invalid characters under NFKC normalization ({url})"
    expected = f"{util.URL_PARSER_ERROR} (ftp://exa／mple.org/a)"
    assert util.strip_url_userinfo(text, [url]) == expected


@pytest.mark.parametrize(
    "url",
    [
        "ftp://user:secret@exa\uff0fmple.org/a",
        " ftp://user:secret@exa\uff0fmple.org/a ",
        "ftp://us\uff0fer:se?cret@example.org/a",
    ],
)
def test_strip_url_userinfo_known_url_parser_error(url):
    with pytest.raises(ValueError) as exc_info:
        urlsplit(url)
    stripped = util.strip_url_userinfo(f"Failed to fetch url: {exc_info.value} ({url})", [url])
    assert "secret" not in stripped
    # The parser quotes a netloc only up to the first "?", here a part of the userinfo.
    assert "er:se" not in stripped


def _url_parser_error(url):
    with pytest.raises(ValueError) as exc_info:
        urlsplit(url)
    return str(exc_info.value)


def _unparsable_urls(count, userinfo="user{}:secret@"):
    return [f"ftp://{userinfo.format(i)}exa／mple{i}.org/a" for i in range(count)]


def test_strip_url_userinfo_known_url_parser_errors_up_to_limit():
    urls = _unparsable_urls(util._MAX_URL_PARSER_ERRORS)
    text = " ".join(_url_parser_error(url) for url in urls)
    expected = " ".join([util.URL_PARSER_ERROR] * len(urls))
    assert util.strip_url_userinfo(text, urls) == expected


@pytest.mark.parametrize("count", [1, 10_000], ids=["one", "many"])
def test_strip_url_userinfo_withholds_text_past_known_url_parser_error_limit(count):
    urls = _unparsable_urls(util._MAX_URL_PARSER_ERRORS + count)
    text = " ".join(_url_parser_error(url) for url in urls)
    assert util.strip_url_userinfo(text, urls) == util.URL_PARSER_ERRORS_WITHHELD


def test_strip_url_userinfo_counts_each_known_url_parser_error_once():
    url = _unparsable_urls(1)[0]
    text = f"Failed to fetch url: {_url_parser_error(url)}"
    expected = f"Failed to fetch url: {util.URL_PARSER_ERROR}"
    urls = [url, f" {url} "] * util._MAX_URL_PARSER_ERRORS
    assert util.strip_url_userinfo(text, urls) == expected


def test_strip_url_userinfo_skips_known_url_parser_errors_longer_than_text():
    urls = _unparsable_urls(util._MAX_URL_PARSER_ERRORS + 1)
    assert util.strip_url_userinfo("Failed to fetch url", urls) == "Failed to fetch url"


def test_strip_url_userinfo_skips_known_url_parser_errors_without_userinfo():
    urls = _unparsable_urls(util._MAX_URL_PARSER_ERRORS + 1, userinfo="")
    text = " ".join(_url_parser_error(url) for url in urls)
    assert util.strip_url_userinfo(text, urls) == text


@pytest.mark.parametrize("reverse", [False, True], ids=["inner-first", "outer-first"])
def test_strip_url_userinfo_known_url_parser_error_inside_another(reverse):
    inner_url = "ftp://user:secret@exa／mple.org/a"
    # The userinfo of this URL holds the whole parser error of inner_url.
    outer_url = f"ftp://x:{_url_parser_error(inner_url)}@h／/a"
    urls = [inner_url, outer_url][:: -1 if reverse else 1]
    assert util.strip_url_userinfo(_url_parser_error(outer_url), urls) == util.URL_PARSER_ERROR


def test_strip_url_userinfo_known_url_with_parser_error_in_userinfo():
    inner_url = "ftp://user:secret@exa／mple.org/a"
    outer_url = f"ftp://x:{_url_parser_error(inner_url)}@h／/a"
    text = f"Failed to fetch url: {_url_parser_error(outer_url)} ({outer_url})"
    expected = f"Failed to fetch url: {util.URL_PARSER_ERROR} (ftp://h／/a)"
    assert util.strip_url_userinfo(text, [inner_url, outer_url]) == expected


_INNER_URL = "ftp://longuser:longsecret@exa／mple.org/a"
# The path of this URL holds the parser error of _INNER_URL, which is longer than its own.
_OUTER_URL = f"ftp://x／:outersecret@h/{_url_parser_error(_INNER_URL)}"


@pytest.mark.parametrize("reverse", [False, True], ids=["outer-first", "inner-first"])
@pytest.mark.parametrize("padding", ["", " " + "x" * 200], ids=["unpadded", "padded"])
def test_strip_url_userinfo_known_url_parser_error_with_another_in_path(reverse, padding):
    urls = [_OUTER_URL, _INNER_URL][:: -1 if reverse else 1]
    text = _url_parser_error(_OUTER_URL) + padding
    assert util.strip_url_userinfo(text, urls) == util.URL_PARSER_ERROR + padding


@pytest.mark.parametrize("reverse", [False, True], ids=["outer-first", "inner-first"])
def test_strip_url_userinfo_overlapping_known_url_parser_errors(reverse):
    # These parser errors start and end with "n", so two of them can share a character.
    urls = [_OUTER_URL, _INNER_URL][:: -1 if reverse else 1]
    text = _url_parser_error(_OUTER_URL)[:-1] + _url_parser_error(_INNER_URL)
    assert util.strip_url_userinfo(text, urls) == util.URL_PARSER_ERROR


def test_strip_url_userinfo_overlapping_copies_of_known_url_parser_error():
    error = _url_parser_error(_INNER_URL)
    assert util.strip_url_userinfo(f"{error}{error[1:]}", [_INNER_URL]) == util.URL_PARSER_ERROR


def test_strip_url_userinfo_parser_error_of_trimmed_known_url():
    # Without a path, the trailing space is part of the netloc the parser quotes.
    url = " ftp://user:secret@exa／mple.org "
    assert util.strip_url_userinfo(_url_parser_error(url.strip()), [url]) == util.URL_PARSER_ERROR


def test_strip_url_userinfo_withholds_text_covered_many_times_by_known_url_parser_error():
    # The parser error of this URL is a run of 10 copies of one block, so it occurs at every block of the text.
    suffix = "' contains invalid characters under NFKC normalization"
    netloc = "u／:pw@h" + f"{suffix}netloc 'u／:pw@h" * 9
    url = f"ftp://{netloc}/a"
    text = _url_parser_error(url) * 100
    assert text == f"netloc 'u／:pw@h{suffix}" * 1_000
    assert util.strip_url_userinfo(text, [url]) == util.URL_PARSER_ERRORS_WITHHELD


_NESTED_SECRETS = {
    False: ["alpha-secret-1", "bravo-secret-2", "charlie-secret-3"],
    # The generic scan ends an authority at whitespace, so only the known URLs can delimit these.
    True: ["alpha sec ret-1", "bravo sec ret-2", "charlie sec ret-3"],
}


def _nest_url(index, inner, placement, broken, spaced):
    # The fullwidth solidus fails urlsplit(); in the userinfo, the URL without its userinfo parses.
    user, host = f"user{index}", f"example{index}.org"
    if broken == "userinfo":
        user += "／"
    else:
        host = host.replace("x", "x／", 1)
    password = _NESTED_SECRETS[spaced][index]
    if placement == "path":
        return f"ftp://{user}:{password}@{host}/{inner}"
    if placement == "query":
        return f"ftp://{user}:{password}@{host}/a?next={inner}"
    if placement == "userinfo":
        return f"ftp://{user}:{password}{inner}@{host}/a"
    return f"ftp://{user}:{password}@{host}{inner}/a"


def _nested_url_chain(placements, broken, spaced):
    """URLs from innermost to outermost; each one holds the parser error of the one before it."""
    urls = [_nest_url(0, "", "path", broken, spaced)]
    for index, placement in enumerate(placements, start=1):
        inner_error = _url_parser_error(urls[-1])
        urls.append(_nest_url(index, inner_error, placement, broken, spaced))
        assert inner_error in urls[-1]
        _url_parser_error(urls[-1])
    return urls


def _assert_no_userinfo(stripped, secrets, count):
    for secret in secrets:
        for part in secret.split():
            assert part not in stripped
    for index in range(count):
        assert f"user{index}" not in stripped


_PLACEMENTS = ["path", "query", "userinfo", "netloc"]


@pytest.mark.parametrize(
    "placements",
    [(p,) for p in _PLACEMENTS] + [(p, q) for p in _PLACEMENTS for q in _PLACEMENTS],
    ids=lambda placements: "-".join(placements),
)
@pytest.mark.parametrize("broken", ["host", "userinfo"])
@pytest.mark.parametrize("spaced", [False, True], ids=["unspaced", "spaced"])
@pytest.mark.parametrize("reverse", [False, True], ids=["inner-first", "outer-first"])
@pytest.mark.parametrize("form", ["error", "fetch", "padded", "all-errors"])
def test_strip_url_userinfo_nested_known_url_parser_errors(placements, broken, spaced, reverse, form):
    urls = _nested_url_chain(placements, broken, spaced)
    outer_url = urls[-1]
    secrets = _NESTED_SECRETS[spaced][: len(urls)]
    if form == "error":
        text = _url_parser_error(outer_url)
    elif form == "fetch":
        text = f"Failed to fetch url: {_url_parser_error(outer_url)} ({outer_url})"
    elif form == "padded":
        text = _url_parser_error(outer_url) + " " + "x" * sum(map(len, urls))
    else:
        text = " ".join(_url_parser_error(url) for url in urls)
    assert secrets[-1] in text
    if form == "all-errors":
        assert all(secret in text for secret in secrets)
    stripped = util.strip_url_userinfo(text, urls[:: -1 if reverse else 1])
    _assert_no_userinfo(stripped, secrets, len(urls))


def _nested_url(placements, spaced):
    """A URL holding a URL in each of ``placements``, outermost first; each one has userinfo."""
    secrets = _NESTED_SECRETS[spaced]
    url = f"ftp://user0:{secrets[0]}@example0.org/a"
    for index, placement in enumerate(reversed(placements), start=1):
        prefix = f"https://user{index}:{secrets[index]}@example{index}.org/a"
        if placement == "path":
            url = f"{prefix}/{url}"
        elif placement == "query":
            url = f"{prefix}?next={url}"
        else:
            url = f"{prefix}#{url}"
    return url


_URL_PLACEMENTS = ["path", "query", "fragment"]


@pytest.mark.parametrize(
    "placements",
    [(p,) for p in _URL_PLACEMENTS] + [(p, q) for p in _URL_PLACEMENTS for q in _URL_PLACEMENTS],
    ids=lambda placements: "-".join(placements),
)
@pytest.mark.parametrize("spaced", [False, True], ids=["unspaced", "spaced"])
@pytest.mark.parametrize("form", ["url", "rejected", "fetch"])
def test_strip_url_userinfo_urls_nested_in_known_url(placements, spaced, form):
    url = _nested_url(placements, spaced)
    if form == "url":
        text = url
    elif form == "rejected":
        text = f"URL contains unencoded characters (e.g. spaces): {url}. The URL source should be encoded."
    else:
        text = f"Failed to fetch url: 404 Client Error: Not Found for url: {url} ({url})"
    count = len(placements) + 1
    secrets = _NESTED_SECRETS[spaced][:count]
    assert all(secret in text for secret in secrets)
    # Only the outer URL is requested, as in a fetch request.
    stripped = util.strip_url_userinfo(text, [url])
    _assert_no_userinfo(stripped, secrets, count)
    assert stripped.count("example0.org/a") == text.count("example0.org/a")


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.org/a?next=ftp://u:sec ret@h/b", "https://example.org/a?next=ftp://h/b"),
        ("https://example.org/a#ftp://u:sec ret@h", "https://example.org/a#ftp://h"),
        ("https://example.org/ftp://u:sec ret@h/b", "https://example.org/ftp://h/b"),
        ("https://example.org/a?next=ftp://u:se?c ret@h/b", "https://example.org/a?next=ftp://h/b"),
        ("https://example.org/a?next=ftp://u:se#c ret@h/b", "https://example.org/a?next=ftp://h/b"),
        ("https://o:outer pw@example.org/a?next=ftp://u:sec ret@h/b", "https://example.org/a?next=ftp://h/b"),
        ("https://example.org?next=ftp://u:sec ret@h/b", "https://example.org?next=ftp://h/b"),
        (
            "https://example.org/a?next=https://example.com/b?next=ftp://u:sec ret@h/c",
            "https://example.org/a?next=https://example.com/b?next=ftp://h/c",
        ),
    ],
)
def test_strip_url_userinfo_userinfo_of_url_nested_in_known_url(url, expected):
    text = f"URL contains unencoded characters (e.g. spaces): {url}. ({url})"
    assert (
        util.strip_url_userinfo(text, [url])
        == f"URL contains unencoded characters (e.g. spaces): {expected}. ({expected})"
    )


def test_strip_url_userinfo_url_nested_in_known_url_without_urlsplit_removed_characters():
    url = "https://example.org/a?next=ftp://u:sec\tret word@h/b"
    text = f"{url} for url: https://example.org/a?next=ftp://u:secret word@h/b"
    expected = "https://example.org/a?next=ftp://h/b for url: https://example.org/a?next=ftp://h/b"
    assert util.strip_url_userinfo(text, [url]) == expected


def test_strip_url_userinfo_scales_linearly_with_known_urls():
    # Each known URL ends in "/" followed by many "://", the worst case for a search per known URL.
    urls = [f"https://user{i}:sec ret@example.org/" + "://" * 10 for i in range(10_000)]
    text = "://" * 70_000
    start = time.perf_counter()
    assert util.strip_url_userinfo(text, urls) == text
    assert time.perf_counter() - start < 1.0


def test_strip_url_userinfo_scales_linearly_with_shared_known_userinfo_prefix():
    prefix = "u" * 50
    urls = [f"https://{prefix} {i}:secret@example.org/a" for i in range(10_000)]
    text = f"https://{prefix} 9999:secret/" * 3_000
    start = time.perf_counter()
    assert util.strip_url_userinfo(text, urls) == text
    assert time.perf_counter() - start < 1.0


def test_strip_url_userinfo_scales_linearly_with_urls_nested_in_known_url():
    url = "https://example.org/a?" + "".join(f"://x{i}@" for i in range(7_000))
    text = f"{url} ({url})"
    expected_url = "https://example.org/a?" + "://" * 7_000
    start = time.perf_counter()
    assert util.strip_url_userinfo(text, [url]) == f"{expected_url} ({expected_url})"
    assert time.perf_counter() - start < 1.0


def test_strip_url_userinfo_scales_linearly_with_known_urls_holding_nested_urls():
    urls = [f"https://example.org/a?next=ftp://user{i}:sec ret@h/b" for i in range(4_000)]
    text = "ftp://user3999:sec ret/" * 3_000 + " ".join(urls[:1_000])
    start = time.perf_counter()
    stripped = util.strip_url_userinfo(text, urls)
    assert time.perf_counter() - start < 1.0
    # count() keeps a failure report short; the text is too long for an "in" diff.
    assert stripped.count("sec ret@") == 0


@pytest.mark.parametrize(
    "text",
    [
        "https://example.org/" + "a." * 100_000,
        "https://" + "a" * 200_000,
        "a://" * 70_000,
    ],
    ids=["dotted-path", "long-netloc", "repeated-separator"],
)
def test_strip_url_userinfo_scales_linearly(text):
    start = time.perf_counter()
    assert util.strip_url_userinfo(text) == text
    assert time.perf_counter() - start < 1.0


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.org/data/a.bed", "a.bed"),
        ("https://example.org/a.bed?x=1", "a.bed?x=1"),
        ("https://user:secret@example.org", "example.org"),
        ("https://user:sec ret@example.org:8080", "example.org:8080"),
        ("ftp://user:secret@ftp.example.org/pub/a.bed", "a.bed"),
        ("https://example.org/a?next=ftp://user:secret@ftp.example.org", "ftp.example.org"),
        ("https://example.org/a?next=ftp://user:se?cret@ftp.example.org", "ftp.example.org"),
        ("https://example.org/a#ftp://user:se#cret@ftp.example.org", "ftp.example.org"),
        ("https://example.org/a?next=ftp://user:sec ret@ftp.example.org", "ftp.example.org"),
        ("https://example.org/dir/user@file.txt", "user@file.txt"),
        ("https://example.org/a?next=//user:secret@ftp.example.org", "ftp.example.org"),
        ("https://example.org/a?next=///user:secret@ftp.example.org", "ftp.example.org"),
        ("https://example.org/a?next=ftp:///user:secret@ftp.example.org", "ftp.example.org"),
        ("https:///user:secret@example.org", "example.org"),
        ("file:///data/a.bed", "a.bed"),
        # A "//" in a path starts an authority too, so a name after it loses the part up to its "@".
        ("https://example.org/a//b@c.txt", "c.txt"),
    ],
)
def test_name_from_url(url, expected):
    assert util.name_from_url(url) == expected
