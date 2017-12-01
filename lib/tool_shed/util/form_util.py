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

    def get_html(self, prefix=""):
        """Returns the html widget corresponding to the parameter"""
        raise TypeError("Abstract Method")

    def get_disabled_str(self, disabled=False):
        if disabled:
            return ' disabled="disabled"'
        else:
            return ''


class CheckboxField(BaseField):
    """
    A checkbox (boolean input)

    >>> print(CheckboxField( "foo" ).get_html())
    <input type="checkbox" id="foo" name="foo" value="__CHECKED__"><input type="hidden" name="foo" value="__NOTHING__">
    >>> print(CheckboxField( "bar", checked="yes" ).get_html())
    <input type="checkbox" id="bar" name="bar" value="__CHECKED__" checked="checked"><input type="hidden" name="bar" value="__NOTHING__">
    """

    def __init__(self, name, checked=None, refresh_on_change=False, refresh_on_change_values=None, value=None, **kwds):
        super(CheckboxField, self).__init__(name, value, **kwds)
        self.name = name
        self.checked = (checked is True) or (isinstance(checked, string_types) and (checked.lower() in ("yes", "true", "on")))
        self.refresh_on_change = refresh_on_change
        self.refresh_on_change_values = refresh_on_change_values or []
        if self.refresh_on_change:
            self.refresh_on_change_text = ' refresh_on_change="true" '
            if self.refresh_on_change_values:
                self.refresh_on_change_text = '%s refresh_on_change_values="%s" ' % (self.refresh_on_change_text, ",".join(self.refresh_on_change_values))
        else:
            self.refresh_on_change_text = ''

    def get_html(self, prefix="", disabled=False):
        if self.checked:
            checked_text = ' checked="checked"'
        else:
            checked_text = ''
        id_name = prefix + self.name
        return unicodify('<input type="checkbox" id="%s" name="%s" value="__CHECKED__"%s%s%s><input type="hidden" name="%s" value="__NOTHING__"%s>'
                         % (id_name, id_name, checked_text, self.get_disabled_str(disabled), self.refresh_on_change_text, id_name, self.get_disabled_str(disabled)))

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


class SelectField(BaseField):
    """
    A select field.

    >>> t = SelectField( "foo", multiple=True )
    >>> t.add_option( "tuti", 1 )
    >>> t.add_option( "fruity", "x" )
    >>> print(t.get_html())
    <select name="foo" multiple>
    <option value="1">tuti</option>
    <option value="x">fruity</option>
    </select>

    >>> t = SelectField( "bar" )
    >>> t.add_option( "automatic", 3 )
    >>> t.add_option( "bazooty", 4, selected=True )
    >>> print(t.get_html())
    <select name="bar" last_selected_value="4">
    <option value="3">automatic</option>
    <option value="4" selected>bazooty</option>
    </select>

    >>> t = SelectField( "foo", display="radio" )
    >>> t.add_option( "tuti", 1 )
    >>> t.add_option( "fruity", "x" )
    >>> print(t.get_html())
    <div><input type="radio" name="foo" value="1" id="foo|1"><label class="inline" for="foo|1">tuti</label></div>
    <div><input type="radio" name="foo" value="x" id="foo|x"><label class="inline" for="foo|x">fruity</label></div>

    >>> t = SelectField( "bar", multiple=True, display="checkboxes" )
    >>> t.add_option( "automatic", 3 )
    >>> t.add_option( "bazooty", 4, selected=True )
    >>> print(t.get_html())
    <div class="checkUncheckAllPlaceholder" checkbox_name="bar"></div>
    <div><input type="checkbox" name="bar" value="3" id="bar|3"><label class="inline" for="bar|3">automatic</label></div>
    <div><input type="checkbox" name="bar" value="4" id="bar|4" checked='checked'><label class="inline" for="bar|4">bazooty</label></div>
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

    def get_html(self, prefix="", disabled=False, extra_attr=None):
        if extra_attr is not None:
            self.extra_attributes = ' %s' % ' '.join(['%s="%s"' % (k, escape(v)) for k, v in extra_attr.items()])
        else:
            self.extra_attributes = ''
        if self.display == "checkboxes":
            return self.get_html_checkboxes(prefix, disabled)
        elif self.display == "radio":
            return self.get_html_radio(prefix, disabled)
        else:
            return self.get_html_default(prefix, disabled)

    def get_html_checkboxes(self, prefix="", disabled=False):
        rval = []
        ctr = 0
        if len(self.options) > 1:
            rval.append('<div class="checkUncheckAllPlaceholder" checkbox_name="%s%s"></div>' % (prefix, self.name))  # placeholder for the insertion of the Select All/Unselect All buttons
        for text, value, selected in self.options:
            style = ""
            text = unicodify(text)
            escaped_value = escape(unicodify(value), quote=True)
            uniq_id = "%s%s|%s" % (prefix, self.name, escaped_value)
            if len(self.options) > 2 and ctr % 2 == 1:
                style = " class=\"odd_row\""
            selected_text = ""
            if selected:
                selected_text = " checked='checked'"
            rval.append('<div%s><input type="checkbox" name="%s%s" value="%s" id="%s"%s%s%s><label class="inline" for="%s">%s</label></div>'
                        % (style, prefix, self.name, escaped_value, uniq_id, selected_text, self.get_disabled_str(disabled), self.extra_attributes, uniq_id, escape(text, quote=True)))
            ctr += 1
        return unicodify("\n".join(rval))

    def get_html_radio(self, prefix="", disabled=False):
        rval = []
        ctr = 0
        for text, value, selected in self.options:
            style = ""
            escaped_value = escape(str(value), quote=True)
            uniq_id = "%s%s|%s" % (prefix, self.name, escaped_value)
            if len(self.options) > 2 and ctr % 2 == 1:
                style = " class=\"odd_row\""
            selected_text = ""
            if selected:
                selected_text = " checked='checked'"
            rval.append('<div%s><input type="radio" name="%s%s"%s value="%s" id="%s"%s%s%s><label class="inline" for="%s">%s</label></div>'
                        % (style,
                           prefix,
                           self.name,
                           self.refresh_on_change_text,
                           escaped_value,
                           uniq_id,
                           selected_text,
                           self.get_disabled_str(disabled),
                           self.extra_attributes,
                           uniq_id,
                           text))
            ctr += 1
        return unicodify("\n".join(rval))

    def get_html_default(self, prefix="", disabled=False):
        if self.multiple:
            multiple = " multiple"
        else:
            multiple = ""
        if self.size:
            size = ' size="%s"' % str(self.size)
        else:
            size = ''
        rval = []
        last_selected_value = ""
        for text, value, selected in self.options:
            if selected:
                selected_text = " selected"
                last_selected_value = value
                if not isinstance(last_selected_value, string_types):
                    last_selected_value = str(last_selected_value)
            else:
                selected_text = ""
            rval.append('<option value="%s"%s>%s</option>' % (escape(unicodify(value), quote=True), selected_text, escape(unicodify(text), quote=True)))
        if last_selected_value:
            last_selected_value = ' last_selected_value="%s"' % escape(unicodify(last_selected_value), quote=True)
        if self.field_id is not None:
            id_string = ' id="%s"' % self.field_id
        else:
            id_string = ''
        rval.insert(0, '<select name="%s%s"%s%s%s%s%s%s%s>'
                    % (prefix, self.name, multiple, size, self.refresh_on_change_text, last_selected_value, self.get_disabled_str(disabled), id_string, self.extra_attributes))
        rval.append('</select>')
        return unicodify("\n".join(rval))

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


def get_suite():
    """Get unittest suite for this module"""
    import doctest
    import sys
    return doctest.DocTestSuite(sys.modules[__name__])


# --------- Utility methods -----------------------------
def build_select_field(trans, objs, label_attr, select_field_name, initial_value='none',
                       selected_value='none', refresh_on_change=False, multiple=False, display=None, size=None):
    """
    Build a SelectField given a set of objects.  The received params are:

    - objs: the set of objects used to populate the option list
    - label_attr: the attribute of each obj (e.g., name, email, etc ) whose value is used to populate each option label.

        - If the string 'self' is passed as label_attr, each obj in objs is assumed to be a string, so the obj itself is used

    - select_field_name: the name of the SelectField
    - initial_value: the value of the first option in the SelectField - allows for an option telling the user to select something
    - selected_value: the value of the currently selected option
    - refresh_on_change: True if the SelectField should perform a refresh_on_change
    """
    if initial_value == 'none':
        values = [initial_value]
    else:
        values = []
    for obj in objs:
        if label_attr == 'self':
            # Each obj is a string
            values.append(obj)
        else:
            values.append(trans.security.encode_id(obj.id))
    if refresh_on_change:
        refresh_on_change_values = values
    else:
        refresh_on_change_values = []
    select_field = SelectField(name=select_field_name,
                               multiple=multiple,
                               display=display,
                               refresh_on_change=refresh_on_change,
                               refresh_on_change_values=refresh_on_change_values,
                               size=size)
    for obj in objs:
        if label_attr == 'self':
            # Each obj is a string
            if str(selected_value) == str(obj):
                select_field.add_option(obj, obj, selected=True)
            else:
                select_field.add_option(obj, obj)
        else:
            label = getattr(obj, label_attr)
            if str(selected_value) == str(obj.id) or str(selected_value) == trans.security.encode_id(obj.id):
                select_field.add_option(label, trans.security.encode_id(obj.id), selected=True)
            else:
                select_field.add_option(label, trans.security.encode_id(obj.id))
    return select_field
