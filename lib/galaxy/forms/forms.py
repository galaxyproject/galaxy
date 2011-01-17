"""
FormDefinition and field factories
"""
#TODO: A FormDefinitionField is closely linked to a form_builder result.
#Can this functionality be further abstracted and merged with form_builder?
import logging
from galaxy.util import string_as_bool
from galaxy.model import FormDefinitionCurrent, FormDefinition

FORM_TYPES = dict( [ ( f_type.lower(), f_descript ) for f_type, f_descript in FormDefinition.types.items() ] )

class FormDefinitionFactory( object ):
    def __init__( self, form_types, field_type_factories ):
        self.form_types = form_types
        self.field_type_factories = field_type_factories
    def new( self, form_type, name, description=None, fields=None, layout=None, form_definition_current=None ):
        """
        Return new FormDefinition.
        """
        assert form_type in self.form_types, 'Invalid FormDefinition type ( %s not in %s )' % ( form_type, self.form_types.keys() )
        assert name, 'FormDefinition requires a name'
        if description is None:
            description = ''
        if layout is None:
            layout = []
        if fields is None:
            fields = []
        #Create new FormDefinitionCurrent
        if form_definition_current is None:
            form_definition_current = FormDefinitionCurrent()
        
        rval = FormDefinition( name=name, desc=description, form_type=self.form_types[form_type], form_definition_current=form_definition_current, layout=layout, fields=fields )
        form_definition_current.latest_form = rval
        return rval
    def from_elem( self, elem, form_definition_current = None ):
        """
        Return FormDefinition created from an xml element.
        """
        name = elem.get( 'name', None )
        description = elem.get( 'description', None )
        form_type = elem.get( 'type', None )
        #load layout
        layout = []
        layouts_elem = elem.find( 'layout' )
        if layouts_elem:
            for layout_elem in layouts_elem.findall( 'grid' ):
                layout_name = layout_elem.get( 'name', None )
                assert layout_name and layout_name not in layout, 'Layout grid element requires a unique name.'
                layout.append( layout_name )
        #load fields
        fields = []
        fields_elem = elem.find( 'fields' )
        if fields_elem:
            for field_elem in fields_elem.findall( 'field' ):
                field_type = field_elem.get( 'type' )
                assert field_type in self.field_type_factories, 'Invalid form field type ( %s ).' % field_type
                fields.append( self.field_type_factories[field_type].from_elem( field_elem, layout ) )
        #create and return new form
        return self.new( form_type, name, description=description, fields=fields, layout=layout, form_definition_current=form_definition_current )

class FormDefinitionFieldFactory( object ):
    type = None
    def __get_stored_field_type( self, **kwds ):
        raise 'not implemented'
    def new( self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None ):
        """
        Return new FormDefinition field.
        """
        rval = {}
        assert name, 'Must provide a name'
        rval['name'] = name
        if not label:
            rval['label'] = name
        else:
            rval['label'] = label
        if required:
            rval['required'] = 'required'
        else:
            rval['required'] = 'optional'
        if helptext is None:
            helptext = ''
        rval['helptext'] = helptext
        if default is None:
            default = ''
        rval['default'] = default
        rval['visible'] = visible
        #if layout is None: #is this needed?
        #    layout = ''
        rval['layout'] = layout
        return rval
    def from_elem( self, elem, layout=None ):
        """
        Return FormDefinition created from an xml element.
        """
        name = elem.get( 'name' )
        label = elem.get( 'label' )
        required = string_as_bool( elem.get( 'required', 'false' ) )
        default = elem.get( 'value' )
        helptext = elem.get( 'helptext' )
        visible = string_as_bool( elem.get( 'visible', 'true' ) )
        field_layout = elem.get( 'layout', None )
        if field_layout:
            assert layout and field_layout in layout, 'Invalid layout specified: %s not in %s' %( field_layout, layout )
            field_layout = str( layout.index( field_layout ) ) #existing behavior: integer indexes are stored as strings. why?
        return self.new( name=name, label=label, required=required, helptext=helptext, default=default, visible=visible, layout=field_layout )

class FormDefinitionTextFieldFactory( FormDefinitionFieldFactory ):
    type = 'text'
    def __get_stored_field_type( self, area ):
        if area:
            return 'TextArea'
        else:
            return 'TextField'
    def new( self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None, area=False ):
        """
        Return new FormDefinition field.
        """
        rval = super( FormDefinitionTextFieldFactory, self ).new( name=name, label=label, required=required, helptext=helptext, default=default, visible=visible, layout=layout )
        rval['type'] = self.__get_stored_field_type( area )
        return rval
    def from_elem( self, elem, layout=None ):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super( FormDefinitionTextFieldFactory, self ).from_elem( elem, layout=layout )
        rval['type'] = self.__get_stored_field_type( string_as_bool( elem.get( 'area', 'false' ) ) )
        return rval
    
class FormDefinitionPasswordFieldFactory( FormDefinitionFieldFactory ):
    type = 'password'
    def __get_stored_field_type( self ):
        return 'PasswordField'
    def new( self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None, area=False ):
        """
        Return new FormDefinition field.
        """
        rval = super( FormDefinitionPasswordFieldFactory, self ).new( name=name, label=label, required=required, helptext=helptext, default=default, visible=visible, layout=layout )
        rval['type'] = self.__get_stored_field_type()
        return rval
    def from_elem( self, elem, layout=None ):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super( FormDefinitionPasswordFieldFactory, self ).from_elem( elem, layout=layout )
        rval['type'] = self.__get_stored_field_type()
        return rval
    
class FormDefinitionAddressFieldFactory( FormDefinitionFieldFactory ):
    type = 'address'
    def __get_stored_field_type( self ):
        return 'AddressField'
    def new( self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None ):
        """
        Return new FormDefinition field.
        """
        rval = super( FormDefinitionAddressFieldFactory, self ).new( name=name, label=label, required=required, helptext=helptext, default=default, visible=visible, layout=layout )
        rval['type'] = self.__get_stored_field_type()
        return rval
    def from_elem( self, elem, layout=None ):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super( FormDefinitionAddressFieldFactory, self ).from_elem( elem, layout=layout )
        rval['type'] = self.__get_stored_field_type()
        return rval

class FormDefinitionWorkflowFieldFactory( FormDefinitionFieldFactory ):
    type = 'workflow'
    def __get_stored_field_type( self ):
        return 'WorkflowField'
    def new( self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None ):
        """
        Return new FormDefinition field.
        """
        rval = super( FormDefinitionWorkflowFieldFactory, self ).new( name=name, label=label, required=required, helptext=helptext, default=default, visible=visible, layout=layout )
        rval['type'] = self.__get_stored_field_type()
        return rval
    def from_elem( self, elem, layout=None ):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super( FormDefinitionWorkflowFieldFactory, self ).from_elem( elem, layout=layout )
        rval['type'] = self.__get_stored_field_type( area )
        return rval

class FormDefinitionWorkflowMappingFieldFactory( FormDefinitionFieldFactory ):
    type = 'workflowmapping'
    def __get_stored_field_type( self ):
        return 'WorkflowMappingField'
    def new( self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None ):
        """
        Return new FormDefinition field.
        """
        rval = super( FormDefinitionWorkflowMappingFieldFactory, self ).new( name=name, label=label, required=required, helptext=helptext, default=default, visible=visible, layout=layout )
        rval['type'] = self.__get_stored_field_type()
        return rval
    def from_elem( self, elem, layout=None ):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super( FormDefinitionWorkflowMappingFieldFactory, self ).from_elem( elem, layout=layout )
        rval['type'] = self.__get_stored_field_type( area )
        return rval

class FormDefinitionHistoryFieldFactory( FormDefinitionFieldFactory ):
    type = 'history'
    def __get_stored_field_type( self ):
        return 'HistoryField'
    def new( self, label=None, required=False, helptext=None, default=None, visible=True, layout=None ):
        """
        Return new FormDefinition field.
        """
        rval = super( FormDefinitionHistoryFieldFactory, self ).new( name=name, label=label, required=required, helptext=helptext, default=default, visible=visible, layout=layout )
        rval['type'] = self.__get_stored_field_type()
        return rval
    def from_elem( self, elem, layout=None ):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super( FormDefinitionHistoryFieldFactory, self ).from_elem( elem, layout=layout )
        rval['type'] = self.__get_stored_field_type( area )
        return rval

class FormDefinitionSelectFieldFactory( FormDefinitionFieldFactory ):
    type = 'select'
    def __get_stored_field_type( self, checkboxes ):
        if checkboxes:
            return 'CheckboxField'
        else:
            return 'SelectField'
    def new( self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None, options=[], checkboxes=False ):
        """
        Return new FormDefinition field.
        """
        rval = super( FormDefinitionSelectFieldFactory, self ).new( name=name, label=label, required=required, helptext=helptext, default=default, visible=visible, layout=layout )
        rval['type'] = self.__get_stored_field_type( checkboxes )
        if options is None:
            options = []
        rval['selectlist'] = options
        return rval
    def from_elem( self, elem, layout=None ):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super( FormDefinitionSelectFieldFactory, self ).from_elem( elem, layout=layout )
        rval['type'] = self.__get_stored_field_type( string_as_bool( elem.get( 'checkboxes', 'false' ) ) )
        #load select options
        rval['selectlist'] = []
        for select_option in elem.findall( 'option' ):
            value = select_option.get( 'value', None )
            assert value is not None, 'Must provide a "value" for a select option'
            rval['selectlist'].append( value )
        return rval

field_type_factories = dict( [ ( field.type, field() ) for field in ( FormDefinitionTextFieldFactory, FormDefinitionPasswordFieldFactory, FormDefinitionAddressFieldFactory, FormDefinitionSelectFieldFactory, FormDefinitionWorkflowFieldFactory, FormDefinitionWorkflowMappingFieldFactory, FormDefinitionHistoryFieldFactory ) ] )

form_factory = FormDefinitionFactory( FORM_TYPES, field_type_factories )
