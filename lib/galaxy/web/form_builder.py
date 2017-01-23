"""
Classes for generating HTML forms
"""
import logging

from six import string_types
from cgi import escape
from galaxy.util import restore_text, unicodify

log = logging.getLogger(__name__)


class BaseField(object):
    def __init__( self, name, value=None, label=None, **kwds ):
        self.name = name
        self.label = label
        self.value = value
        self.disabled = kwds.get( 'disabled', False )
        self.optional = kwds.get( 'optional', True ) and kwds.get( 'required', 'optional' ) == 'optional'
        self.help = kwds.get( 'helptext' )

    def get_html( self, prefix="" ):
        """Returns the html widget corresponding to the parameter"""
        raise TypeError( "Abstract Method" )

    def get_disabled_str( self, disabled=False ):
        if disabled:
            return ' disabled="disabled"'
        else:
            return ''

    def to_dict( self ):
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

    >>> print TextField( "foo" ).get_html()
    <input type="text" name="foo" size="10" value="">
    >>> print TextField( "bins", size=4, value="default" ).get_html()
    <input type="text" name="bins" size="4" value="default">
    """
    def __init__( self, name, size=None, value=None, **kwds ):
        super( TextField, self ).__init__( name, value, **kwds )
        self.size = int( size or 10 )

    def get_html( self, prefix="", disabled=False ):
        value = unicodify( self.value or "" )
        return unicodify( '<input type="text" name="%s%s" size="%d" value="%s"%s>'
                          % ( prefix, self.name, self.size, escape( value, quote=True ), self.get_disabled_str( disabled ) ) )

    def set_size(self, size):
        self.size = int( size )

    def to_dict( self ):
        d = super( TextField, self ).to_dict()
        d[ 'type' ] = 'text'
        return d


class PasswordField(BaseField):
    """
    A password input box. text appears as "******"

    >>> print PasswordField( "foo" ).get_html()
    <input type="password" name="foo" size="10" value="">
    >>> print PasswordField( "bins", size=4, value="default" ).get_html()
    <input type="password" name="bins" size="4" value="default">
    """
    def __init__( self, name, size=None, value=None, **kwds ):
        super( PasswordField, self ).__init__( name, value, **kwds )
        self.name = name
        self.size = int( size or 10 )
        self.value = value or ""

    def get_html( self, prefix="", disabled=False  ):
        return unicodify( '<input type="password" name="%s%s" size="%d" value="%s"%s>'
                          % ( prefix, self.name, self.size, escape( str( self.value ), quote=True ), self.get_disabled_str( disabled ) ) )

    def set_size(self, size):
        self.size = int( size )

    def to_dict( self ):
        d = super( PasswordField, self ).to_dict()
        d[ 'type' ] = 'password'
        return d


class TextArea(BaseField):
    """
    A standard text area box.

    >>> print TextArea( "foo" ).get_html()
    <textarea name="foo" rows="5" cols="25"></textarea>
    >>> print TextArea( "bins", size="4x5", value="default" ).get_html()
    <textarea name="bins" rows="4" cols="5">default</textarea>
    """
    _DEFAULT_SIZE = "5x25"

    def __init__( self, name, size=None, value=None, **kwds ):
        super( TextArea, self ).__init__( name, value, **kwds )
        self.name = name
        size = size or self._DEFAULT_SIZE
        self.size = size.split("x")
        self.rows = int(self.size[0])
        self.cols = int(self.size[-1])
        self.value = value or ""

    def get_html( self, prefix="", disabled=False ):
        return unicodify( '<textarea name="%s%s" rows="%d" cols="%d"%s>%s</textarea>'
                          % ( prefix, self.name, self.rows, self.cols, self.get_disabled_str( disabled ), escape( str( self.value ), quote=True ) ) )

    def set_size(self, rows, cols):
        self.rows = rows
        self.cols = cols

    def to_dict( self ):
        d = super( TextArea, self ).to_dict()
        d[ 'type'  ] = 'text'
        d[ 'area'  ] = True
        return d


class CheckboxField(BaseField):
    """
    A checkbox (boolean input)

    >>> print CheckboxField( "foo" ).get_html()
    <input type="checkbox" id="foo" name="foo" value="__CHECKED__"><input type="hidden" name="foo" value="__NOTHING__">
    >>> print CheckboxField( "bar", checked="yes" ).get_html()
    <input type="checkbox" id="bar" name="bar" value="__CHECKED__" checked="checked"><input type="hidden" name="bar" value="__NOTHING__">
    """

    def __init__( self, name, checked=None, refresh_on_change=False, refresh_on_change_values=None, value=None, **kwds ):
        super( CheckboxField, self ).__init__( name, value, **kwds )
        self.name = name
        self.checked = ( checked is True ) or ( isinstance( checked, string_types ) and ( checked.lower() in ( "yes", "true", "on" ) ) )
        self.refresh_on_change = refresh_on_change
        self.refresh_on_change_values = refresh_on_change_values or []
        if self.refresh_on_change:
            self.refresh_on_change_text = ' refresh_on_change="true" '
            if self.refresh_on_change_values:
                self.refresh_on_change_text = '%s refresh_on_change_values="%s" ' % ( self.refresh_on_change_text, ",".join( self.refresh_on_change_values ) )
        else:
            self.refresh_on_change_text = ''

    def get_html( self, prefix="", disabled=False ):
        if self.checked:
            checked_text = ' checked="checked"'
        else:
            checked_text = ''
        id_name = prefix + self.name
        return unicodify( '<input type="checkbox" id="%s" name="%s" value="__CHECKED__"%s%s%s><input type="hidden" name="%s" value="__NOTHING__"%s>'
                          % ( id_name, id_name, checked_text, self.get_disabled_str( disabled ), self.refresh_on_change_text, id_name, self.get_disabled_str( disabled ) ) )

    @staticmethod
    def is_checked( value ):
        if value in [ True, "true" ]:
            return True
        return isinstance( value, list ) and ( '__CHECKED__' in value or len( value ) == 2 )

    def set_checked(self, value):
        if isinstance( value, string_types ):
            self.checked = value.lower() in [ "yes", "true", "on" ]
        else:
            self.checked = value

    def to_dict( self ):
        d = super( CheckboxField, self ).to_dict()
        d[ 'type' ] = 'boolean'
        return d


class FileField(BaseField):
    """
    A file upload input.

    >>> print FileField( "foo" ).get_html()
    <input type="file" name="foo">
    >>> print FileField( "foo", ajax = True ).get_html()
    <input type="file" name="foo" galaxy-ajax-upload="true">
    """

    def __init__( self, name, value=None, ajax=False, **kwds ):
        super( FileField, self ).__init__( name, value, **kwds )
        self.name = name
        self.ajax = ajax
        self.value = value

    def get_html( self, prefix="" ):
        value_text = ""
        if self.value:
            value_text = ' value="%s"' % escape( str( self.value ), quote=True )
        ajax_text = ""
        if self.ajax:
            ajax_text = ' galaxy-ajax-upload="true"'
        return unicodify( '<input type="file" name="%s%s"%s%s>' % ( prefix, self.name, ajax_text, value_text ) )


class HiddenField(BaseField):
    """
    A hidden field.

    >>> print HiddenField( "foo", 100 ).get_html()
    <input type="hidden" name="foo" value="100">
    """
    def __init__( self, name, value=None, **kwds ):
        super( HiddenField, self ).__init__( name, value, **kwds )
        self.name = name
        self.value = value or ""

    def get_html( self, prefix="" ):
        return unicodify( '<input type="hidden" name="%s%s" value="%s">' % ( prefix, self.name, escape( str( self.value ), quote=True ) ) )

    def to_dict( self ):
        d = super( HiddenField, self ).to_dict()
        d[ 'type'    ] = 'hidden'
        d[ 'hidden'  ] = True
        return d


class SelectField(BaseField):
    """
    A select field.

    >>> t = SelectField( "foo", multiple=True )
    >>> t.add_option( "tuti", 1 )
    >>> t.add_option( "fruity", "x" )
    >>> print t.get_html()
    <select name="foo" multiple>
    <option value="1">tuti</option>
    <option value="x">fruity</option>
    </select>

    >>> t = SelectField( "bar" )
    >>> t.add_option( "automatic", 3 )
    >>> t.add_option( "bazooty", 4, selected=True )
    >>> print t.get_html()
    <select name="bar" last_selected_value="4">
    <option value="3">automatic</option>
    <option value="4" selected>bazooty</option>
    </select>

    >>> t = SelectField( "foo", display="radio" )
    >>> t.add_option( "tuti", 1 )
    >>> t.add_option( "fruity", "x" )
    >>> print t.get_html()
    <div><input type="radio" name="foo" value="1" id="foo|1"><label class="inline" for="foo|1">tuti</label></div>
    <div><input type="radio" name="foo" value="x" id="foo|x"><label class="inline" for="foo|x">fruity</label></div>

    >>> t = SelectField( "bar", multiple=True, display="checkboxes" )
    >>> t.add_option( "automatic", 3 )
    >>> t.add_option( "bazooty", 4, selected=True )
    >>> print t.get_html()
    <div class="checkUncheckAllPlaceholder" checkbox_name="bar"></div>
    <div><input type="checkbox" name="bar" value="3" id="bar|3"><label class="inline" for="bar|3">automatic</label></div>
    <div><input type="checkbox" name="bar" value="4" id="bar|4" checked='checked'><label class="inline" for="bar|4">bazooty</label></div>
    """
    def __init__( self, name, multiple=None, display=None, refresh_on_change=False, refresh_on_change_values=None, size=None, field_id=None, value=None, selectlist=None, **kwds ):
        super( SelectField, self ).__init__( name, value, **kwds )
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
            assert not( multiple ), "Radio display only supported for single select"
        elif display is not None:
            raise Exception( "Unknown display type: %s" % display )
        self.display = display
        self.refresh_on_change = refresh_on_change
        self.refresh_on_change_values = refresh_on_change_values or []
        if self.refresh_on_change:
            self.refresh_on_change_text = ' refresh_on_change="true"'
            if self.refresh_on_change_values:
                self.refresh_on_change_text = '%s refresh_on_change_values="%s"' % ( self.refresh_on_change_text, escape( ",".join( self.refresh_on_change_values ), quote=True ) )
        else:
            self.refresh_on_change_text = ''

    def add_option( self, text, value, selected=False ):
        self.options.append( ( text, value, selected ) )

    def get_html( self, prefix="", disabled=False, extra_attr=None ):
        if extra_attr is not None:
            self.extra_attributes = ' %s' % ' '.join( [ '%s="%s"' % ( k, escape( v ) ) for k, v in extra_attr.items() ] )
        else:
            self.extra_attributes = ''
        if self.display == "checkboxes":
            return self.get_html_checkboxes( prefix, disabled )
        elif self.display == "radio":
            return self.get_html_radio( prefix, disabled )
        else:
            return self.get_html_default( prefix, disabled )

    def get_html_checkboxes( self, prefix="", disabled=False ):
        rval = []
        ctr = 0
        if len( self.options ) > 1:
            rval.append( '<div class="checkUncheckAllPlaceholder" checkbox_name="%s%s"></div>' % ( prefix, self.name ) )  # placeholder for the insertion of the Select All/Unselect All buttons
        for text, value, selected in self.options:
            style = ""
            text = unicodify( text )
            escaped_value = escape( unicodify( value ), quote=True )
            uniq_id = "%s%s|%s" % (prefix, self.name, escaped_value)
            if len(self.options) > 2 and ctr % 2 == 1:
                style = " class=\"odd_row\""
            selected_text = ""
            if selected:
                selected_text = " checked='checked'"
            rval.append( '<div%s><input type="checkbox" name="%s%s" value="%s" id="%s"%s%s%s><label class="inline" for="%s">%s</label></div>'
                         % ( style, prefix, self.name, escaped_value, uniq_id, selected_text, self.get_disabled_str( disabled ), self.extra_attributes, uniq_id, escape( text, quote=True ) ) )
            ctr += 1
        return unicodify( "\n".join( rval ) )

    def get_html_radio( self, prefix="", disabled=False ):
        rval = []
        ctr = 0
        for text, value, selected in self.options:
            style = ""
            escaped_value = escape( str( value ), quote=True )
            uniq_id = "%s%s|%s" % (prefix, self.name, escaped_value)
            if len(self.options) > 2 and ctr % 2 == 1:
                style = " class=\"odd_row\""
            selected_text = ""
            if selected:
                selected_text = " checked='checked'"
            rval.append( '<div%s><input type="radio" name="%s%s"%s value="%s" id="%s"%s%s%s><label class="inline" for="%s">%s</label></div>'
                         % ( style,
                             prefix,
                             self.name,
                             self.refresh_on_change_text,
                             escaped_value,
                             uniq_id,
                             selected_text,
                             self.get_disabled_str( disabled ),
                             self.extra_attributes,
                             uniq_id,
                             text ) )
            ctr += 1
        return unicodify( "\n".join( rval ) )

    def get_html_default( self, prefix="", disabled=False ):
        if self.multiple:
            multiple = " multiple"
        else:
            multiple = ""
        if self.size:
            size = ' size="%s"' % str( self.size )
        else:
            size = ''
        rval = []
        last_selected_value = ""
        for text, value, selected in self.options:
            if selected:
                selected_text = " selected"
                last_selected_value = value
                if not isinstance( last_selected_value, string_types ):
                    last_selected_value = str( last_selected_value )
            else:
                selected_text = ""
            rval.append( '<option value="%s"%s>%s</option>' % ( escape( unicodify( value ), quote=True ), selected_text, escape( unicodify( text ), quote=True ) ) )
        if last_selected_value:
            last_selected_value = ' last_selected_value="%s"' % escape( unicodify( last_selected_value ), quote=True )
        if self.field_id is not None:
            id_string = ' id="%s"' % self.field_id
        else:
            id_string = ''
        rval.insert( 0, '<select name="%s%s"%s%s%s%s%s%s%s>'
                     % ( prefix, self.name, multiple, size, self.refresh_on_change_text, last_selected_value, self.get_disabled_str( disabled ), id_string, self.extra_attributes ) )
        rval.append( '</select>' )
        return unicodify( "\n".join( rval ) )

    def get_selected( self, return_label=False, return_value=False, multi=False ):
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
                        selected_options.append( ( label, value ) )
                    else:
                        return ( label, value )
                elif return_label:
                    if multi:
                        selected_options.append( label )
                    else:
                        return label
                elif return_value:
                    if multi:
                        selected_options.append( value )
                    else:
                        return value
        if multi:
            return selected_options
        return None

    def to_dict( self ):
        d = super( SelectField, self ).to_dict()
        d[ 'type' ] = 'select'
        d[ 'display' ] = self.display
        d[ 'multiple' ] = self.multiple
        d[ 'data' ] = []
        for value in self.selectlist:
            d[ 'data' ].append( { 'label': value, 'value': value } )
        return d


class AddressField(BaseField):
    @staticmethod
    def fields():
        return [  ( "desc", "Short address description", "Required" ),
                  ( "name", "Name", "" ),
                  ( "institution", "Institution", "" ),
                  ( "address", "Address", "" ),
                  ( "city", "City", "" ),
                  ( "state", "State/Province/Region", "" ),
                  ( "postal_code", "Postal Code", "" ),
                  ( "country", "Country", "" ),
                  ( "phone", "Phone", "" )  ]

    def __init__(self, name, user=None, value=None, params=None, security=None, **kwds):
        super( AddressField, self ).__init__( name, value, **kwds )
        self.user = user
        self.security = security
        self.select_address = None
        self.params = params

    def get_html( self, disabled=False ):
        address_html = ''
        add_ids = ['none']
        if self.user:
            for a in self.user.addresses:
                add_ids.append( str( a.id ) )
        add_ids.append( 'new' )
        self.select_address = SelectField( self.name,
                                           refresh_on_change=True,
                                           refresh_on_change_values=add_ids )
        if self.value == 'none':
            self.select_address.add_option( 'Select one', 'none', selected=True )
        else:
            self.select_address.add_option( 'Select one', 'none' )
        if self.user:
            for a in self.user.addresses:
                if not a.deleted:
                    if self.value == str( a.id ):
                        self.select_address.add_option( a.desc, str( a.id ), selected=True )
                        # Display this address
                        address_html += '''
                                        <div class="form-row">
                                            %s
                                        </div>
                                        ''' % a.get_html()
                    else:
                        self.select_address.add_option( a.desc, str( a.id ) )
        if self.value == 'new':
            self.select_address.add_option( 'Add a new address', 'new', selected=True )
            for field_name, label, help_text in self.fields():
                add_field = TextField( self.name + '_' + field_name,
                                       40,
                                       restore_text( self.params.get( self.name + '_' + field_name, ''  ) ) )
                address_html += '''
                                <div class="form-row">
                                    <label>%s</label>
                                    %s
                                    ''' % ( label, add_field.get_html( disabled=disabled ) )
                if help_text:
                    address_html += '''
                                    <div class="toolParamHelp" style="clear: both;">
                                        %s
                                    </div>
                                    ''' % help_text
                address_html += '''
                                </div>
                                '''
        else:
            self.select_address.add_option( 'Add a new address', 'new' )
        return self.select_address.get_html( disabled=disabled ) + address_html

    def to_dict( self ):
        d = super( AddressField, self ).to_dict()
        d[ 'type' ] = 'select'
        d[ 'data' ] = []
        if self.user and self.security:
            for a in self.user.addresses:
                if not a.deleted:
                    d[ 'data' ].append( { 'label': a.desc, 'value': self.security.encode_id( a.id ) } )
        return d


class WorkflowField( BaseField ):
    def __init__( self, name, user=None, value=None, params=None, security=None, **kwds ):
        super( WorkflowField, self ).__init__( name, value, **kwds )
        self.name = name
        self.user = user
        self.value = value
        self.security = security
        self.select_workflow = None
        self.params = params

    def get_html( self, disabled=False ):
        self.select_workflow = SelectField( self.name )
        if self.value == 'none':
            self.select_workflow.add_option( 'Select one', 'none', selected=True )
        else:
            self.select_workflow.add_option( 'Select one', 'none' )
        if self.user:
            for a in self.user.stored_workflows:
                if not a.deleted:
                    if str( self.value ) == str( a.id ):
                        self.select_workflow.add_option( a.name, str( a.id ), selected=True )
                    else:
                        self.select_workflow.add_option( a.name, str( a.id ) )
        return self.select_workflow.get_html( disabled=disabled )

    def to_dict( self ):
        d = super( WorkflowField, self ).to_dict()
        d[ 'type' ] = 'select'
        d[ 'data' ] = []
        if self.user and self.security:
            for a in self.user.stored_workflows:
                if not a.deleted:
                    d[ 'data' ].append( { 'label': a.name, 'value': self.security.encode_id( a.id ) } )
        return d


class WorkflowMappingField( BaseField ):
    def __init__( self, name, user=None, value=None, params=None, **kwd ):
        # DBTODO integrate this with the new __build_workflow approach in requests_common.  As it is, not particularly useful.
        self.name = name
        self.user = user
        self.value = value
        self.select_workflow = None
        self.params = params
        self.workflow_inputs = []

    def get_html( self, disabled=False ):
        self.select_workflow = SelectField( self.name, refresh_on_change=True )
        workflow_inputs = []
        if self.value == 'none':
            self.select_workflow.add_option( 'Select one', 'none', selected=True )
        else:
            self.select_workflow.add_option( 'Select one', 'none' )
        if self.user:
            for a in self.user.stored_workflows:
                if not a.deleted:
                    if str( self.value ) == str( a.id ):
                        self.select_workflow.add_option( a.name, str( a.id ), selected=True )
                    else:
                        self.select_workflow.add_option( a.name, str( a.id ) )
            if self.value and self.value != 'none':
                # Workflow selected.  Find all inputs.
                for workflow in self.user.stored_workflows:
                    if workflow.id == int(self.value):
                        for step in workflow.latest_workflow.steps:
                            if step.type == 'data_input':
                                if step.tool_inputs and "name" in step.tool_inputs:
                                    workflow_inputs.append((step.tool_inputs['name'], TextField( '%s_%s' % (self.name, step.id), 20)))
        # Do something more appropriate here and allow selection of inputs
        return self.select_workflow.get_html( disabled=disabled ) + ''.join(['<div class="form-row"><label>%s</label>%s</div>' % (s[0], s[1].get_html()) for s in workflow_inputs])


class HistoryField( BaseField ):
    def __init__( self, name, user=None, value=None, params=None, security=None, **kwds ):
        super( HistoryField, self ).__init__( name, value, **kwds )
        self.name = name
        self.user = user
        self.value = value
        self.security = security
        self.select_history = None
        self.params = params

    def get_html( self, disabled=False ):
        self.select_history = SelectField( self.name )
        if self.value == 'none':
            self.select_history.add_option( 'No Import', 'none', selected=True )
            self.select_history.add_option( 'New History', 'new' )
        else:
            self.select_history.add_option( 'No Import', 'none' )
            if self.value == 'new':
                self.select_history.add_option( 'New History', 'new', selected=True )
            else:
                self.select_history.add_option( 'New History', 'new')
        if self.user:
            for a in self.user.histories:
                if not a.deleted:
                    if str( self.value ) == str( a.id ):
                        self.select_history.add_option( a.name, str( a.id ), selected=True )
                    else:
                        self.select_history.add_option( a.name, str( a.id ) )
        return self.select_history.get_html( disabled=disabled )

    def to_dict( self ):
        d = super( HistoryField, self ).to_dict()
        d[ 'type' ] = 'select'
        d[ 'data' ] = [{ 'label': 'New History', 'value': 'new' }]
        if self.user and self.security:
            for a in self.user.histories:
                if not a.deleted:
                    d[ 'data' ].append( { 'label': a.name, 'value': self.security.encode_id( a.id ) } )
        return d


def get_suite():
    """Get unittest suite for this module"""
    import doctest
    import sys
    return doctest.DocTestSuite( sys.modules[__name__] )


# --------- Utility methods -----------------------------
def build_select_field( trans, objs, label_attr, select_field_name, initial_value='none',
                        selected_value='none', refresh_on_change=False, multiple=False, display=None, size=None ):
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
        values = [ initial_value ]
    else:
        values = []
    for obj in objs:
        if label_attr == 'self':
            # Each obj is a string
            values.append( obj )
        else:
            values.append( trans.security.encode_id( obj.id ) )
    if refresh_on_change:
        refresh_on_change_values = values
    else:
        refresh_on_change_values = []
    select_field = SelectField( name=select_field_name,
                                multiple=multiple,
                                display=display,
                                refresh_on_change=refresh_on_change,
                                refresh_on_change_values=refresh_on_change_values,
                                size=size )
    for obj in objs:
        if label_attr == 'self':
            # Each obj is a string
            if str( selected_value ) == str( obj ):
                select_field.add_option( obj, obj, selected=True )
            else:
                select_field.add_option( obj, obj )
        else:
            label = getattr( obj, label_attr )
            if str( selected_value ) == str( obj.id ) or str( selected_value ) == trans.security.encode_id( obj.id ):
                select_field.add_option( label, trans.security.encode_id( obj.id ), selected=True )
            else:
                select_field.add_option( label, trans.security.encode_id( obj.id ) )
    return select_field
