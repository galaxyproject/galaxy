import re
import string

import yaml

from pkg_resources import resource_string

from selenium.webdriver.common.by import By

from galaxy.util.bunch import Bunch


old_data_yaml = resource_string(__name__, 'navigation-data.yml').decode("UTF-8")
NAVIGATION_DATA = yaml.safe_load(old_data_yaml)
new_data_yaml = resource_string(__name__, 'navigation.yml').decode("UTF-8")
NAVIGATION_RAW = yaml.safe_load(new_data_yaml)


class SelectorTemplate(object):

    def __init__(self, selector, selector_type, kwds=None, with_classes=None):
        self._selector = selector
        self.selector_type = selector_type
        self.__kwds = kwds or {}
        self.with_classes = with_classes or []

    @staticmethod
    def from_dict(raw_value):
        if isinstance(raw_value, dict):
            return SelectorTemplate(raw_value["selector"], raw_value.get("type", "css"))
        else:
            return SelectorTemplate(raw_value, "css")

    def with_class(self, class_):
        assert self.selector_type == "css"
        return SelectorTemplate(self._selector, self.selector_type, kwds=self.__kwds, with_classes=self.with_classes + [class_])

    def __call__(self, **kwds):
        new_kwds = self.__kwds
        new_kwds.update(**kwds)
        return SelectorTemplate(self._selector, self.selector_type, kwds=new_kwds, with_classes=self.with_classes)

    @property
    def description(self):
        if self.selector_type == "css":
            template = "CSS selector [%s]"
        elif self.selector_type == "xpath":
            template = "XPATH selector [%s]"
        elif self.selector_type == "id":
            template = "DOM element with id [%s]"
        return template % self.selector

    @property
    def selector(self):
        selector = self._selector
        if self.__kwds is not None:
            selector = string.Template(selector).substitute(self.__kwds)
        selector = selector + "".join([".%s" % c for c in self.with_classes])
        return selector

    @property
    def element_locator(self):
        if self.selector_type == "css":
            by = By.CSS_SELECTOR
        elif self.selector_type == "xpath":
            by = By.XPATH
        elif self.selector_type == "id":
            by = By.ID
        else:
            raise Exception("Unknown selector type")
        return (by, self.selector)

    @property
    def as_css_class(self):
        assert self.selector_type == "css"
        assert re.compile(r"\.\w+").match(self._selector)
        return self._selector[1:]


class Label(object):

    def __init__(self, text):
        self.text = text

    @property
    def description(self):
        return "Link text [%s]" % self.text

    @property
    def element_locator(self):
        return (By.LINK_TEXT, self.text)


class Text(object):

    def __init__(self, text):
        self.text = text

    @property
    def description(self):
        return "Text containing [%s]" % self.text

    @property
    def element_locator(self):
        return (By.PARTIAL_LINK_TEXT, self.text)


class Component(object):

    def __init__(self, name, sub_components, selectors, labels, text):
        self.name = name
        self._sub_components = sub_components
        self._selectors = selectors
        self._labels = labels
        self._text = text

        self.selectors = Bunch(**self._selectors)
        self.labels = Bunch(**self._labels)
        self.text = Bunch(**self._text)

    @property
    def selector(self):
        if "_" in self._selectors:
            return self._selectors["_"]
        else:
            raise Exception("No _ selector for [%s]" % self)

    @staticmethod
    def from_dict(name, raw_value):
        selectors = {}
        labels = {}
        text = {}
        sub_components = {}

        for key, value in raw_value.items():
            if key == "selectors":
                for selector_key, selector_value in value.items():
                    selectors[selector_key] = SelectorTemplate.from_dict(selector_value)
            elif key == "labels":
                for label_key, label_value in value.items():
                    labels[label_key] = Label(label_value)
            elif key == "text":
                for text_key, text_value in value.items():
                    text[text_key] = Text(text_value)
            else:
                component = Component.from_dict(key, value)
                sub_components[key] = component

        return Component(name, sub_components, selectors, labels, text)

    def __getattr__(self, attr):
        return self._sub_components[attr]

    def __str__(self):
        return "Component[%s]" % self.name


NAVIGATION = Component.from_dict("root", NAVIGATION_RAW)
