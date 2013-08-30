#Contains objects for accessing external services applications
import logging
from parameters import ExternalServiceParameter
from actions import ExternalServiceAction
from galaxy.util.bunch import Bunch

log = logging.getLogger( __name__ )


class ExternalServiceActionsGroup( object ):
    def __init__( self, parent, name, label=None ):
        self.name = name
        self.label = label
        self.parent = parent
        self.items = []
    @classmethod
    def from_elem( self, elem, parent = None ):
        """
        Return ExternalServiceActionsGroup created from an xml element.
        """
        if elem is not None:
            name = elem.get( 'name' )
            label = elem.get( 'label' )
            rval = ExternalServiceActionsGroup( parent, name, label=label )
            rval.load_sub_elems( elem )
        else:
            rval = ExternalServiceActionsGroup( None, None )
        return rval
    def load_sub_elems( self, elem ):
        for sub_elem in elem:
            if sub_elem.tag == 'param':
                self.add_item( ExternalServiceParameter.from_elem( sub_elem, self ) )
            elif sub_elem.tag == 'action':
                self.add_item( ExternalServiceAction.from_elem( sub_elem, self ) )
            elif sub_elem.tag == 'section':
                self.add_item( ExternalServiceActionsGroup.from_elem( sub_elem, self ) )
            elif sub_elem.tag == 'conditional':
                self.add_item( ExternalServiceActionsConditional( sub_elem, self ) )
            else:
                raise ValueError( 'Unknown tag: %s' % sub_elem.tag )
    def add_item( self, item ):
        self.items.append( item )
    def populate( self, service_instance, item = None, param_dict = None ):
        return PopulatedExternalService( self, service_instance, item, param_dict )
    def prepare_actions( self, param_dict, parent_dict, parent_section ):
        group = Bunch()
        group_section = ActionSection( self.name, self.label )
        parent_section.append( group_section )
        parent_dict[ self.name ] = group
        for item in self.items:
            if isinstance( item, ExternalServiceParameter ):
                group[ item.name ] = item.get_value( param_dict )
            elif isinstance( item, ExternalServiceActionsGroup ):
                group[ item.name ] = item.prepare_actions( param_dict, group, group_section )
            elif isinstance( item, ExternalServiceAction ):
                group_section.append( item.populate_action( param_dict ) )
            elif isinstance( item, ExternalServiceActionsConditional ):
                conditional_group = Bunch()
                conditional_group_section = ActionSection( item.name, item.label )#[]
                group_section.append( conditional_group_section )
                group[ item.name ] = conditional_group
                for case in item.get_current_cases( param_dict ):
                    conditional_group[ case.name ] = case.prepare_actions( param_dict, conditional_group, conditional_group_section )
            else:
                raise TypeError( 'unknown item type found: %s' % item )
        return group

class ExternalServiceActionsGroupWhen( ExternalServiceActionsGroup ):
    type="when"
    @classmethod
    def from_elem( self, parent, elem ):
        """Loads the proper when by attributes of elem"""
        when_type = elem.get( 'type' )
        assert when_type in when_type_to_class, TypeError( "When type not implemented: %s" % when_type )
        return when_type_to_class[ when_type ].from_elem( parent, elem )
    def is_case( self, param_dict ):
        raise TypeError( "Abstract method" )
    def get_ref( self, param_dict ):
        ref = param_dict
        for ref_name in self.parent.ref:
            assert ref_name in ref, "Required dependency '%s' not found in incoming values" % ref_name
            ref = ref.get( ref_name )
        return ref

class ValueExternalServiceActionsGroupWhen( ExternalServiceActionsGroupWhen ):
    type = "value"
    def __init__( self, parent, name, value, label=None ):
        super( ValueExternalServiceActionsGroupWhen, self ).__init__( parent, name, label )
        self.value = value
    @classmethod
    def from_elem( self, parent, elem ):
        """Returns an instance of this when"""
        rval = ValueExternalServiceActionsGroupWhen( parent, elem.get( 'name' ), elem.get( 'value' ), elem.get( 'label' ) )
        rval.load_sub_elems( elem )
        return rval
    def is_case( self, param_dict ):
        ref = self.get_ref( param_dict )
        return bool( str( ref ) == self.value )

class BooleanExternalServiceActionsGroupWhen( ExternalServiceActionsGroupWhen ):
    type = "boolean"
    def __init__( self, parent, name, value, label=None ):
        super( BooleanExternalServiceActionsGroupWhen, self ).__init__( parent, name, label )
        self.value = value
    @classmethod
    def from_elem( self, parent, elem ):
        """Returns an instance of this when"""
        rval = BooleanExternalServiceActionsGroupWhen( parent, elem.get( 'name' ), elem.get( 'label' ) )
        rval.load_sub_elems( elem )
        return rval
    def is_case( self, param_dict ):
        ref = self.get_ref( param_dict )
        return bool( ref )

class ItemIsInstanceExternalServiceActionsGroupWhen( ExternalServiceActionsGroupWhen ):
    type = "item_type"
    def __init__( self, parent, name, value, label=None ):
        super( ItemIsInstanceExternalServiceActionsGroupWhen, self ).__init__( parent, name, label )
        self.value = value
    @classmethod
    def from_elem( self, parent, elem ):
        """Returns an instance of this when"""
        rval = ItemIsInstanceExternalServiceActionsGroupWhen( parent, elem.get( 'name' ), elem.get( 'value' ), elem.get( 'label' ) )
        rval.load_sub_elems( elem )
        return rval
    def is_case( self, param_dict ):
        ref = self.get_ref( param_dict )
        return ref.__class__.__name__.lower() in map( lambda x: x.lower(), self.value.split( '.' ) ) #HACK!

when_type_to_class = {}
for class_type in [ ValueExternalServiceActionsGroupWhen, BooleanExternalServiceActionsGroupWhen, ItemIsInstanceExternalServiceActionsGroupWhen]:
    when_type_to_class[ class_type.type ] = class_type

class ExternalServiceActionsConditional( object ):
    type = "conditional"
    def __init__( self, elem, parent ):
        self.parent = parent
        self.name = elem.get( 'name', None )
        assert self.name is not None, "Required 'name' attribute missing from ExternalServiceActionsConditional"
        self.label = elem.get( 'label' )
        self.ref = elem.get( 'ref', None )
        assert self.ref is not None, "Required 'ref' attribute missing from ExternalServiceActionsConditional"
        self.ref = self.ref.split( '.' )
        self.cases = []
        for when_elem in elem.findall( 'when' ):
            self.cases.append( ExternalServiceActionsGroupWhen.from_elem( self, when_elem ) )
    def get_current_cases( self, param_dict ):
        rval = []
        for case in self.cases:
            if case.is_case( param_dict ):
                rval.append( case )
        return rval

class ActionSection( list ):
    def __init__( self, name, label ):
        list.__init__( self )
        self.name = name
        self.label = label
    def has_action( self ):
        for item in self:
            if not isinstance( item, ActionSection ):
                return True
            else:
                if item.has_action():
                    return True
        return False

class PopulatedExternalService( object ):
    def __init__( self, service_group, service_instance, item, param_dict = None ):
        self.service_group = service_group
        self.service_instance = service_instance
        self.item = item
        self.param_dict = param_dict
        self.populate()
    def __getattr__( self, name ):
        return getattr( self.service_instance, name )#should .service or.service_instance should be here...
    def populate( self ):
        param_dict = {}
        param_dict['fields'] = Bunch( **self.service_instance.form_values.content )
        param_dict['item'] = self.item
        param_dict['service'] = self.service_group.parent
        param_dict['service_instance'] = self.service_instance
        action_list = ActionSection( self.service_group.name, self.service_group.label )
        for item in self.service_group.items:
            if isinstance( item, ExternalServiceParameter ):
                param_dict[ item.name ] = item.get_value( param_dict )
            elif isinstance( item, ExternalServiceAction ):
                action_list.append( item.populate_action( param_dict ) )
            elif isinstance( item, ExternalServiceActionsGroup ):
                item.prepare_actions( param_dict, param_dict, action_list )
            else:
                raise 'unknown item type found'
        self.param_dict = param_dict
        self.actions = action_list
    def perform_action_by_name( self, actions_list ):
        action = self.get_action_by_name( actions_list )
        result = action.perform_action()
        return action
    def get_action_by_name( self, actions_list ):
        action = None
        actions = self.actions #populated actions
        for name in actions_list:
            action_found = False
            for action in actions:
                if action.name == name:
                    action_found = True
                    actions = action
                    break
            assert action_found, 'Action not found: %s in %s' % ( name, actions_list )
        assert action, 'Action not found: %s' % actions_list
        return action

    def get_action_links( self ):
        rval = []
        param_dict = {}
        param_dict['fields'] = Bunch( **self.service_instance.form_values.content )
        param_dict['item'] = self.item
        for item in self.service.items:
            if isinstance( item, ExternalServiceParameter ):
                param_dict[ item.name ] = item.get_value( param_dict )
            elif isinstance( item, ExternalServiceAction ):
                rval.append( item.get_action_access_link( self.item, trans, param_dict ) )
            elif isinstance( item, ExternalServiceActionsGroup ):
                rval.extend( item.populate( self.service_instance, item, param_dict ).get_action_links() )
            else:
                raise 'unknown item type found'
    def __nonzero__( self ):
        return self.actions.has_action()
