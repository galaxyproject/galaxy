from __future__ import absolute_import

import logging

from galaxy import model, util
from markupsafe import escape
from galaxy.web.base.controller import BaseUIController, web, UsesFormDefinitionsMixin
from galaxy.web.form_builder import TextField, SelectField
from galaxy.web.framework.helpers import time_ago, iff, grids
from .requests_common import invalid_id_redirect

log = logging.getLogger( __name__ )


class ExternalServiceGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, external_service):
            return escape(external_service.name)

    class ExternalServiceTypeColumn( grids.TextColumn ):
        def get_value(self, trans, grid, external_service):
            try:
                return trans.app.external_service_types.all_external_service_types[ external_service.external_service_type_id ].name
            except KeyError:
                return 'Error in loading external_service type: %s' % external_service.external_service_type_id

    # Grid definition
    title = "External Services"
    template = "admin/external_service/grid.mako"
    model_class = model.ExternalService
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
        ExternalServiceTypeColumn( "External Service Type" ),
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
        grids.GridAction( "Reload external service types", dict( controller='external_service', action='reload_external_service_types' ) ),
        grids.GridAction( "Create new external service", dict( controller='external_service', action='create_external_service' ) )
    ]


class ExternalService( BaseUIController, UsesFormDefinitionsMixin ):
    external_service_grid = ExternalServiceGrid()

    @web.expose
    @web.require_admin
    def browse_external_services( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "view":
                return self.view_external_service( trans, **kwd )
            elif operation == "edit":
                return self.edit_external_service( trans, **kwd )
            elif operation == "delete":
                return self.delete_external_service( trans, **kwd )
            elif operation == "undelete":
                return self.undelete_external_service( trans, **kwd )
        # Render the grid view
        return self.external_service_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def create_external_service( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        external_service_type_id = params.get( 'external_service_type_id', 'none' )
        widgets = self.__build_external_service_widgets( trans, external_service=None, **kwd )
        external_service_type = None
        error = False
        if not trans.app.external_service_types.visible_external_service_types:
            error = True
            message = 'There are no visible external_service types in the external_service types config file'
        elif params.get( 'create_external_service_button', False ):
            if external_service_type_id == 'none':
                error = True
                message = 'Provide an external_service_type_id to create a new external service.'
            else:
                self.__save_external_service( trans, **kwd )
                message = 'The external_service has been created.'
                return trans.response.send_redirect( web.url_for( controller='external_service',
                                                                  action='browse_external_services',
                                                                  message=message,
                                                                  status=status ) )
        elif external_service_type_id != 'none':
            # Form submission via refresh_on_change
            trans.app.external_service_types.reload( external_service_type_id )
            external_service_type = self.get_external_service_type( trans, external_service_type_id )
            widgets.extend( external_service_type.form_definition.get_widgets( trans.user, **kwd ) )
        if error:
            return trans.response.send_redirect( web.url_for( controller='external_service',
                                                              action='browse_external_services',
                                                              message=message,
                                                              status='error' ) )
        return trans.fill_template( '/admin/external_service/create_external_service.mako',
                                    widgets=widgets,
                                    message=message,
                                    status=status,
                                    external_service_type=external_service_type )

    @web.expose
    @web.require_admin
    def view_external_service( self, trans, **kwd ):
        external_service_id = kwd.get( 'id', None )
        try:
            external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
        except:
            return invalid_id_redirect( trans, 'external_service', external_service_id, 'external_service', action='browse_external_services' )
        external_service_type = self.get_external_service_type( trans, external_service.external_service_type_id )
        return trans.fill_template( '/admin/external_service/view_external_service.mako',
                                    external_service=external_service,
                                    external_service_type=external_service_type )

    @web.expose
    @web.require_admin
    def edit_external_service( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        external_service_id = params.get( 'id', None )
        try:
            external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
        except:
            return invalid_id_redirect( trans, 'external_service', external_service_id, 'external_service', action='browse_external_services' )
        if params.get( 'edit_external_service_button', False ):
            external_service = self.__save_external_service( trans, **kwd )
            trans.sa_session.refresh( external_service )
            message = 'Changes made to external service (%s) have been saved' % external_service.name
        widgets = self.__build_external_service_widgets( trans, external_service, **kwd )
        widgets.extend( external_service.form_definition.get_widgets( trans.user, external_service.form_values.content, **kwd ) )
        external_service_type = self.get_external_service_type( trans, external_service.external_service_type_id )
        return trans.fill_template( '/admin/external_service/edit_external_service.mako',
                                    external_service=external_service,
                                    widgets=widgets,
                                    message=message,
                                    status=status,
                                    external_service_type=external_service_type )

    def __save_external_service( self, trans, **kwd ):
        # Here we save a newly created external_service or save changed
        # attributes of an existing external_service.
        params = util.Params( kwd )
        external_service_id = params.get( 'id', None )
        name = util.restore_text( params.get( 'external_service_name', ''  ) )
        description = util.restore_text( params.get( 'external_service_description', '' ) )
        version = util.restore_text( params.get( 'external_service_version', '' ) )
        external_service_type_id = params.get( 'external_service_type_id', '' )
        if external_service_id:
            # We're saving changed attributes of an existing external_service.
            external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
            external_service.name = name
            external_service.description = description
            external_service.version = version
            external_service.form_values.content = self.get_form_values( trans, trans.user, external_service.form_definition, **kwd )
            trans.sa_session.add( external_service )
            trans.sa_session.add( external_service.form_values )
            trans.sa_session.flush()
        else:
            # We're saving a newly created external_service
            external_service_type = self.get_external_service_type( trans, external_service_type_id )
            external_service = trans.model.ExternalService( name, description, external_service_type_id, version )
            external_service.form_definition = external_service_type.form_definition
            # Get the form values from kwd, some of which may be different than the defaults in the external service
            # type config because the user could have overwritten them.
            values = self.get_form_values( trans, trans.user, external_service.form_definition, **kwd )
            external_service.form_values = trans.model.FormValues( external_service.form_definition, values )
            trans.sa_session.add( external_service )
            trans.sa_session.add( external_service.form_definition )
            trans.sa_session.add( external_service.form_values )
            trans.sa_session.flush()
        return external_service

    @web.expose
    @web.require_admin
    def edit_external_service_form_definition( self, trans, **kwd ):
        util.Params( kwd )
        external_service_id = kwd.get( 'id', None )
        try:
            external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
        except:
            return invalid_id_redirect( trans, 'external_service', external_service_id, 'external_service', action='browse_external_services' )
        vars = dict( id=trans.security.encode_id( external_service.form_definition.form_definition_current_id ),
                     response_redirect=web.url_for( controller='external_service',
                                                    action='update_external_service_form_definition',
                                                    **kwd ) )
        return trans.response.send_redirect( web.url_for( controller='forms', action='edit_form_definition', **vars ) )

    @web.expose
    @web.require_admin
    def update_external_service_form_definition( self, trans, **kwd ):
        util.Params( kwd )
        external_service_id = kwd.get( 'id', None )
        try:
            external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
        except:
            return invalid_id_redirect( trans, 'external_service', external_service_id, 'external_service', action='browse_external_services' )
        external_service.form_definition = external_service.form_definition.current.latest_form
        trans.sa_session.add( external_service )
        trans.sa_session.flush()
        message = "The form definition for the '%s' external service has been updated with your changes." % external_service.name
        return trans.response.send_redirect( web.url_for( controller='external_service',
                                                          action='edit_external_service',
                                                          message=message,
                                                          status='done',
                                                          **kwd ) )

    @web.expose
    @web.require_admin
    def delete_external_service( self, trans, **kwd ):
        external_service_id = kwd.get( 'id', '' )
        external_service_id_list = util.listify( external_service_id )
        for external_service_id in external_service_id_list:
            try:
                external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
            except:
                return invalid_id_redirect( trans, 'external_service', external_service_id, 'external_service', action='browse_external_services' )
            external_service.deleted = True
            trans.sa_session.add( external_service )
            trans.sa_session.flush()
        message = '%i external services has been deleted' % len( external_service_id_list )
        return trans.response.send_redirect( web.url_for( controller='external_service',
                                                          action='browse_external_services',
                                                          message=message,
                                                          status='done' ) )

    @web.expose
    @web.require_admin
    def undelete_external_service( self, trans, **kwd ):
        external_service_id = kwd.get( 'id', '' )
        external_service_id_list = util.listify( external_service_id )
        for external_service_id in external_service_id_list:
            try:
                external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
            except:
                return invalid_id_redirect( trans, 'external_service', external_service_id, 'external_service', action='browse_external_services' )
            external_service.deleted = False
            trans.sa_session.add( external_service )
            trans.sa_session.flush()
        status = 'done'
        message = '%i external services have been undeleted' % len( external_service_id_list )
        return trans.response.send_redirect( web.url_for( controller='external_service',
                                                          action='browse_external_services',
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_admin
    def reload_external_service_types( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        external_service_type_id = params.get( 'external_service_type_id', 'none' )
        if params.get( 'reload_external_service_type_button', False ):
            new_external_service_type = trans.app.external_service_types.reload( external_service_type_id )
            status = 'done'
            message = 'Reloaded external service type: %s' % new_external_service_type.name
        external_service_type_select_field = self.__build_external_service_type_select_field( trans,
                                                                                              external_service_type_id,
                                                                                              refresh_on_change=False,
                                                                                              visible_external_service_types_only=False )
        if not trans.app.external_service_types.visible_external_service_types:
            message = 'There are no visible external service types in the external service types config file.'
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='external_service',
                                                              action='browse_external_services',
                                                              message=message,
                                                              status=status ) )
        return trans.fill_template( '/admin/external_service/reload_external_service_types.mako',
                                    external_service_type_select_field=external_service_type_select_field,
                                    message=message,
                                    status=status )

    def get_external_service_type(self, trans, external_service_type_id, action='browse_external_services'):
        try:
            return trans.app.external_service_types.all_external_service_types[ external_service_type_id ]
        except KeyError:
            message = 'Error in loading external service type: %s' % external_service_type_id
            return trans.response.send_redirect( web.url_for( controller='external_service',
                                                              action=action,
                                                              message=message,
                                                              status='error' ) )

    # ===== Methods for building SelectFields used on various admin_requests forms
    def __build_external_service_widgets( self, trans, external_service=None, **kwd ):
        params = util.Params( kwd )
        if external_service:
            name = external_service.name
            description = external_service.description
            version = external_service.version
            seq_type = external_service.external_service_type_id
        else:
            name = util.restore_text( params.get( 'external_service_name', ''  ) )
            description = util.restore_text( params.get( 'external_service_description', ''  ) )
            version = util.restore_text( params.get( 'external_service_version', ''  ) )
            selected_seq_type = params.get( 'external_service_type_id', ''  )
            if selected_seq_type in trans.app.external_service_types.all_external_service_types:
                seq_type = trans.app.external_service_types.all_external_service_types[ selected_seq_type ].id
            else:
                seq_type = 'none'
        widgets = [ dict( label='Name',
                          widget=TextField( 'external_service_name', 40, name ),
                          helptext='' ),
                    dict( label='Description',
                          widget=TextField( 'external_service_description', 40, description ),
                          helptext='' ),
                    dict( label='Version',
                          widget=TextField( 'external_service_version', 40, version ),
                          helptext='' ) ]
        # Do not show the external_service_type selectfield when editing a external_service
        if not external_service:
            widgets.append( dict( label='External service type',
                                  widget=self.__build_external_service_type_select_field( trans, seq_type, visible_external_service_types_only=True ),
                                  helptext='') )
        return widgets

    def __build_external_service_type_select_field( self, trans, selected_value, refresh_on_change=True, visible_external_service_types_only=False ):
        external_service_types = trans.app.external_service_types.all_external_service_types
        if visible_external_service_types_only:
            objs_list = [ external_service_types[ seq_type_id ] for seq_type_id in trans.app.external_service_types.visible_external_service_types ]
        else:
            objs_list = external_service_types.values()
        refresh_on_change_values = [ 'none' ]
        refresh_on_change_values.extend( [ trans.security.encode_id( obj.id ) for obj in objs_list] )
        select_external_service_type = SelectField( 'external_service_type_id',
                                                    refresh_on_change=refresh_on_change,
                                                    refresh_on_change_values=refresh_on_change_values )
        if selected_value == 'none':
            select_external_service_type.add_option( 'Select one', 'none', selected=True )
        else:
            select_external_service_type.add_option( 'Select one', 'none' )
        for seq_type in objs_list:
            if seq_type.version:
                option_name = " ".join( [ seq_type.name, "version", seq_type.version ] )
            else:
                option_name = seq_type.name
            if selected_value == seq_type.id:
                select_external_service_type.add_option( option_name, seq_type.id, selected=True )
            else:
                select_external_service_type.add_option( option_name, seq_type.id )
        return select_external_service_type
