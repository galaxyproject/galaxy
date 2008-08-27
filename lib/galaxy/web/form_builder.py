"""
Classes for generating HTML forms
"""

import logging,sys
log = logging.getLogger(__name__)

class BaseField(object):
    def get_html( self, prefix="" ):
        """Returns the html widget corresponding to the parameter"""
        raise TypeError( "Abstract Method" )
        
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
    def get_html( self, prefix="" ):
        return '<input type="text" name="%s%s" size="%d" value="%s">' \
            % ( prefix, self.name, self.size, self.value )

class TextArea(BaseField):
    """
    A standard text area box.
    
    >>> print TextArea( "foo" ).get_html()
    <textarea name="foo" rows="5" cols="25"></textarea>
    >>> print TextArea( "bins", size="4x5", value="default" ).get_html()
    <textarea name="bins" rows="4" cols="5">default</textarea>
    """
    def __init__( self, name, size="5x25", value=None ):
        self.name = name
        self.size = size.split("x")
        self.rows = int(self.size[0])
        self.cols = int(self.size[-1])
        self.value = value or ""
    def get_html( self, prefix="" ):
        return '<textarea name="%s%s" rows="%d" cols="%d">%s</textarea>' \
            % ( prefix, self.name, self.rows, self.cols, self.value )

class CheckboxField(BaseField):
    """
    A checkbox (boolean input)
    
    >>> print CheckboxField( "foo" ).get_html()
    <input type="checkbox" name="foo" value="true" ><input type="hidden" name="foo" value="true">
    >>> print CheckboxField( "bar", checked="yes" ).get_html()
    <input type="checkbox" name="bar" value="true" checked><input type="hidden" name="bar" value="true">
    """
    def __init__( self, name, checked=None ):
        self.name = name
        self.checked = (checked == True) or (type(checked) == type('a') and (checked.lower() in (  "yes", "true", "on" ))) 
    def get_html( self, prefix="" ):
        if self.checked: checked_text = "checked"
        else: checked_text = ""
        return '<input type="checkbox" name="%s%s" value="true" %s><input type="hidden" name="%s" value="true">' \
            % ( prefix, self.name, checked_text, self.name )
    @staticmethod
    def is_checked( value ):
        if value == True: # wierd behaviour caused by following check for 2 valued list - wtf? ross august 22
           return value
        if type( value ) == list and len( value ) == 2:
            return True
        else:
            return False

class FileField(BaseField):
    """
    A file upload input.
    
    >>> print FileField( "foo" ).get_html()
    <input type="file" name="foo">
    """
    def __init__( self, name ):
        self.name = name
    def get_html( self, prefix="" ):
        return '<input type="file" name="%s%s">' % ( prefix, self.name )

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
        return '<input type="hidden" name="%s%s" value="%s">' % ( prefix, self.name, self.value )

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
    <select name="bar">
    <option value="3">automatic</option>
    <option value="4" selected>bazooty</option>
    </select>
    
    >>> t = SelectField( "foo", display="radio" )
    >>> t.add_option( "tuti", 1 )
    >>> t.add_option( "fruity", "x" )
    >>> print t.get_html()
    <div><input type="radio" name="foo" value="1">tuti</div>
    <div><input type="radio" name="foo" value="x">fruity</div>

    >>> t = SelectField( "bar", multiple=True, display="checkboxes" )
    >>> t.add_option( "automatic", 3 )
    >>> t.add_option( "bazooty", 4, selected=True )
    >>> print t.get_html()
    <div><input type="checkbox" name="bar" value="3">automatic</div>
    <div><input type="checkbox" name="bar" value="4" checked>bazooty</div>
    """
    def __init__( self, name, multiple=None, display=None, refresh_on_change=False ):
        self.name = name
        self.multiple = multiple or False
        self.options = list()
        if display == "checkboxes":
            assert multiple, "Checkbox display only supported for multiple select"
        elif display == "radio":
            assert not( multiple ), "Radio display only supported for single select"
        elif display is not None:
            raise Exception, "Unknown display type: %s" % display
        self.display = display
        self.refresh_on_change = refresh_on_change
        if self.refresh_on_change: 
            self.refresh_on_change_text = ' refresh_on_change="true"'
        else:
            self.refresh_on_change_text = ''
    def add_option( self, text, value, selected = False ):
        self.options.append( ( text, value, selected ) )
    def get_html( self, prefix="" ):
        if self.display == "checkboxes":
            return self.get_html_checkboxes( prefix )
        elif self.display == "radio":
            return self.get_html_radio( prefix )
        else:
            return self.get_html_default( prefix )
    def get_html_checkboxes( self, prefix="" ):
        rval = []
        ctr = 0
        for text, value, selected in self.options:
            style = ""
            if len(self.options) > 2 and ctr % 2 == 1:
                style = " class=\"odd_row\""
            if selected:
                rval.append( '<div%s><input type="checkbox" name="%s%s" value="%s" checked>%s</div>' % ( style, prefix, self.name, value, text) )
            else:
                rval.append( '<div%s><input type="checkbox" name="%s%s" value="%s">%s</div>' % ( style, prefix, self.name, value, text) )
            ctr += 1
        return "\n".join( rval )
    def get_html_radio( self, prefix="" ):
        rval = []
        ctr = 0
        for text, value, selected in self.options:
            style = ""
            if len(self.options) > 2 and ctr % 2 == 1:
                style = " class=\"odd_row\""
            if selected: selected_text = " checked"
            else: selected_text = ""
            rval.append( '<div%s><input type="radio" name="%s%s"%s value="%s"%s>%s</div>' % ( style, prefix, self.name, self.refresh_on_change_text, value, selected_text, text ) )
            ctr += 1
        return "\n".join( rval )    
    def get_html_default( self, prefix="" ):
        if self.multiple: multiple = " multiple"
        else: multiple = ""
        rval = [ '<select name="%s%s"%s%s>' % ( prefix, self.name, multiple, self.refresh_on_change_text ) ]
        for text, value, selected in self.options:
            if selected: selected_text = " selected"
            else: selected_text = ""
            rval.append( '<option value="%s"%s>%s</option>' % ( value, selected_text, text ) )
        rval.append( '</select>' )
        return "\n".join( rval )


class DrillDownField( BaseField ):
    """
    A hierarchical select field, which allows users to 'drill down' a tree-like set of options.
    
    >>> t = DrillDownField( "foo", multiple=True, display="checkbox", options=[{'name': 'Heading 1', 'value': 'heading1', 'options': [{'name': 'Option 1', 'value': 'option1', 'options': []}, {'name': 'Option 2', 'value': 'option2', 'options': []}, {'name': 'Heading 1', 'value': 'heading1', 'options': [{'name': 'Option 3', 'value': 'option3', 'options': []}, {'name': 'Option 4', 'value': 'option4', 'options': []}]}]}, {'name': 'Option 5', 'value': 'option5', 'options': []}] )
    >>> print t.get_html()
    <div><ul class="toolParameterExpandableCollapsable">
    <li><span class="toolParameterExpandableCollapsable">[+]</span><input type="checkbox" name="foo" value="heading1"">Heading 1
    <ul class="toolParameterExpandableCollapsable" default_state="collapsed">
    <li><input type="checkbox" name="foo" value="option1"">Option 1
    </li>
    <li><input type="checkbox" name="foo" value="option2"">Option 2
    </li>
    <li><span class="toolParameterExpandableCollapsable">[+]</span><input type="checkbox" name="foo" value="heading1"">Heading 1
    <ul class="toolParameterExpandableCollapsable" default_state="collapsed">
    <li><input type="checkbox" name="foo" value="option3"">Option 3
    </li>
    <li><input type="checkbox" name="foo" value="option4"">Option 4
    </li>
    </ul>
    </li>
    </ul>
    </li>
    <li><input type="checkbox" name="foo" value="option5"">Option 5
    </li>
    </ul></div>
    >>> t = DrillDownField( "foo", multiple=False, display="radio", options=[{'name': 'Heading 1', 'value': 'heading1', 'options': [{'name': 'Option 1', 'value': 'option1', 'options': []}, {'name': 'Option 2', 'value': 'option2', 'options': []}, {'name': 'Heading 1', 'value': 'heading1', 'options': [{'name': 'Option 3', 'value': 'option3', 'options': []}, {'name': 'Option 4', 'value': 'option4', 'options': []}]}]}, {'name': 'Option 5', 'value': 'option5', 'options': []}] )
    >>> print t.get_html()
    <div><ul class="toolParameterExpandableCollapsable">
    <li><span class="toolParameterExpandableCollapsable">[+]</span><input type="radio" name="foo" value="heading1"">Heading 1
    <ul class="toolParameterExpandableCollapsable" default_state="collapsed">
    <li><input type="radio" name="foo" value="option1"">Option 1
    </li>
    <li><input type="radio" name="foo" value="option2"">Option 2
    </li>
    <li><span class="toolParameterExpandableCollapsable">[+]</span><input type="radio" name="foo" value="heading1"">Heading 1
    <ul class="toolParameterExpandableCollapsable" default_state="collapsed">
    <li><input type="radio" name="foo" value="option3"">Option 3
    </li>
    <li><input type="radio" name="foo" value="option4"">Option 4
    </li>
    </ul>
    </li>
    </ul>
    </li>
    <li><input type="radio" name="foo" value="option5"">Option 5
    </li>
    </ul></div>
    """
    def __init__( self, name, multiple=None, display=None, refresh_on_change=False, options = [], value = [] ):
        self.name = name
        self.multiple = multiple or False
        self.options = options
        if value is not None:
            if not isinstance( value, list ): value = [ value ]
        else:
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
        if self.refresh_on_change: 
            self.refresh_on_change_text = ' refresh_on_change="true"'
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
        def recurse_options( html, options, expanded_options = [] ):
            for option in options:
                selected = ( option['value'] in self.value )
                if selected: selected = ' checked'
                else: selected = ''
                if option['options']:
                    default_state = 'collapsed'
                    default_icon = '[+]'
                    if option['value'] in expanded_options:
                        default_state = 'expanded'
                        default_icon = '[-]'
                    html.append( '<li><span class="toolParameterExpandableCollapsable">%s</span><input type="%s" name="%s%s" value="%s"%s">%s' % ( default_icon, self.display, prefix, self.name, option['value'], selected, option['name']) )
                    html.append( '<ul class="toolParameterExpandableCollapsable" default_state="%s">' % default_state )
                    recurse_options( html, option['options'], expanded_options )
                    html.append( '</ul>')
                else:
                    html.append( '<li><input type="%s" name="%s%s" value="%s"%s">%s' % ( self.display, prefix, self.name, option['value'], selected, option['name']) )
                html.append( '</li>' )
        rval = []
        rval.append( '<div><ul class="toolParameterExpandableCollapsable">' )
        expanded_options = []
        find_expanded_options( expanded_options, self.options )
        recurse_options( rval, self.options, expanded_options )
        rval.append( '</ul></div>' )
        return '\n'.join( rval )

def get_suite():
    """Get unittest suite for this module"""
    import doctest, sys
    return doctest.DocTestSuite( sys.modules[__name__] )
