import logging
from galaxy.web.form_builder import SelectField

log = logging.getLogger( __name__ )

REPOSITORY_DEPENDENCY_DEFINITION_FILENAME = 'repository_dependencies.xml'
REPOSITORY_SUITE_DEFINITION = 'repository_suite_definition'
TOOL_DEPENDENCY_DEFINITION = 'tool_dependency_definition'
TOOL_DEPENDENCY_DEFINITION_FILENAME = 'tool_dependencies.xml'
UNRESTRICTED = 'unrestricted'

types = [ UNRESTRICTED, TOOL_DEPENDENCY_DEFINITION, REPOSITORY_SUITE_DEFINITION ]

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

def generate_message_for_repository_type_change( app, repository ):
    message = ''
    if repository.can_change_type_to( app, REPOSITORY_SUITE_DEFINITION ):
        repository_suite_definition_type_class = \
            app.repository_types_registry.get_class_by_label( REPOSITORY_SUITE_DEFINITION )
        message += "This repository currently contains a single file named <b>%s</b>.  If the intent of this repository is " % \
            REPOSITORY_DEPENDENCY_DEFINITION_FILENAME
        message += "to define relationships to a collection of repositories that contain related Galaxy utilities with "
        message += "no plans to add additional files, consider setting its type to <b>%s</b>.<br/>" % \
            repository_suite_definition_type_class.label
    elif repository.can_change_type_to( app, TOOL_DEPENDENCY_DEFINITION ):
        tool_dependency_definition_type_class = \
            app.repository_types_registry.get_class_by_label( TOOL_DEPENDENCY_DEFINITION )
        message += "This repository currently contains a single file named <b>%s</b>.  If additional files will " % \
            TOOL_DEPENDENCY_DEFINITION_FILENAME
        message += "not be added to this repository, consider setting its type to <b>%s</b>.<br/>" % \
            tool_dependency_definition_type_class.label
    return message
