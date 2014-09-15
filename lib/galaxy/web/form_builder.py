"""
Classes for generating HTML forms
"""

import logging, sys, os, time

from operator import itemgetter
from cgi import escape
from galaxy.util import restore_text, relpath, nice_size, unicodify
from galaxy.util.json import dumps
from galaxy.web import url_for
from binascii import hexlify

log = logging.getLogger(__name__)

class BaseField(object):
    def get_html( self, prefix="" ):
        """Returns the html widget corresponding to the parameter"""
        raise TypeError( "Abstract Method" )
    def get_disabled_str( self, disabled=False ):
        if disabled:
            return ' disabled="disabled"'
        else:
            return ''

class TextField(BaseField):
    """
    A standard text input box.

    >>> print TextField( "foo" ).get_html()
    <input type="text" name="foo" size="10" value="">
    >>> print TextField( "bins", size=4, value="default" ).get_html()
    <input type="text" name="bins" size="4" value="default">
    """
    def __init__( self, name, size=None, value=None ):
        self.name = name
        self.size = int( size or 10 )
        self.value = value or ""
    def get_html( self, prefix="", disabled=False ):
        value = self.value
        if not isinstance( value, basestring ):
            value = str( value )
        value = unicodify( value )
        return unicodify( '<input type="text" name="%s%s" size="%d" value="%s"%s>' \
            % ( prefix, self.name, self.size, escape( value,  quote=True ), self.get_disabled_str( disabled ) ) )
    def set_size(self, size):
        self.size = int( size )

class PasswordField(BaseField):
    """
    A password input box. text appears as "******"

    >>> print PasswordField( "foo" ).get_html()
    <input type="password" name="foo" size="10" value="">
    >>> print PasswordField( "bins", size=4, value="default" ).get_html()
    <input type="password" name="bins" size="4" value="default">
    """
    def __init__( self, name, size=None, value=None ):
        self.name = name
        self.size = int( size or 10 )
        self.value = value or ""
    def get_html( self, prefix="", disabled=False  ):
        return unicodify( '<input type="password" name="%s%s" size="%d" value="%s"%s>' \
            % ( prefix, self.name, self.size, escape( str( self.value ), quote=True ), self.get_disabled_str( disabled ) ) )
    def set_size(self, size):
        self.size = int( size )

class TextArea(BaseField):
    """
    A standard text area box.

    >>> print TextArea( "foo" ).get_html()
    <textarea name="foo" rows="5" cols="25"></textarea>
    >>> print TextArea( "bins", size="4x5", value="default" ).get_html()
    <textarea name="bins" rows="4" cols="5">default</textarea>
    """
    _DEFAULT_SIZE = "5x25"
    def __init__( self, name, size=None, value=None ):
        self.name = name
        size = size or self._DEFAULT_SIZE
        self.size = size.split("x")
        self.rows = int(self.size[0])
        self.cols = int(self.size[-1])
        self.value = value or ""
    def get_html( self, prefix="", disabled=False ):
        return unicodify( '<textarea name="%s%s" rows="%d" cols="%d"%s>%s</textarea>' \
            % ( prefix, self.name, self.rows, self.cols, self.get_disabled_str( disabled ), escape( str( self.value ), quote=True ) ) )
    def set_size(self, rows, cols):
        self.rows = rows
        self.cols = cols

class CheckboxField(BaseField):
    """
    A checkbox (boolean input)

    >>> print CheckboxField( "foo" ).get_html()
    <input type="checkbox" id="foo" name="foo" value="true"><input type="hidden" name="foo" value="true">
    >>> print CheckboxField( "bar", checked="yes" ).get_html()
    <input type="checkbox" id="bar" name="bar" value="true" checked="checked"><input type="hidden" name="bar" value="true">
    """
    def __init__( self, name, checked=None, refresh_on_change = False, refresh_on_change_values = None ):
        self.name = name
        self.checked = ( checked == True ) or ( isinstance( checked, basestring ) and ( checked.lower() in ( "yes", "true", "on" ) ) )
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
            checked_text = ""
        id_name = prefix + self.name
        # The hidden field is necessary because if the check box is not checked on the form, it will
        # not be included in the request params.  The hidden field ensure that this will happen.  When
        # parsing the request, the value 'true' in the hidden field actually means it is NOT checked.
        # See the is_checked() method below.  The prefix is necessary in each case to ensure functional
        # correctness when the param is inside a conditional.
        return unicodify( '<input type="checkbox" id="%s" name="%s" value="true"%s%s%s><input type="hidden" name="%s%s" value="true"%s>' \
            % ( id_name, id_name, checked_text, self.get_disabled_str( disabled ), self.refresh_on_change_text, prefix, self.name, self.get_disabled_str( disabled ) ) )
    @staticmethod
    def is_checked( value ):
        if value == True:
            return True
        # This may look strange upon initial inspection, but see the comments in the get_html() method
        # above for clarification.  Basically, if value is not True, then it will always be a list with
        # 2 input fields ( a checkbox and a hidden field ) if the checkbox is checked.  If it is not
        # checked, then value will be only the hidden field.
        return isinstance( value, list ) and len( value ) == 2
    def set_checked(self, value):
        if isinstance( value, basestring ):
            self.checked = value.lower() in [ "yes", "true", "on" ]
        else:
            self.checked = value

class FileField(BaseField):
    """
    A file upload input.

    >>> print FileField( "foo" ).get_html()
    <input type="file" name="foo">
    >>> print FileField( "foo", ajax = True ).get_html()
    <input type="file" name="foo" galaxy-ajax-upload="true">
    """
    def __init__( self, name, value = None, ajax=False ):
        self.name = name
        self.ajax = ajax
        self.value = value
    def get_html( self, prefix="" ):
        value_text = ""
        if self.value:
            value_text = ' value="%s"' % escape( str( self.value ),  quote=True )
        ajax_text = ""
        if self.ajax:
            ajax_text = ' galaxy-ajax-upload="true"'
        return unicodify( '<input type="file" name="%s%s"%s%s>' % ( prefix, self.name, ajax_text, value_text ) )

class FTPFileField(BaseField):
    """
    An FTP file upload input.
    """
    thead = '''
        <table id="grid-table" class="grid">
            <thead id="grid-table-header">
                <tr>
                    <th id="select-header"></th>
                    <th id="name-header">
                        File
                    </th>
                    <th id="size-header">
                        Size
                    </th>
                    <th id="date-header">
                        Date
                    </th>
                </tr>
            </thead>
            <tbody id="grid-table-body">
    '''
    trow = '''
                <tr>
                    <td><input type="checkbox" name="%s%s" value="%s"/></td>
                    <td>%s</td>
                    <td>%s</td>
                    <td>%s</td>
                </tr>
    '''
    tfoot = '''
            </tbody>
        </table>
    '''
    def __init__( self, name, dir, ftp_site, value = None ):
        self.name = name
        self.dir = dir
        self.ftp_site = ftp_site
        self.value = value
    def get_html( self, prefix="" ):
        rval = FTPFileField.thead
        if self.dir is None:
            rval += '<tr><td colspan="4"><em>Please <a href="%s">create</a> or <a href="%s">log in to</a> a Galaxy account to view files uploaded via FTP.</em></td></tr>' % ( url_for( controller='user', action='create', cntrller='user', referer=url_for( controller='root' ) ), url_for( controller='user', action='login', cntrller='user', referer=url_for( controller='root' ) ) )
        elif not os.path.exists( self.dir ):
            rval += '<tr><td colspan="4"><em>Your FTP upload directory contains no files.</em></td></tr>'
        else:
            uploads = []
            for ( dirpath, dirnames, filenames ) in os.walk( self.dir ):
                for filename in filenames:
                    path = relpath( os.path.join( dirpath, filename ), self.dir )
                    statinfo = os.lstat( os.path.join( dirpath, filename ) )
                    uploads.append( dict( path=path,
                                          size=nice_size( statinfo.st_size ),
                                          ctime=time.strftime( "%m/%d/%Y %I:%M:%S %p", time.localtime( statinfo.st_ctime ) ) ) )
            if not uploads:
                rval += '<tr><td colspan="4"><em>Your FTP upload directory contains no files.</em></td></tr>'
            uploads = sorted(uploads, key=itemgetter("path"))
            for upload in uploads:
                rval += FTPFileField.trow % ( prefix, self.name, upload['path'], upload['path'], upload['size'], upload['ctime'] )
        rval += FTPFileField.tfoot
        rval += '<div class="toolParamHelp">This Galaxy server allows you to upload files via FTP.  To upload some files, log in to the FTP server at <strong>%s</strong> using your Galaxy credentials (email address and password).</div>' % self.ftp_site
        return rval

class HiddenField(BaseField):
    """
    A hidden field.

    >>> print HiddenField( "foo", 100 ).get_html()
    <input type="hidden" name="foo" value="100">
    """
    def __init__( self, name, value=None ):
        self.name = name
        self.value = value or ""
    def get_html( self, prefix="" ):
        return unicodify( '<input type="hidden" name="%s%s" value="%s">' % ( prefix, self.name, escape( str( self.value ), quote=True ) ) )

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
    def __init__( self, name, multiple=None, display=None, refresh_on_change=False, refresh_on_change_values=None, size=None ):
        self.name = name
        self.multiple = multiple or False
        self.size = size
        self.options = list()
        if display == "checkboxes":
            assert multiple, "Checkbox display only supported for multiple select"
        elif display == "radio":
            assert not( multiple ), "Radio display only supported for single select"
        elif display is not None:
            raise Exception, "Unknown display type: %s" % display
        self.display = display
        self.refresh_on_change = refresh_on_change
        self.refresh_on_change_values = refresh_on_change_values or []
        if self.refresh_on_change:
            self.refresh_on_change_text = ' refresh_on_change="true"'
            if self.refresh_on_change_values:
                self.refresh_on_change_text = '%s refresh_on_change_values="%s"' % ( self.refresh_on_change_text, escape( ",".join( self.refresh_on_change_values ), quote=True ) )
        else:
            self.refresh_on_change_text = ''
    def add_option( self, text, value, selected = False ):
        self.options.append( ( text, value, selected ) )
    def get_html( self, prefix="", disabled=False ):
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
            rval.append ( '<div class="checkUncheckAllPlaceholder" checkbox_name="%s%s"></div>' % ( prefix, self.name ) ) #placeholder for the insertion of the Select All/Unselect All buttons
        for text, value, selected in self.options:
            style = ""
            if not isinstance( value, basestring ):
                value = str( value )
            if not isinstance( text, basestring ):
                text = str( text )
            text = unicodify( text )
            escaped_value = escape( unicodify( value ), quote=True )
            uniq_id = "%s%s|%s" % (prefix, self.name, escaped_value)
            if len(self.options) > 2 and ctr % 2 == 1:
                style = " class=\"odd_row\""
            selected_text = ""
            if selected:
                selected_text = " checked='checked'"
            rval.append( '<div%s><input type="checkbox" name="%s%s" value="%s" id="%s"%s%s><label class="inline" for="%s">%s</label></div>' % \
                ( style, prefix, self.name, escaped_value, uniq_id, selected_text, self.get_disabled_str( disabled ), uniq_id, escape( text, quote=True ) ) )
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
            rval.append( '<div%s><input type="radio" name="%s%s"%s value="%s" id="%s"%s%s><label class="inline" for="%s">%s</label></div>' % \
                         ( style,
                           prefix,
                           self.name,
                           self.refresh_on_change_text,
                           escaped_value,
                           uniq_id,
                           selected_text,
                           self.get_disabled_str( disabled ),
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
                if not isinstance( last_selected_value, basestring ):
                    last_selected_value = str( last_selected_value )
            else:
                selected_text = ""
            if not isinstance( value, basestring ):
                value = str( value )
            if not isinstance( text, basestring ):
                text = str( text )
            rval.append( '<option value="%s"%s>%s</option>' % ( escape( unicodify( value ), quote=True ), selected_text, escape( unicodify( text ), quote=True ) ) )
        if last_selected_value:
            last_selected_value = ' last_selected_value="%s"' % escape( unicodify( last_selected_value ), quote=True )
        rval.insert( 0, '<select name="%s%s"%s%s%s%s%s>' % \
                     ( prefix, self.name, multiple, size, self.refresh_on_change_text, last_selected_value, self.get_disabled_str( disabled ) ) )
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
        return dict(
            name=self.name,
            multiple=self.multiple,
            options=self.options
        )


class DrillDownField( BaseField ):
    """
    A hierarchical select field, which allows users to 'drill down' a tree-like set of options.

    >>> t = DrillDownField( "foo", multiple=True, display="checkbox", options=[{'name': 'Heading 1', 'value': 'heading1', 'options': [{'name': 'Option 1', 'value': 'option1', 'options': []}, {'name': 'Option 2', 'value': 'option2', 'options': []}, {'name': 'Heading 1', 'value': 'heading1', 'options': [{'name': 'Option 3', 'value': 'option3', 'options': []}, {'name': 'Option 4', 'value': 'option4', 'options': []}]}]}, {'name': 'Option 5', 'value': 'option5', 'options': []}] )
    >>> print t.get_html()
    <div class="form-row drilldown-container" id="drilldown--666f6f">
    <div class="form-row-input">
    <div><span class="form-toggle icon-button toggle-expand" id="drilldown--666f6f-68656164696e6731-click"></span>
    <input type="checkbox" name="foo" value="heading1" >Heading 1
    </div><div class="form-row" id="drilldown--666f6f-68656164696e6731-container" style="float: left; margin-left: 1em;">
    <div class="form-row-input">
    <input type="checkbox" name="foo" value="option1" >Option 1
    </div>
    <div class="form-row-input">
    <input type="checkbox" name="foo" value="option2" >Option 2
    </div>
    <div class="form-row-input">
    <div><span class="form-toggle icon-button toggle-expand" id="drilldown--666f6f-68656164696e6731-68656164696e6731-click"></span>
    <input type="checkbox" name="foo" value="heading1" >Heading 1
    </div><div class="form-row" id="drilldown--666f6f-68656164696e6731-68656164696e6731-container" style="float: left; margin-left: 1em;">
    <div class="form-row-input">
    <input type="checkbox" name="foo" value="option3" >Option 3
    </div>
    <div class="form-row-input">
    <input type="checkbox" name="foo" value="option4" >Option 4
    </div>
    </div>
    </div>
    </div>
    </div>
    <div class="form-row-input">
    <input type="checkbox" name="foo" value="option5" >Option 5
    </div>
    </div>
    >>> t = DrillDownField( "foo", multiple=False, display="radio", options=[{'name': 'Heading 1', 'value': 'heading1', 'options': [{'name': 'Option 1', 'value': 'option1', 'options': []}, {'name': 'Option 2', 'value': 'option2', 'options': []}, {'name': 'Heading 1', 'value': 'heading1', 'options': [{'name': 'Option 3', 'value': 'option3', 'options': []}, {'name': 'Option 4', 'value': 'option4', 'options': []}]}]}, {'name': 'Option 5', 'value': 'option5', 'options': []}] )
    >>> print t.get_html()
    <div class="form-row drilldown-container" id="drilldown--666f6f">
    <div class="form-row-input">
    <div><span class="form-toggle icon-button toggle-expand" id="drilldown--666f6f-68656164696e6731-click"></span>
    <input type="radio" name="foo" value="heading1" >Heading 1
    </div><div class="form-row" id="drilldown--666f6f-68656164696e6731-container" style="float: left; margin-left: 1em;">
    <div class="form-row-input">
    <input type="radio" name="foo" value="option1" >Option 1
    </div>
    <div class="form-row-input">
    <input type="radio" name="foo" value="option2" >Option 2
    </div>
    <div class="form-row-input">
    <div><span class="form-toggle icon-button toggle-expand" id="drilldown--666f6f-68656164696e6731-68656164696e6731-click"></span>
    <input type="radio" name="foo" value="heading1" >Heading 1
    </div><div class="form-row" id="drilldown--666f6f-68656164696e6731-68656164696e6731-container" style="float: left; margin-left: 1em;">
    <div class="form-row-input">
    <input type="radio" name="foo" value="option3" >Option 3
    </div>
    <div class="form-row-input">
    <input type="radio" name="foo" value="option4" >Option 4
    </div>
    </div>
    </div>
    </div>
    </div>
    <div class="form-row-input">
    <input type="radio" name="foo" value="option5" >Option 5
    </div>
    </div>
    """
    def __init__( self, name, multiple=None, display=None, refresh_on_change=False, options = [], value = [], refresh_on_change_values = [] ):
        self.name = name
        self.multiple = multiple or False
        self.options = options
        if value and not isinstance( value, list ):
            value = [ value ]
        elif not value:
            value = []
        self.value = value
        if display == "checkbox":
            assert multiple, "Checkbox display only supported for multiple select"
        elif display == "radio":
            assert not( multiple ), "Radio display only supported for single select"
        else:
            raise Exception, "Unknown display type: %s" % display
        self.display = display
        self.refresh_on_change = refresh_on_change
        self.refresh_on_change_values = refresh_on_change_values
        if self.refresh_on_change:
            self.refresh_on_change_text = ' refresh_on_change="true"'
            if self.refresh_on_change_values:
                self.refresh_on_change_text = '%s refresh_on_change_values="%s"' % ( self.refresh_on_change_text, ",".join( self.refresh_on_change_values ) )
        else:
            self.refresh_on_change_text = ''
    def get_html( self, prefix="" ):
        def find_expanded_options( expanded_options, options, parent_options = [] ):
            for option in options:
                if option['value'] in self.value:
                    expanded_options.extend( parent_options )
                if option['options']:
                    new_parents = list( parent_options ) + [ option['value'] ]
                    find_expanded_options( expanded_options, option['options'], new_parents )
        def recurse_options( html, options, base_id, expanded_options = [] ):
            for option in options:
                escaped_option_value = escape( str( option['value'] ), quote=True )
                selected = ( option['value'] in self.value )
                if selected:
                    selected = ' checked'
                else:
                    selected = ''
                span_class = 'form-toggle icon-button toggle'
                if option['value'] not in expanded_options:
                    span_class = "%s-expand" % ( span_class )
                html.append( '<div class="form-row-input">')
                drilldown_group_id = "%s-%s" % ( base_id, hexlify( option['value'] ) )
                if option['options']:
                    html.append( '<div><span class="%s" id="%s-click"></span>' % ( span_class, drilldown_group_id ) )
                html.append( '<input type="%s" name="%s%s" value="%s" %s>%s' % ( self.display, prefix, self.name, escaped_option_value, selected, option['name']) )
                if option['options']:
                    html.append( '</div><div class="form-row" id="%s-container" style="float: left; margin-left: 1em;">' % ( drilldown_group_id )  )
                    recurse_options( html, option['options'], drilldown_group_id, expanded_options )
                    html.append( '</div>')
                html.append( '</div>')
        drilldown_id = "drilldown-%s-%s" % ( hexlify( prefix ), hexlify( self.name ) )
        rval = []
        rval.append( '<div class="form-row drilldown-container" id="%s">' % ( drilldown_id ) )
        expanded_options = []
        find_expanded_options( expanded_options, self.options )
        recurse_options( rval, self.options, drilldown_id, expanded_options )
        rval.append( '</div>' )
        return unicodify( '\n'.join( rval ) )


class SwitchingSelectField(BaseField):

    def __init__( self, delegate_fields, default_field=None ):
        self.delegate_fields = delegate_fields
        self.default_field = default_field or delegate_fields.keys()[ 0 ]

    @property
    def primary_field( self ):
        primary_field = self.delegate_fields[ self.delegate_fields.keys()[ 0 ] ]
        return primary_field

    def get_html( self, prefix="", disabled=False ):
        primary_field = self.primary_field
        html = '<div class="switch-option">'
        html += primary_field.get_html( prefix=prefix, disabled=disabled )
        html += '<input name="__switch_default__" type="hidden" value="%s" />' % self.default_field
        options = []
        for name, delegate_field in self.delegate_fields.items():
            field = dumps( delegate_field.to_dict() )
            option = " '%s': %s" % ( name, field )
            options.append( option )
        html += '<script>$(document).ready( function() {\nvar switchOptions = {\n'
        html += ','.join( options )
        html += '};\n'
        html += 'if ( window.enhanced_galaxy_tools ) {\n'
        html += 'require( [ "galaxy.tools" ], function( mod_tools ) { new mod_tools.SwitchSelectView({\n'
        html += 'el: $(\'[name="%s%s"]\').closest( "div.switch-option" ),' % ( prefix, primary_field.name )
        html += 'default_option: "%s",\n' % self.default_field
        html += 'prefix: "%s",\n' % prefix
        html += 'switch_options: switchOptions }); } )\n'
        html += "}"
        html += '});\n</script></div>'
        return html


class AddressField(BaseField):
    @staticmethod
    def fields():
        return   [  ( "short_desc", "Short address description", "Required" ),
                    ( "name", "Name", "Required" ),
                    ( "institution", "Institution", "Required" ),
                    ( "address", "Address", "Required" ),
                    ( "city", "City", "Required" ),
                    ( "state", "State/Province/Region", "Required" ),
                    ( "postal_code", "Postal Code", "Required" ),
                    ( "country", "Country", "Required" ),
                    ( "phone", "Phone", "" )  ]
    def __init__(self, name, user=None, value=None, params=None):
        self.name = name
        self.user = user
        self.value = value
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

class WorkflowField( BaseField ):
    def __init__( self, name, user=None, value=None, params=None ):
        self.name = name
        self.user = user
        self.value = value
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

class WorkflowMappingField( BaseField):
    def __init__( self, name, user=None, value=None, params=None, **kwd ):
        # DBTODO integrate this with the new __build_workflow approach in requests_common.  As it is, not particularly useful.
        self.name = name
        self.user = user
        self.value = value
        self.select_workflow = None
        self.params = params
        self.workflow_inputs = []
    def get_html( self, disabled=False ):
        self.select_workflow = SelectField( self.name, refresh_on_change = True )
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
    def get_display_text(self):
        if self.value:
            return self.value
        else:
            return '-'
class HistoryField( BaseField ):
    def __init__( self, name, user=None, value=None, params=None ):
        self.name = name
        self.user = user
        self.value = value
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
    def get_display_text(self):
        if self.value:
            return self.value
        else:
            return '-'

class LibraryField( BaseField ):
    def __init__( self, name, value=None, trans=None ):
        self.name = name
        self.lddas = value
        self.trans = trans
    def get_html( self, prefix="", disabled=False ):
        if not self.lddas:
            ldda_ids = ""
            text = "Select library dataset(s)"
        else:
            ldda_ids = "||".join( [ self.trans.security.encode_id( ldda.id ) for ldda in self.lddas ] )
            text = "<br />".join( [ "%s. %s" % (i+1, ldda.name) for i, ldda in enumerate(self.lddas)] )
        return unicodify( '<a href="javascript:void(0);" class="add-librarydataset">%s</a> \
                <input type="hidden" name="%s%s" value="%s">' % ( text, prefix, self.name, escape( str(ldda_ids), quote=True ) ) )

    def get_display_text(self):
        if self.ldda:
            return self.ldda.name
        else:
            return 'None'

def get_suite():
    """Get unittest suite for this module"""
    import doctest, sys
    return doctest.DocTestSuite( sys.modules[__name__] )

# --------- Utility methods -----------------------------

def build_select_field( trans, objs, label_attr,  select_field_name, initial_value='none',
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
