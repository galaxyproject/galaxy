"""
Classes for generating HTML forms
"""

import logging, util

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
    <input type="checkbox" name="foo" value="true"><input type="hidden" name="foo" value="true">
    >>> print CheckboxField( "bar", checked="yes" ).get_html()
    <input type="checkbox" name="bar" value="true" checked><input type="hidden" name="bar" value="true">
    """
    def __init__( self, name, checked=None ):
        if checked is None: checked = False
        self.name = name
        self.checked = ( checked in ( True, "yes", "true", "on" ) )
    def get_html( self, prefix="" ):
        if self.checked: checked_text = " checked"
        else: checked_text = ""
        return '<input type="checkbox" name="%s%s" value="true"%s><input type="hidden" name="%s" value="true">' \
            % ( prefix, self.name, checked_text, self.name )
    @staticmethod
    def is_checked( value ):
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
    def add_option( self, text, value, selected = False ):
        self.options.append( ( text, value, selected ) )
    def get_html( self, prefix="" ):
        if self.display == "checkboxes":
            return self.get_html_checkboxes( prefix )
        elif self.display == "radio":
            return self.get_html_radio( prefix)
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
            if selected:
                rval.append( '<div%s><input type="radio" name="%s%s" value="%s" checked>%s</div>' % ( style, prefix, self.name, value, text) )
            else:
                rval.append( '<div%s><input type="radio" name="%s%s" value="%s">%s</div>' % ( style, prefix, self.name, value, text) )
            ctr += 1
        return "\n".join( rval )    
    def get_html_default( self, prefix="" ):
        if self.multiple: multiple = " multiple"
        else: multiple = ""
        if self.refresh_on_change:
            rval = [ '<select name="%s%s"%s onchange="document.forms[0].submit();">' % ( prefix, self.name, multiple ) ]
        else:
            rval = [ '<select name="%s%s"%s>' % ( prefix, self.name, multiple ) ]
        for text, value, selected in self.options:
            if selected: selected_text = " selected"
            else: selected_text = ""
            rval.append( '<option value="%s"%s>%s</option>' % ( value, selected_text, text ) )
        rval.append( '</select>' )
        return "\n".join( rval )

def get_suite():
    """Get unittest suite for this module"""
    import doctest, sys
    return doctest.DocTestSuite( sys.modules[__name__] )
