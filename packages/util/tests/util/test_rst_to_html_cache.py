from galaxy.util.rst_to_html import rst_to_html


def test_cache_is_bounded():
    assert rst_to_html.cache_info().maxsize is not None


def test_text_is_cached():
    rst_to_html("**cached text**")
    hits = rst_to_html.cache_info().hits
    rst_to_html("**cached text**")
    assert rst_to_html.cache_info().hits == hits + 1
