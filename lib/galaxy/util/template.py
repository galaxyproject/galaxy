import pkg_resources
pkg_resources.require( "Cheetah" )

from Cheetah.Template import Template

def fill_template( template_text, context=None, **kwargs ):
    if not context:
        context = kwargs
    return str( Template( source=template_text, searchList=[context] ) )