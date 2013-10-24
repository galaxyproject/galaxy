import logging
from galaxy.web.form_builder import SelectField

log = logging.getLogger( __name__ )

UNRESTRICTED = 'unrestricted'
TOOL_DEPENDENCY_DEFINITION = 'tool_dependency_definition'

types = [ UNRESTRICTED, TOOL_DEPENDENCY_DEFINITION ]

def build_repository_type_select_field( trans, repository=None, name='repository_type' ):
    """Called from the Tool Shed to generate the current list of supported repository types."""
    if repository:
        selected_type = str( repository.type )
    else:
        selected_type = None
    repository_type_select_field = SelectField( name=name )
    for type_label, type_class in trans.app.repository_types_registry.repository_types_by_label.items():
        option_label = str( type_class.label )
        option_value = str( type_class.type )
        if selected_type and selected_type == option_value:
            selected = True
        else:
            selected = False
        if repository:
            if repository.type == option_value:
                repository_type_select_field.add_option( option_label, option_value, selected=selected )
            elif type_class.is_valid_for_type( trans.app, repository ):
                repository_type_select_field.add_option( option_label, option_value, selected=selected )
        else:
            repository_type_select_field.add_option( option_label, option_value, selected=selected )
    return repository_type_select_field
