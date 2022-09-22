"""
Classes for generating HTML forms
"""

import logging

from galaxy.util import asbool

log = logging.getLogger(__name__)


class BaseField:
    def __init__(self, name, value=None, label=None, **kwds):
        self.name = name
        self.label = label
        self.value = value
        self.disabled = kwds.get("disabled", False)
        if "optional" in kwds:
            self.optional = asbool(kwds.get("optional"))
        else:
            self.optional = kwds.get("required", "optional") == "optional"
        self.help = kwds.get("helptext")

    def to_dict(self):
        return {
            "name": self.name,
            "label": self.label,
            "disabled": self.disabled,
            "optional": self.optional,
            "value": self.value,
            "help": self.help,
        }


class TextField(BaseField):
    """
    A standard text input box.
    """

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "text"
        return d


class PasswordField(BaseField):
    """
    A password input box. text appears as "******"
    """

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "password"
        return d


class TextArea(BaseField):
    """
    A standard text area box.
    """

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "text"
        d["area"] = True
        return d


class CheckboxField(BaseField):
    """
    A checkbox (boolean input)
    """

    @staticmethod
    def is_checked(value):
        if value in [True, "True", "true"]:
            return True
        return False

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "boolean"
        return d


class SelectField(BaseField):
    """
    A select field.
    """

    def __init__(
        self,
        name,
        multiple=None,
        display=None,
        field_id=None,
        value=None,
        selectlist=None,
        refresh_on_change=False,
        **kwds,
    ):
        super().__init__(name, value, **kwds)
        self.field_id = field_id
        self.multiple = multiple or False
        self.refresh_on_change = refresh_on_change
        self.selectlist = selectlist or []
        self.options = list()
        if display == "checkboxes":
            assert multiple, "Checkbox display only supported for multiple select"
        elif display == "radio":
            assert not (multiple), "Radio display only supported for single select"
        elif display is not None:
            raise Exception(f"Unknown display type: {display}")
        self.display = display

    def add_option(self, text, value, selected=False):
        self.options.append((text, value, selected))

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "select"
        d["display"] = self.display
        d["multiple"] = self.multiple
        d["data"] = []
        for value in self.selectlist:
            d["data"].append({"label": value, "value": value})
        d["options"] = [{"label": t[0], "value": t[1]} for t in self.options]
        return d


class AddressField(BaseField):
    @staticmethod
    def fields():
        return [
            ("desc", "Short address description", "Required"),
            ("name", "Name", ""),
            ("institution", "Institution", ""),
            ("address", "Address", ""),
            ("city", "City", ""),
            ("state", "State/Province/Region", ""),
            ("postal_code", "Postal Code", ""),
            ("country", "Country", ""),
            ("phone", "Phone", ""),
        ]

    def __init__(self, name, user=None, value=None, security=None, **kwds):
        super().__init__(name, value, **kwds)
        self.user = user
        self.security = security

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "select"
        d["data"] = []
        if self.user and self.security:
            for a in self.user.addresses:
                if not a.deleted:
                    d["data"].append({"label": a.desc, "value": self.security.encode_id(a.id)})
        return d


class WorkflowField(BaseField):
    def __init__(self, name, user=None, value=None, security=None, **kwds):
        super().__init__(name, value, **kwds)
        self.user = user
        self.value = value
        self.security = security

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "select"
        d["data"] = []
        if self.user and self.security:
            for a in self.user.stored_workflows:
                if not a.deleted:
                    d["data"].append({"label": a.name, "value": self.security.encode_id(a.id)})
        return d


class WorkflowMappingField(BaseField):
    def __init__(self, name, user=None, value=None, **kwds):
        super().__init__(name, value, **kwds)
        self.user = user


class HistoryField(BaseField):
    def __init__(self, name, user=None, value=None, security=None, **kwds):
        super().__init__(name, value, **kwds)
        self.user = user
        self.value = value
        self.security = security

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "select"
        d["data"] = [{"label": "New History", "value": "new"}]
        if self.user and self.security:
            for a in self.user.histories:
                if not a.deleted:
                    d["data"].append({"label": a.name, "value": self.security.encode_id(a.id)})
        return d
