"""Utilities for using sizzle (jQuery-style) selectors with Selenium."""

import re

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait

SIZZLE_LOAD_TIMEOUT = 5
SIZZLE_URL = "//cdnjs.cloudflare.com/ajax/libs/sizzle/1.10.18/sizzle.js"


def sizzle_selector_clickable(selector):
    def ec(driver):
        elements = find_elements_by_sizzle(driver, selector)
        if not elements:
            return False
        element = elements[0]
        if element.is_displayed() and element.is_enabled():
            return element
        else:
            return None

    return ec


def sizzle_presence_of_selector(selector):
    def ec(driver):
        elements = find_elements_by_sizzle(driver, selector)
        if not elements:
            return False
        element = elements[0]
        if element.is_displayed():
            return element
        else:
            return None

    return ec


def find_element_by_sizzle(driver, sizzle_selector):
    """
    Finds an element by sizzle selector.
    :Args:
     - sizzle_selector: The sizzle selector to use when finding element.
    :Usage:
        driver.find_element_by_sizzle('#foo')
    """
    elements = driver.find_elements_by_sizzle(sizzle_selector)
    if elements:
        return elements[0]
    else:
        raise NoSuchElementException(
            "Unable to locate element by Sizzle: {selector}".format(selector=sizzle_selector)
        )


def find_elements_by_sizzle(driver, sizzle_selector):
    """
    Finds elements by sizzle selector.
    :Args:
     - sizzle_selector: The sizzle selector to use when finding elements.
    :Usage:
        driver.find_elements_by_sizzle('.foo')
    """
    if not _is_sizzle_loaded(driver):
        _inject_sizzle(driver, SIZZLE_URL, SIZZLE_LOAD_TIMEOUT)
    elements = driver.execute_script(_make_sizzle_string(sizzle_selector))
    return elements


def _inject_sizzle(driver, sizzle_url, timeout):
    script = """
        var _s = document.createElement("script");
        _s.type = "text/javascript";
        _s.src = "{src}";
        var _h = document.getElementsByTagName("head")[0];
        _h.appendChild(_s);
    """.format(src=sizzle_url)
    driver.execute_script(script)
    wait = WebDriverWait(driver, timeout)
    wait.until(lambda d: _is_sizzle_loaded(d),
               "Can't inject Sizzle in {timeout} seconds".format(timeout=timeout))


def _is_sizzle_loaded(driver):
    script = "return typeof(Sizzle) != \"undefined\";"
    return driver.execute_script(script)


def _make_sizzle_string(sizzle_selector):
    try:
        selector = sizzle_selector.decode("utf-8")
    except (AttributeError, UnicodeEncodeError):
        selector = sizzle_selector
    return u"return Sizzle(\"{selector}\");".format(selector=re.escape(selector))


__all__ = (
    "sizzle_selector_clickable",
    "sizzle_presence_of_selector",
    "find_element_by_sizzle",
    "find_elements_by_sizzle",
)
