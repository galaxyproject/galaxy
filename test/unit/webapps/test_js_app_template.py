"""
Unit tests for analytics snippets rendered by ``templates/js-app.mako``.

These exercise the ``config_matomo_analytics`` def in isolation so no full
application/request context is required.
"""

import os

from mako.template import Template

from galaxy.util import galaxy_directory

JS_APP_TEMPLATE = os.path.join(galaxy_directory(), "templates", "js-app.mako")

DISABLE_COOKIES = "_paq.push(['disableCookies']);"
TRACK_PAGE_VIEW = "_paq.push(['trackPageView']);"


def _render_matomo(matomo_disable_cookies):
    template = Template(filename=JS_APP_TEMPLATE)
    matomo_def = template.get_def("config_matomo_analytics")
    return matomo_def.render(
        matomo_server="https://matomo.example.org",
        matomo_site_id="42",
        matomo_disable_cookies=matomo_disable_cookies,
    )


def test_matomo_cookieless_enabled_emits_disable_cookies():
    rendered = _render_matomo(matomo_disable_cookies=True)
    # The cookieless call must be present ...
    assert DISABLE_COOKIES in rendered
    assert TRACK_PAGE_VIEW in rendered
    # ... and must come *before* trackPageView, per
    # https://matomo.org/faq/general/faq_157/.
    assert rendered.index(DISABLE_COOKIES) < rendered.index(TRACK_PAGE_VIEW)


def test_matomo_cookieless_disabled_omits_disable_cookies():
    rendered = _render_matomo(matomo_disable_cookies=False)
    assert DISABLE_COOKIES not in rendered
    # Tracking itself is unaffected.
    assert TRACK_PAGE_VIEW in rendered
