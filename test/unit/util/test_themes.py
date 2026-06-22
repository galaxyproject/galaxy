from galaxy.util.themes import (
    BUILTIN_THEMES,
    flatten_theme,
    flattened_builtin_themes,
)


def test_flatten_theme_nests_with_double_dash_prefix():
    flat = flatten_theme({"masthead": {"color": "#000", "text": {"color": "#fff"}}})
    assert flat["--masthead-color"] == "#000"
    assert flat["--masthead-text-color"] == "#fff"


def test_flatten_theme_emits_content_css_variables():
    flat = flatten_theme({"content": {"background": "#2c3143", "text": "#f0f2f8"}})
    assert flat["--content-background"] == "#2c3143"
    assert flat["--content-text"] == "#f0f2f8"


def test_flatten_theme_skips_non_str_non_dict_values():
    # ``None`` (e.g. ``img-secondary: null``) is neither str nor dict and is dropped.
    flat = flatten_theme({"logo": {"img": "/x.svg", "img-secondary": None}})
    assert flat == {"--logo-img": "/x.svg"}


def test_builtin_orbit_theme_exposes_content_vars():
    flat = flattened_builtin_themes()
    assert "orbit" in flat
    orbit = flat["orbit"]
    # Content surface vars the page/markdown render stack consumes.
    assert orbit["--content-background"] == "#2c3143"
    assert orbit["--content-text"] == "#f0f2f8"
    assert orbit["--content-link"] == "#ffd700"
    # Still a complete theme (masthead present) so it is normally selectable.
    assert orbit["--masthead-color"] == "#2c3143"


def test_builtin_themes_are_nested_form():
    # Source-of-truth constant stays nested; flatten happens on demand.
    assert isinstance(BUILTIN_THEMES["orbit"]["content"], dict)
