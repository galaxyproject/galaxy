from galaxy.util import bunch

import logging
log = logging.getLogger( __name__ )


def form( *args, **kwargs ):
    return FormBuilder( *args, **kwargs )


class FormBuilder( object ):
    """
    Simple class describing an HTML form
    """
    def __init__( self, action="", title="", name="form", submit_text="submit", use_panels=False ):
        self.title = title
        self.name = name
        self.action = action
        self.submit_text = submit_text
        self.inputs = []
        self.use_panels = use_panels

    def add_input( self, type, name, label, value=None, error=None, help=None, use_label=True  ):
        self.inputs.append( FormInput( type, label, name, value, error, help, use_label ) )
        return self

    def add_checkbox( self, name, label, value=None, error=None, help=None  ):
        return self.add_input( 'checkbox', label, name, value, error, help )

    def add_text( self, name, label, value=None, error=None, help=None  ):
        return self.add_input( 'text', label, name, value, error, help )

    def add_password( self, name, label, value=None, error=None, help=None  ):
        return self.add_input( 'password', label, name, value, error, help )

    def add_select( self, name, label, value=None, options=[], error=None, help=None, use_label=True ):
        self.inputs.append( SelectInput( name, label, value=value, options=options, error=error, help=help, use_label=use_label   ) )
        return self


class FormInput( object ):
    """
    Simple class describing a form input element
    """
    def __init__( self, type, name, label, value=None, error=None, help=None, use_label=True, extra_attributes={}, **kwargs ):
        self.type = type
        self.name = name
        self.label = label
        self.value = value
        self.error = error
        self.help = help
        self.use_label = use_label
        self.extra_attributes = extra_attributes


class DatalistInput( FormInput ):
    """ Data list input """

    def __init__( self, name, *args, **kwargs ):
        if 'extra_attributes' not in kwargs:
            kwargs[ 'extra_attributes' ] = {}
        kwargs[ 'extra_attributes' ][ 'list' ] = name
        FormInput.__init__( self, None, name, *args, **kwargs )
        self.options = kwargs.get( 'options', {} )

    def body_html( self ):
        options = "".join( [ "<option value='%s'>%s</option>" % ( key, value ) for key, value in self.options.iteritems() ] )
        return """<datalist id="%s">%s</datalist>""" % ( self.name, options )


class SelectInput( FormInput ):
    """ A select form input. """
    def __init__( self, name, label, value=None, options=[], error=None, help=None, use_label=True ):
        FormInput.__init__( self, "select", name, label, value=value, error=error, help=help, use_label=use_label )
        self.options = options


class FormData( object ):
    """
    Class for passing data about a form to a template, very rudimentary, could
    be combined with the tool form handling to build something more general.
    """
    def __init__( self ):
        # TODO: galaxy's two Bunchs are defined differently. Is this right?
        self.values = bunch.Bunch()
        self.errors = bunch.Bunch()
