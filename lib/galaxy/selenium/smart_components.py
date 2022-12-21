from selenium.webdriver.support.select import Select

from galaxy.navigation.components import (
    Component,
    Target,
)


class SmartComponent:
    """Wrap a Component with driver aware methods.

    Adapts Galaxy's component locators more tightly to Selenium - including a Selenium
    runtime. Allows smarter selectors that know how to wait for themselves, test themselves,
    click themselves, etc.... More "magic", but much cleaner usage.
    """

    def __init__(self, component, has_driver):
        self._component = component
        self._has_driver = has_driver

    def __getattr__(self, name):
        return self._wrap(getattr(self._component, name))

    def __getitem__(self, name):
        return self._wrap(self._component[name])

    def _wrap(self, simple_object):
        if isinstance(simple_object, Component):
            return SmartComponent(simple_object, self._has_driver)
        elif isinstance(simple_object, Target):
            return SmartTarget(simple_object, self._has_driver)
        else:
            return simple_object


class SmartTarget:
    """Wrap a Target with driver aware methods."""

    def __init__(self, target, has_driver):
        self._target = target
        self._has_driver = has_driver

    def __call__(self, *args, **kwds):
        return self._wrap(self._target(*args[:], **kwds.copy()))

    def __getattr__(self, name):
        return self._wrap(getattr(self._target, name))

    def __getitem__(self, name):
        return self._wrap(self._target[name])

    def _wrap(self, simple_object):
        if isinstance(simple_object, Target):
            return SmartTarget(simple_object, self._has_driver)
        else:
            return simple_object

    def all(self):
        return self._has_driver.driver.find_elements(*self._target.element_locator)

    def wait_for_element_count_of_at_least(self, n: int, **kwds):
        self._has_driver.wait_for_element_count_of_at_least(self._target, n, **kwds)

    def wait_for_and_click(self, **kwds):
        return self._has_driver.wait_for_and_click(self._target, **kwds)

    def wait_for_visible(self, **kwds):
        return self._has_driver.wait_for_visible(self._target, **kwds)

    def wait_for_select(self, **kwds):
        return Select(self.wait_for_visible(**kwds))

    def wait_for_clickable(self, **kwds):
        return self._has_driver.wait_for_clickable(self._target, **kwds)

    def wait_for_text(self, **kwds):
        return self._has_driver.wait_for_visible(self._target, **kwds).text

    def wait_for_value(self, **kwds):
        return self._has_driver.wait_for_visible(self._target, **kwds).get_attribute("value")

    @property
    def is_displayed(self):
        return self._has_driver.is_displayed(self._target)

    @property
    def is_absent(self):
        return self._has_driver.element_absent(self._target)

    def wait_for_absent_or_hidden(self, **kwds):
        self._has_driver.wait_for_absent_or_hidden(self._target, **kwds)

    def wait_for_absent(self, **kwds):
        self._has_driver.wait_for_absent(self._target, **kwds)

    def wait_for_present(self, **kwds):
        return self._has_driver.wait_for_present(self._target, **kwds)

    def assert_absent(self, **kwds):
        self._has_driver.assert_absent(self._target, **kwds)

    def assert_absent_or_hidden(self, **kwds):
        self._has_driver.assert_absent_or_hidden(self._target, **kwds)

    def assert_absent_or_hidden_after_transitions(self, **kwds):
        self._has_driver.assert_absent_or_hidden_after_transitions(self._target, **kwds)

    def assert_disabled(self, **kwds):
        self._has_driver.assert_disabled(self._target, **kwds)

    def has_class(self, class_name):
        classes_str = self._has_driver.driver.find_element(*self._target.element_locator).get_attribute("class") or ""
        return class_name in classes_str.split(" ")

    def wait_for_and_send_keys(self, *text):
        self.wait_for_visible().send_keys(*text)
