"""
Classes for generating HTML forms
"""
from __future__ import print_function

import logging
from cgi import escape

from six import string_types

from galaxy.util import (
    asbool,
    restore_text,
    unicodify
)

log = logging.getLogger(__name__)


class BaseField(object):
    def __init__(self, name, value=None, label=None, **kwds):
        self.name = name
        self.label = label
        self.value = value
        self.disabled = kwds.get('disabled', False)
        if 'optional' in kwds:
            self.optional = asbool(kwds.get('optional'))
        else:
            self.optional = kwds.get('required', 'optional') == 'optional'
        self.help = kwds.get('helptext')

    def to_dict(self):
        return {
            'name'      : self.name,
            'label'     : self.label,
            'disabled'  : self.disabled,
            'optional'  : self.optional,
            'value'     : self.value,
            'help'      : self.help
        }


class TextField(BaseField):
    """
    A standard text input box.
    """
    def to_dict(self):
        d = super(TextField, self).to_dict()
        d['type'] = 'text'
        return d


class PasswordField(BaseField):
    """
    A password input box. text appears as "******"
    """
    def to_dict(self):
        d = super(PasswordField, self).to_dict()
        d['type'] = 'password'
        return d


class TextArea(BaseField):
    """
    A standard text area box.
    """
    def to_dict(self):
        d = super(TextArea, self).to_dict()
        d['type'] = 'text'
        d['area'] = True
        return d


class CheckboxField(BaseField):
    """
    A checkbox (boolean input)
    """

    def __init__(self, name, checked=None, refresh_on_change=False, refresh_on_change_values=None, value=None, **kwds):
        super(CheckboxField, self).__init__(name, value, **kwds)
        self.name = name
        self.checked = (checked is True) or (isinstance(checked, string_types) and (checked.lower() in ("yes", "true", "on")))

    @staticmethod
    def is_checked(value):
        if value in [True, "true"]:
            return True
        return isinstance(value, list) and ('__CHECKED__' in value or len(value) == 2)

    def set_checked(self, value):
        if isinstance(value, string_types):
            self.checked = value.lower() in ["yes", "true", "on"]
        else:
            self.checked = value

    def to_dict(self):
        d = super(CheckboxField, self).to_dict()
        d['type'] = 'boolean'
        return d


class FileField(BaseField):
    """
    A file upload input.
    """

    def __init__(self, name, value=None, ajax=False, **kwds):
        super(FileField, self).__init__(name, value, **kwds)
        self.name = name
        self.ajax = ajax
        self.value = value


class GenomespaceFileField(BaseField):
    """
    A genomspace file browser field.
    """
    def __init__(self, name, value=None):
        self.name = name
        self.value = value or ""

    def to_dict(self):
        return dict(name=self.name,
                    token_field=self.token_field)


class HiddenField(BaseField):
    """
    A hidden field.
    """

    def __init__(self, name, value=None, **kwds):
        super(HiddenField, self).__init__(name, value, **kwds)
        self.name = name
        self.value = value or ""

    def to_dict(self):
        d = super(HiddenField, self).to_dict()
        d['type'] = 'hidden'
        d['hidden'] = True
        return d


class SelectField(BaseField):
    """
    A select field.
    """

    def __init__(self, name, multiple=None, display=None, refresh_on_change=False, refresh_on_change_values=None, size=None, field_id=None, value=None, selectlist=None, **kwds):
        super(SelectField, self).__init__(name, value, **kwds)
        self.name = name
        self.field_id = field_id
        self.multiple = multiple or False
        self.selectlist = selectlist or []
        self.value = value
        self.size = size
        self.options = list()
        if display == "checkboxes":
            assert multiple, "Checkbox display only supported for multiple select"
        elif display == "radio":
            assert not(multiple), "Radio display only supported for single select"
        elif display is not None:
            raise Exception("Unknown display type: %s" % display)
        self.display = display
        self.refresh_on_change = refresh_on_change
        self.refresh_on_change_values = refresh_on_change_values or []
        if self.refresh_on_change:
            self.refresh_on_change_text = ' refresh_on_change="true"'
            if self.refresh_on_change_values:
                self.refresh_on_change_text = '%s refresh_on_change_values="%s"' % (self.refresh_on_change_text, escape(",".join(self.refresh_on_change_values), quote=True))
        else:
            self.refresh_on_change_text = ''

    def add_option(self, text, value, selected=False):
        self.options.append((text, value, selected))

    def get_selected(self, return_label=False, return_value=False, multi=False):
        '''
        Return the currently selected option's label, value or both as a tuple.  For
        multi-select lists, a list is returned.
        '''
        if multi:
            selected_options = []
        for label, value, selected in self.options:
            if selected:
                if return_label and return_value:
                    if multi:
                        selected_options.append((label, value))
                    else:
                        return (label, value)
                elif return_label:
                    if multi:
                        selected_options.append(label)
                    else:
                        return label
                elif return_value:
                    if multi:
                        selected_options.append(value)
                    else:
                        return value
        if multi:
            return selected_options
        return None

    def to_dict(self):
        d = super(SelectField, self).to_dict()
        d['type'] = 'select'
        d['display'] = self.display
        d['multiple'] = self.multiple
        d['data'] = []
        for value in self.selectlist:
            d['data'].append({'label': value, 'value': value})
        return d


class AddressField(BaseField):
    @staticmethod
    def fields():
        return [("desc", "Short address description", "Required"),
                ("name", "Name", ""),
                ("institution", "Institution", ""),
                ("address", "Address", ""),
                ("city", "City", ""),
                ("state", "State/Province/Region", ""),
                ("postal_code", "Postal Code", ""),
                ("country", "Country", ""),
                ("phone", "Phone", "")]

    def __init__(self, name, user=None, value=None, params=None, security=None, **kwds):
        super(AddressField, self).__init__(name, value, **kwds)
        self.user = user
        self.security = security
        self.select_address = None
        self.params = params

    def to_dict(self):
        d = super(AddressField, self).to_dict()
        d['type'] = 'select'
        d['data'] = []
        if self.user and self.security:
            for a in self.user.addresses:
                if not a.deleted:
                    d['data'].append({'label': a.desc, 'value': self.security.encode_id(a.id)})
        return d


class WorkflowField(BaseField):
    def __init__(self, name, user=None, value=None, params=None, security=None, **kwds):
        super(WorkflowField, self).__init__(name, value, **kwds)
        self.name = name
        self.user = user
        self.value = value
        self.security = security
        self.select_workflow = None
        self.params = params

    def to_dict(self):
        d = super(WorkflowField, self).to_dict()
        d['type'] = 'select'
        d['data'] = []
        if self.user and self.security:
            for a in self.user.stored_workflows:
                if not a.deleted:
                    d['data'].append({'label': a.name, 'value': self.security.encode_id(a.id)})
        return d


class WorkflowMappingField(BaseField):
    def __init__(self, name, user=None, value=None, params=None, **kwd):
        # DBTODO integrate this with the new __build_workflow approach in requests_common.  As it is, not particularly useful.
        self.name = name
        self.user = user
        self.value = value
        self.select_workflow = None
        self.params = params
        self.workflow_inputs = []


class HistoryField(BaseField):
    def __init__(self, name, user=None, value=None, params=None, security=None, **kwds):
        super(HistoryField, self).__init__(name, value, **kwds)
        self.name = name
        self.user = user
        self.value = value
        self.security = security
        self.select_history = None
        self.params = params

    def to_dict(self):
        d = super(HistoryField, self).to_dict()
        d['type'] = 'select'
        d['data'] = [{'label': 'New History', 'value': 'new'}]
        if self.user and self.security:
            for a in self.user.histories:
                if not a.deleted:
                    d['data'].append({'label': a.name, 'value': self.security.encode_id(a.id)})
        return d


def get_suite():
    """Get unittest suite for this module"""
    import doctest
    import sys
    return doctest.DocTestSuite(sys.modules[__name__])
