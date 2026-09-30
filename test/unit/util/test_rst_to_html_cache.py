from galaxy.util.rst_to_html import (
    _cached_publish,
    rst_to_html,
)


def test_cache_is_bounded():
    assert _cached_publish.cache_info().maxsize is not None


def test_uncached_text_is_not_cached():
    before = _cached_publish.cache_info().currsize
    html = rst_to_html("**uncached text**", cache=False)
    assert "<strong>uncached text</strong>" in html
    assert _cached_publish.cache_info().currsize == before


def test_text_is_cached_by_default():
    rst_to_html("**cached text**")
    hits = _cached_publish.cache_info().hits
    rst_to_html("**cached text**")
    assert _cached_publish.cache_info().hits == hits + 1
