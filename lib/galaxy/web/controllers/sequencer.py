from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy import model, util
from galaxy.web.form_builder import *
from galaxy.web.controllers.requests_common import invalid_id_redirect
import logging, os

log = logging.getLogger( __name__ )

class SequencerGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, sequencer):
            return sequencer.name
    class SequencerTypeColumn( grids.TextColumn ):
        def get_value(self, trans, grid, sequencer):
            try:
                return trans.app.sequencer_types.all_sequencer_types[ sequencer.sequencer_type_id ].name
            except KeyError, e:
                return 'Error in loading sequencer type: %s' % sequencer.sequencer_type_id

    # Grid definition
    webapp = "galaxy"
    title = "Sequencer Configurations"
    template = "admin/sequencer/grid.mako"
    model_class = model.Sequencer
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict( deleted="False" )
    columns = [
        NameColumn( "Name", 
                    key="name",
                    link=( lambda item: iff( item.deleted, None, dict( operation="view", id=item.id ) ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        grids.TextColumn( "Description",
                           key='description',
                           filterable="advanced" ),
        SequencerTypeColumn( "Sequencer Type" ),
        grids.GridColumn( "Last Updated", 
                          key="update_time", 
                          format=time_ago ),
        grids.DeletedColumn( "Deleted", 
                             key="deleted", 
                             visible=False, 
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted  )  ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted  )  ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),    
    ]
    global_actions = [
        grids.GridAction( "Reload sequencer types", dict( controller='sequencer', action='reload_sequencer_types' ) ),
        grids.GridAction( "Create new sequencer", dict( controller='sequencer', action='create_sequencer' ) )
    ]
    


class Sequencer( BaseController, UsesFormDefinitions ):
    sequencer_grid = SequencerGrid()

    @web.expose
    @web.require_admin
    def browse_sequencers( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            obj_id = kwd.get( 'id', None )
            if operation == "view":
                return self.view_sequencer( trans, **kwd )
            elif operation == "edit":
                return self.edit_sequencer( trans, **kwd )
            elif operation == "delete":
                return self.delete_sequencer( trans, **kwd )
            elif operation == "undelete":
                return self.undelete_sequencer( trans, **kwd )
        # Render the grid view
        return self.sequencer_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def create_sequencer( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        sequencer_type_id = params.get( 'sequencer_type_id', 'none' )
        widgets = self.__build_sequencer_widgets( trans, sequencer=None, **kwd )
        sequencer_type = None
        if params.get( 'create_sequencer_button', False ):
            self.__save_sequencer( trans, **kwd )
            message = 'The sequencer configuration has been created.'
            return trans.response.send_redirect( web.url_for( controller='sequencer',
                                                              action='browse_sequencers',
                                                              message=message,
                                                              status=status ) )
        elif sequencer_type_id != 'none':
            trans.app.sequencer_types.reload( sequencer_type_id )
            sequencer_type = self.get_sequencer_type( trans, sequencer_type_id )
            widgets.extend( sequencer_type.form_definition.get_widgets( trans.user, **kwd ) )
        if not trans.app.sequencer_types.visible_sequencer_types:
            message = 'There are no visible sequencer types in the sequencer types config file'
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='sequencer',
                                                              action='browse_sequencers',
                                                              message=message,
                                                              status=status ) )
        return trans.fill_template( '/admin/sequencer/create_sequencer.mako',
                                    widgets=widgets,
                                    message=message,
                                    status=status,
                                    sequencer_type=sequencer_type )
    @web.expose
    @web.require_admin
    def view_sequencer( self, trans, **kwd ):
        sequencer_id = kwd.get( 'id', None )
        try:
            sequencer = trans.sa_session.query( trans.model.Sequencer ).get( trans.security.decode_id( sequencer_id ) )
        except:
            return invalid_id_redirect( trans, 'sequencer', sequencer_id, 'sequencer', action='browse_sequencers' )
        sequencer_type = self.get_sequencer_type( trans, sequencer.sequencer_type_id )
        return trans.fill_template( '/admin/sequencer/view_sequencer.mako', 
                                    sequencer=sequencer,
                                    sequencer_type=sequencer_type )
    @web.expose
    @web.require_admin
    def edit_sequencer( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        sequencer_id = params.get( 'id', None )
        try:
            sequencer = trans.sa_session.query( trans.model.Sequencer ).get( trans.security.decode_id( sequencer_id ) )
        except:
            return invalid_id_redirect( trans, 'sequencer', sequencer_id, 'sequencer', action='browse_sequencers' )
        if params.get( 'edit_sequencer_button', False ):
            sequencer = self.__save_sequencer( trans, **kwd )
            trans.sa_session.refresh( sequencer )
            message = 'Changes made to sequencer configuration (%s) have been saved' % sequencer.name
        widgets = self.__build_sequencer_widgets( trans, sequencer, **kwd )
        widgets.extend( sequencer.form_definition.get_widgets( trans.user, sequencer.form_values.content, **kwd ) )
        sequencer_type = self.get_sequencer_type( trans, sequencer.sequencer_type_id )
        return trans.fill_template( '/admin/sequencer/edit_sequencer.mako',
                                    sequencer=sequencer,
                                    widgets=widgets,
                                    message=message,
                                    status=status,
                                    sequencer_type=sequencer_type )
    def __save_sequencer( self, trans, **kwd ):
        # Here we save a newly created sequencer or save changed
        # attributes of an existing sequencer.
        params = util.Params( kwd )
        sequencer_id = params.get( 'id', None )
        name = util.restore_text( params.get( 'sequencer_name', ''  ) )
        description = util.restore_text( params.get( 'sequencer_description', '' ) )
        version = util.restore_text( params.get( 'sequencer_version', '' ) )
        sequencer_type_id = params.get( 'sequencer_type_id', '' )
        values = self.get_form_values( trans, trans.user, sequencer.form_definition, **kwd )
        if sequencer_id:
            # We're saving changed attributes of an existing sequencer.
            sequencer = trans.sa_session.query( trans.model.Sequencer ).get( trans.security.decode_id( sequencer_id ) )
            sequencer.name = name
            sequencer.description = description
            sequencer.version = version
            sequencer.form_values.content = values
            trans.sa_session.add( sequencer )
            trans.sa_session.add( sequencer.form_values )
            trans.sa_session.flush()
            sequencer.load_data_transfer_settings( trans )
        else:
            # We're saving a newly created sequencer
            sequencer_type = self.get_sequencer_type( trans, sequencer_type_id )
            sequencer = trans.model.Sequencer( name, description, sequencer_type_id, version )
            sequencer.form_definition = sequencer_type.form_definition
            sequencer.form_values = trans.model.FormValues( sequencer.form_definition, values )
            trans.sa_session.add( sequencer.form_definition )
            trans.sa_session.add( sequencer.form_values )
            trans.sa_session.add( sequencer )
            trans.sa_session.flush()
        return sequencer
    @web.expose
    @web.require_admin
    def edit_sequencer_form_definition( self, trans, **kwd ):
        params = util.Params( kwd )
        sequencer_id = kwd.get( 'id', None )
        edited = util.string_as_bool( params.get( 'edited', False ) )
        try:
            sequencer = trans.sa_session.query( trans.model.Sequencer ).get( trans.security.decode_id( sequencer_id ) )
        except:
            return invalid_id_redirect( trans, 'sequencer', sequencer_id, 'sequencer', action='browse_sequencers' )
        if edited:
            sequencer.form_definition = sequencer.form_definition.current.latest_form
            trans.sa_session.add( sequencer )
            trans.sa_session.flush()
            message = "The form definition for the '%s' sequencer has been updated with your changes." % sequencer.name
            return trans.response.send_redirect( web.url_for( controller='sequencer',
                                                              action='edit_sequencer',
                                                              message=message,
                                                              status='done',
                                                              **kwd ) )
        vars = dict( id=trans.security.encode_id( sequencer.form_definition.form_definition_current_id ),
                     response_redirect=web.url_for( controller='sequencer',
                                                    action='edit_sequencer_form_definition',
                                                    edited=True,
                                                    **kwd ) )
        return trans.response.send_redirect( web.url_for( controller='forms', action='edit_form_definition', **vars ) )
    @web.expose
    @web.require_admin
    def delete_sequencer( self, trans, **kwd ):
        sequencer_id = kwd.get( 'id', '' )
        sequencer_id_list = util.listify( sequencer_id )
        for sequencer_id in sequencer_id_list:
            try:
                sequencer = trans.sa_session.query( trans.model.Sequencer ).get( trans.security.decode_id( sequencer_id ) )
            except:
                return invalid_id_redirect( trans, 'sequencer', sequencer_id, 'sequencer', action='browse_sequencers' )
            sequencer.deleted = True
            trans.sa_session.add( sequencer )
            trans.sa_session.flush()
        status = 'done'
        message = '%i sequencers has been deleted' % len( sequencer_id_list )
        return trans.response.send_redirect( web.url_for( controller='sequencer',
                                                          action='browse_sequencers',
                                                          message=message,
                                                          status='done' ) )
    @web.expose
    @web.require_admin
    def undelete_sequencer( self, trans, **kwd ):
        sequencer_id = kwd.get( 'id', '' )
        sequencer_id_list = util.listify( sequencer_id )
        for sequencer_id in sequencer_id_list:
            try:
                sequencer = trans.sa_session.query( trans.model.Sequencer ).get( trans.security.decode_id( sequencer_id ) )
            except:
                return invalid_id_redirect( trans, 'sequencer', sequencer_id, 'sequencer', action='browse_sequencers' )
            sequencer.deleted = False
            trans.sa_session.add( sequencer )
            trans.sa_session.flush()
        status = 'done'
        message = '%i sequencers have been undeleted' % len( sequencer_id_list )
        return trans.response.send_redirect( web.url_for( controller='sequencer',
                                                          action='browse_sequencers',
                                                          message=message,
                                                          status=status ) )
    @web.expose
    @web.require_admin
    def reload_sequencer_types( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        sequencer_type_id = params.get( 'sequencer_type_id', 'none' )
        if params.get( 'reload_sequencer_type_button', False ):
            new_sequencer_type = trans.app.sequencer_types.reload( sequencer_type_id )
            status = 'done'
            message = 'Reloaded sequencer type: %s' % new_sequencer_type.name  
        sequencer_type_select_field = self.__build_sequencer_type_select_field( trans, 
                                                                                sequencer_type_id, 
                                                                                refresh_on_change=False,
                                                                                visible_sequencer_types_only=False )
        if not trans.app.sequencer_types.visible_sequencer_types:
            message = 'There are no visible sequencer types in the sequencer types config file.'
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='sequencer',
                                                              action='browse_sequencers',
                                                              message=message,
                                                              status=status ) )
        return trans.fill_template( '/admin/sequencer/reload_sequencer_types.mako', 
                                    sequencer_type_select_field=sequencer_type_select_field,
                                    message=message,
                                    status=status )
    def get_sequencer_type(self, trans, sequencer_type_id, action='browse_sequencers'):
        try:
            return trans.app.sequencer_types.all_sequencer_types[ sequencer_type_id ]
        except KeyError, e:
            message = 'Error in loading sequencer type: %s' % sequencer_type_id
            return trans.response.send_redirect( web.url_for( controller='sequencer',
                                                              action=action,
                                                              message=message,
                                                              status='error' ) )

    # ===== Methods for building SelectFields used on various admin_requests forms
    def __build_sequencer_widgets( self, trans, sequencer=None, **kwd ):
        params = util.Params( kwd )
        if sequencer:
            name = sequencer.name
            description = sequencer.description
            version = sequencer.version
            seq_type = sequencer.sequencer_type_id
        else:
            name = util.restore_text( params.get( 'sequencer_name', ''  ) )
            description = util.restore_text( params.get( 'sequencer_description', ''  ) )
            version = util.restore_text( params.get( 'sequencer_version', ''  ) )
            selected_seq_type = params.get( 'sequencer_type_id', ''  )
            if trans.app.sequencer_types.all_sequencer_types.has_key( selected_seq_type ):
                seq_type = trans.app.sequencer_types.all_sequencer_types[ selected_seq_type ].id
            else:
                seq_type = 'none'
        widgets = [ dict( label='Name',
                          widget=TextField( 'sequencer_name', 40, name ), 
                          helptext='' ),
                    dict( label='Description',
                          widget=TextField( 'sequencer_description', 40, description ), 
                          helptext='' ),
                    dict( label='Version',
                          widget=TextField( 'sequencer_version', 40, version ), 
                          helptext='' ) ]
        # Do not show the sequencer_type selectfield when editing a sequencer
        if not sequencer:
            widgets.append( dict( label='Sequencer type',
                                  widget=self.__build_sequencer_type_select_field( trans, seq_type ),
                                  helptext='') )
        return widgets
    def __build_sequencer_type_select_field( self, trans, selected_value, refresh_on_change=True, visible_sequencer_types_only=True ):
        sequencer_types = trans.app.sequencer_types.all_sequencer_types
        if visible_sequencer_types_only:
            objs_list = [ sequencer_types[ seq_type_id ] for seq_type_id in trans.app.sequencer_types.visible_sequencer_types ]
        else:
            objs_list = sequencer_types.values()
        return build_select_field( trans,
                                   objs=objs_list,
                                   label_attr='do_not_encode',
                                   select_field_name='sequencer_type_id',
                                   initial_value='none',
                                   selected_value=selected_value,
                                   refresh_on_change=refresh_on_change )
