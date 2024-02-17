import abc
import re
import string
from enum import Enum
from typing import (
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

from galaxy.util.bunch import Bunch


class ComponentBy(str, Enum):
    ID = "id"
    XPATH = "xpath"
    CSS_SELECTOR = "css selector"
    LABEL = "label"
    TEXT = "text"


class LocatorT(NamedTuple):
    by: ComponentBy
    locator: str

    @property
    def selenium_by(self) -> str:
        by = self.by
        if by == ComponentBy.LABEL:
            return "link text"
        elif by == ComponentBy.TEXT:
            return "partial link text"
        else:
            return str(by.value)


class Target(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Return a plain-text description of the browser target for logging/messages."""

    @property
    @abc.abstractmethod
    def component_locator(self) -> LocatorT:
        """Return a (by, selector) Selenium element locator tuple for this selector."""

    @property
    def selenium_locator(self) -> Tuple[str, str]:
        element_locator: LocatorT = self.component_locator
        return (element_locator.selenium_by, element_locator.locator)

    @property
    def element_locator(self):
        return self.selenium_locator


class SelectorTemplate(Target):
    def __init__(
        self,
        selector: Union[str, List[str]],
        selector_type: str,
        children=None,
        kwds=None,
        with_classes=None,
        with_data=None,
    ):
        if selector_type == "data-description":
            selector_type = "css"
            selector = f'[data-description="{selector}"]'
        self._selector = selector
        self.selector_type = selector_type
        self._children = children or {}
        self.__kwds = kwds or {}
        self.with_classes = with_classes or []
        self._with_data = with_data or {}

    @staticmethod
    def from_dict(raw_value, children=None):
        children = children or {}
        if isinstance(raw_value, dict):
            return SelectorTemplate(raw_value["selector"], raw_value.get("type", "css"), children=children)
        else:
            return SelectorTemplate(raw_value, "css", children=children)

    def with_class(self, class_):
        assert self.selector_type == "css"
        return SelectorTemplate(
            self._selector,
            self.selector_type,
            kwds=self.__kwds,
            with_classes=self.with_classes + [class_],
            with_data=self._with_data.copy(),
            children=self._children,
        )

    def with_data(self, key, value):
        assert self.selector_type == "css"
        with_data = self._with_data.copy()
        with_data[key] = value
        return SelectorTemplate(
            self._selector,
            self.selector_type,
            kwds=self.__kwds,
            with_classes=self.with_classes,
            with_data=with_data,
            children=self._children,
        )

    def descendant(self, has_selector) -> "SelectorTemplate":
        assert self.selector_type == "css"
        if hasattr(has_selector, "selector"):
            selector = has_selector.selector
        else:
            selector = has_selector

        return SelectorTemplate(
            f"{self.selector} {selector}", self.selector_type, kwds=self.__kwds, children=self._children
        )

    def __call__(self, **kwds):
        new_kwds = self.__kwds.copy()
        new_kwds.update(**kwds)
        return SelectorTemplate(
            self._selector, self.selector_type, kwds=new_kwds, with_classes=self.with_classes, children=self._children
        )

    @property
    def description(self) -> str:
        if self.selector_type == "css":
            template = "CSS selector [%s]"
        elif self.selector_type == "xpath":
            template = "XPATH selector [%s]"
        elif self.selector_type == "id":
            template = "DOM element with id [%s]"
        return template % self.selector

    @property
    def selector(self) -> str:
        raw_selector = self._selector
        if self.__kwds is not None:
            if isinstance(raw_selector, list):
                selector = None
                last_error = None
                for raw_selector_str in raw_selector:
                    try:
                        selector = string.Template(raw_selector_str).substitute(self.__kwds)
                        break
                    except KeyError as e:
                        last_error = e
                if selector is None:
                    assert last_error
                    raise last_error
            else:
                selector = string.Template(raw_selector).substitute(self.__kwds)

        assert selector
        selector = selector + "".join(f".{c}" for c in self.with_classes)
        if self._with_data:
            for key, value in self._with_data.items():
                selector = selector + f'[data-{key}="{value}"]'
        return selector

    @property
    def component_locator(self) -> LocatorT:
        if self.selector_type == "css":
            by = ComponentBy.CSS_SELECTOR
        elif self.selector_type == "xpath":
            by = ComponentBy.XPATH
        elif self.selector_type == "id":
            by = ComponentBy.ID
        else:
            raise Exception(f"Unknown selector type {self.selector_type}")
        return LocatorT(by, self.selector)

    @property
    def as_css_class(self) -> str:
        assert self.selector_type == "css"
        selector = self._selector
        assert isinstance(selector, str)
        assert re.compile(r"\.\w+").match(selector)
        return selector[1:]

    def resolve_component_locator(self, path: Optional[str] = None) -> LocatorT:
        if path:
            return self[path].component_locator
        else:
            return self.component_locator

    def __getattr__(self, name):
        if name in self._children:
            return self._children[name](**{"_": self.selector})
        else:
            raise AttributeError(f"Could not find child [{name}] in {self._children}")

    __getitem__ = __getattr__


class Label(Target):
    def __init__(self, text):
        self.text = text

    @property
    def description(self):
        return f"Link text [{self.text}]"

    @property
    def component_locator(self) -> LocatorT:
        return LocatorT(ComponentBy.LABEL, self.text)


class Text(Target):
    def __init__(self, text):
        self.text = text

    @property
    def description(self):
        return f"Text containing [{self.text}]"

    @property
    def component_locator(self) -> LocatorT:
        return LocatorT(ComponentBy.TEXT, self.text)


HasText = Union[Label, Text]

CALL_ARGUMENTS_RE = re.compile(r"(?P<SUBCOMPONENT>[^.(]*)(\((?P<ARGS>[^)]+)\))?(?:\.(?P<REST>.*))?")


class Component:
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
            raise Exception(f"No _ selector for [{self}]")

    def resolve_component_locator(self, path: Optional[str] = None) -> LocatorT:
        if not path:
            return self._selectors["_"].resolve_component_locator()

        def arguments() -> Tuple[str, Optional[Dict[str, str]], Optional[str]]:
            assert path
            if match := CALL_ARGUMENTS_RE.match(path):
                component_name = match.group("SUBCOMPONENT")
                expression = match.group("ARGS")
                rest = match.group("REST")
                if expression:
                    parts = expression.split(",")
                    parameters = {}
                    for part in parts:
                        key, val = part.split("=", 1)
                        parameters[key.strip()] = val.strip()
                    return component_name, parameters, rest
                return component_name, None, rest
            elif "." in path:
                component_name, rest = path.split(".", 1)
            else:
                component_name = path
                rest = None
            return component_name, None, rest

        component_name, parameters, rest = arguments()
        if not rest:
            if parameters:
                return getattr(self, component_name)(**parameters).resolve_component_locator()
            else:
                return getattr(self, component_name).resolve_component_locator()
        else:
            if parameters:
                return getattr(self, component_name)(**parameters).resolve_component_locator(rest)
            else:
                return getattr(self, component_name).resolve_component_locator(rest)

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
            raise AttributeError(f"Failed to find referenced sub-component/selector/label/text [{attr}]")

    def __call__(self, **kwds):
        return self._selectors["_"](**kwds)

    __getitem__ = __getattr__

    def __str__(self):
        return f"Component[{self._name}]"
