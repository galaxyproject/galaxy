import re
import string
from abc import (
    ABCMeta,
    abstractproperty,
)

import six
from selenium.webdriver.common.by import By

from galaxy.util.bunch import Bunch


@six.add_metaclass(ABCMeta)
class Target(object):

    @abstractproperty
    def description(self):
        """Return a plain-text description of the browser target for logging/messages."""

    @abstractproperty
    def element_locator(self):
        """Return a (by, selector) Selenium elment locator tuple for this selector."""


class SelectorTemplate(Target):

    def __init__(self, selector, selector_type, children=None, kwds=None, with_classes=None):
        self._selector = selector
        self.selector_type = selector_type
        self._children = children or {}
        self.__kwds = kwds or {}
        self.with_classes = with_classes or []

    @staticmethod
    def from_dict(raw_value, children=None):
        children = children or {}
        if isinstance(raw_value, dict):
            return SelectorTemplate(raw_value["selector"], raw_value.get("type", "css"), children=children)
        else:
            return SelectorTemplate(raw_value, "css", children=children)

    def with_class(self, class_):
        assert self.selector_type == "css"
        return SelectorTemplate(self._selector, self.selector_type, kwds=self.__kwds, with_classes=self.with_classes + [class_], children=self._children)

    def descendant(self, has_selector):
        assert self.selector_type == "css"
        if hasattr(has_selector, "selector"):
            selector = has_selector.selector
        else:
            selector = has_selector

        return SelectorTemplate(self.selector + " " + selector, self.selector_type, kwds=self.__kwds, children=self._children)

    def __call__(self, **kwds):
        new_kwds = self.__kwds.copy()
        new_kwds.update(**kwds)
        return SelectorTemplate(self._selector, self.selector_type, kwds=new_kwds, with_classes=self.with_classes, children=self._children)

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

    def __getattr__(self, name):
        if name in self._children:
            return self._children[name](**{"_": self.selector})
        else:
            raise KeyError("Could not find child [%s] in %s" % (name, self._children))

    __getitem__ = __getattr__


class Label(Target):

    def __init__(self, text):
        self.text = text

    @property
    def description(self):
        return "Link text [%s]" % self.text

    @property
    def element_locator(self):
        return (By.LINK_TEXT, self.text)


class Text(Target):

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
        self._name = name
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
                base_selector = None
                if "_" in value:
                    base_selector = value["_"]
                    del value["_"]

                for selector_key, selector_value in value.items():
                    selectors[selector_key] = SelectorTemplate.from_dict(selector_value)

                if base_selector:
                    selectors["_"] = SelectorTemplate.from_dict(base_selector, children=selectors)

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
        if attr in self._sub_components:
            return self._sub_components[attr]
        elif attr in self._selectors:
            return self._selectors[attr]
        elif attr in self._labels:
            return self._labels[attr]
        elif attr in self._text:
            return self._text[attr]
        else:
            raise Exception("Failed to find referenced sub-component/selector/label/text [%s]" % attr)

    __getitem__ = __getattr__

    def __str__(self):
        return "Component[%s]" % self._name
