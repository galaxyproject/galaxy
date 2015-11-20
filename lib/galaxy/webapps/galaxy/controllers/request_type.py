from __future__ import absolute_import

import logging

from sqlalchemy import false
from markupsafe import escape

from galaxy import model, util
from galaxy.web.base.controller import BaseUIController, UsesFormDefinitionsMixin, web
from galaxy.web.form_builder import build_select_field, TextField
from galaxy.web.framework.helpers import iff, grids
from .requests_common import invalid_id_redirect

log = logging.getLogger( __name__ )


class RequestTypeGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return escape(request_type.name)

    class DescriptionColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return escape(request_type.desc)

    class RequestFormColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return escape(request_type.request_form.name)

    class SampleFormColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return escape(request_type.sample_form.name)

    class ExternalServiceColumn( grids.IntegerColumn ):
        def get_value(self, trans, grid, request_type):
            if request_type.external_services:
                return len( request_type.external_services )
            return 'No external service assigned'
    # Grid definition
    title = "Request Types"
    template = "admin/request_type/grid.mako"
    model_class = model.RequestType
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict( deleted="False" )
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: iff( item.deleted, None, dict( operation="view_request_type", id=item.id ) ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='desc',
                           filterable="advanced" ),
        RequestFormColumn( "Request Form",
                           link=( lambda item: iff( item.deleted, None, dict( operation="view_form_definition", id=item.request_form.id ) ) ) ),
        SampleFormColumn( "Sample Form",
                          link=( lambda item: iff( item.deleted, None, dict( operation="view_form_definition", id=item.sample_form.id ) ) ) ),
        ExternalServiceColumn( "External Services" ),
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
        grids.GridOperation( "Edit request type", allow_multiple=False, condition=( lambda item: not item.deleted ) ),
        grids.GridOperation( "Edit permissions", allow_multiple=False, condition=( lambda item: not item.deleted ) ),
        grids.GridOperation( "Use run details template", allow_multiple=False, condition=( lambda item: not item.deleted and not item.run_details ) ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted ) ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),
    ]
    global_actions = [
        grids.GridAction( "Create new request type", dict( controller='request_type', action='create_request_type' ) )
    ]


class RequestType( BaseUIController, UsesFormDefinitionsMixin ):
    request_type_grid = RequestTypeGrid()

    @web.expose
    @web.require_admin
    def browse_request_types( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            obj_id = kwd.get( 'id', None )
            if operation == "view_form_definition":
                return self.view_form_definition( trans, **kwd )
            elif operation == "view_request_type":
                return self.view_request_type( trans, **kwd )
            elif operation == "use run details template":
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='add_template',
                                                                  cntrller='requests_admin',
                                                                  item_type='request_type',
                                                                  form_type=trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE,
                                                                  request_type_id=obj_id ) )
            elif operation == "edit request type":
                return self.view_editable_request_type( trans, **kwd )
            elif operation == "delete":
                return self.delete_request_type( trans, **kwd )
            elif operation == "undelete":
                return self.undelete_request_type( trans, **kwd )
            elif operation == "edit permissions":
                return self.request_type_permissions( trans, **kwd )
            elif operation == "view_external_service":
                return trans.response.send_redirect( web.url_for( controller='external_service',
                                                                  action='view_external_service',
                                                                  **kwd ) )
        # Render the grid view
        return self.request_type_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def create_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        rt_info_widgets, rt_states_widgets = self.__get_populated_request_type_widgets( trans, **kwd )
        external_service_select_fields_list = []
        # get all the external services selected till now
        external_services_list = self.__get_external_services( trans, **kwd )
        for index, external_service in enumerate( external_services_list ):
            external_service_select_field = self.__build_external_service_select_field( trans,
                                                                                        'external_service_id_%i' % index,
                                                                                        external_service )
            external_service_select_fields_list.append( external_service_select_field )
        if params.get( 'add_state_button', False ):
            # Append a new tuple to the set of states which will result in
            # empty state name and description TextFields being displayed on
            # the form.
            rt_states_widgets.append( ( "", "" ) )
        elif params.get( 'remove_state_button', False ):
            index = int( params.get( 'remove_state_button', '' ).split( " " )[2] )
            del rt_states_widgets[ index - 1 ]
        elif params.get( 'add_external_service_button', False ):
            # create a new one
            external_service_select_field = self.__build_external_service_select_field( trans,
                                                                                        'external_service_id_%i' % len( external_services_list ) )
            external_service_select_fields_list.append( external_service_select_field )
        elif params.get( 'create_request_type_button', False ):
            self.__save_request_type( trans, action='create_request_type', **kwd )
            message = 'The request type has been created.'
            return trans.response.send_redirect( web.url_for( controller='request_type',
                                                              action='browse_request_types',
                                                              message=message,
                                                              status=status ) )
        # A request_type requires at least one possible sample state so that
        # it can be used to create a sequencing request
        if not len( rt_states_widgets ):
            rt_states_widgets.append( ( "New", "First sample state" ) )
        return trans.fill_template( '/admin/request_type/create_request_type.mako',
                                    rt_info_widgets=rt_info_widgets,
                                    rt_states_widgets=rt_states_widgets,
                                    external_service_select_fields_list=external_service_select_fields_list,
                                    message=message,
                                    status=status )

    def __get_external_services(self, trans, request_type=None, **kwd):
        params = util.Params( kwd )
        external_services_list = []
        i = 0
        while True:
            if 'external_service_id_%i' % i in kwd:
                id = params.get( 'external_service_id_%i' % i, '' )
                try:
                    external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( id ) )
                except:
                    return invalid_id_redirect( trans, 'request_type', id, 'external service', action='browse_request_types' )
                external_services_list.append( external_service )
                i += 1
            else:
                break
        return external_services_list

    @web.expose
    @web.require_admin
    def view_editable_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_type_id = params.get( 'id', None )
        try:
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
        # See if we have any associated templates
        widgets = request_type.get_template_widgets( trans )
        widget_fields_have_contents = self.widget_fields_have_contents( widgets )
        # get all the external services selected till now
        external_service_select_fields_list = []
        for index, external_service in enumerate( request_type.external_services ):
            external_service_select_field = self.__build_external_service_select_field( trans,
                                                                                        'external_service_id_%i' % index,
                                                                                        external_service )
            external_service_select_fields_list.append( external_service_select_field )
        return trans.fill_template( '/admin/request_type/edit_request_type.mako',
                                    request_type=request_type,
                                    widgets=widgets,
                                    widget_fields_have_contents=widget_fields_have_contents,
                                    external_service_select_fields_list=external_service_select_fields_list,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def edit_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_type_id = params.get( 'id', None )
        try:
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
        # See if we have any associated templates
        widgets = request_type.get_template_widgets( trans )
        widget_fields_have_contents = self.widget_fields_have_contents( widgets )
        # get all the external services selected till now
        external_service_select_fields_list = []
        external_services_list = self.__get_external_services( trans, request_type, **kwd )
        if params.get( 'edit_request_type_button', False ):
            request_type = self.__save_request_type( trans, action='edit_request_type', **kwd )
            message = 'Changes made to request type (%s) have been saved' % request_type.name
        elif params.get( 'add_external_service_button', False ):
            external_services_list.append( None )
        elif params.get( 'remove_external_service_button', False ):
            index = int( kwd[ 'remove_external_service_button' ].split(' ')[3] ) - 1
            del external_services_list[index]
        for index, external_service in enumerate( external_services_list ):
            external_service_select_field = self.__build_external_service_select_field( trans,
                                                                                        'external_service_id_%i' % index,
                                                                                        external_service )
            external_service_select_fields_list.append( external_service_select_field )
        return trans.fill_template( '/admin/request_type/edit_request_type.mako',
                                    request_type=request_type,
                                    widgets=widgets,
                                    widget_fields_have_contents=widget_fields_have_contents,
                                    external_service_select_fields_list=external_service_select_fields_list,
                                    message=message,
                                    status=status )

    def __save_request_type( self, trans, action, **kwd ):
        # Here we save a newly created request_type or save changed
        # attributes of an existing request_type.
        params = util.Params( kwd )
        request_type_id = params.get( 'id', None )
        name = util.restore_text( params.get( 'name', ''  ) )
        desc = util.restore_text( params.get( 'desc', '' ) )
        request_form_id = params.get( 'request_form_id', 'none' )
        sample_form_id = params.get( 'sample_form_id', 'none' )
        # validate
        if not name or request_form_id == 'none' or sample_form_id == 'none':
            message = 'Enter the name, request form, sample form and at least one sample state associated with this request type.'
            return trans.response.send_redirect( web.url_for( controller='request_type',
                                                              action=action,
                                                              message=message,
                                                              status='error' ) )
        try:
            request_form = trans.sa_session.query( trans.model.FormDefinition ).get( trans.security.decode_id( request_form_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'form definition', action='browse_request_types' )

        try:
            sample_form = trans.sa_session.query( trans.model.FormDefinition ).get( trans.security.decode_id( sample_form_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'form definition', action='browse_request_types' )
        if request_type_id:
            # We're saving changed attributes of an existing request_type.
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
            request_type.name = name
            request_type.desc = desc
            request_type.request_form = request_form
            request_type.sample_form = sample_form
            for sample_state in request_type.states:
                sample_state_id = trans.security.encode_id( sample_state.id )
                name = util.restore_text( params.get( 'state_name_%s' % sample_state_id, '' ) )
                desc = util.restore_text( params.get( 'state_desc_%s' % sample_state_id, '' ) )
                sample_state.name = name
                sample_state.desc = desc
                trans.sa_session.add( sample_state )
                trans.sa_session.flush()
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
        else:
            # We're saving a newly created request_type
            request_type = trans.model.RequestType( name=name,
                                                    desc=desc,
                                                    request_form=request_form,
                                                    sample_form=sample_form )
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
            i = 0
            while True:
                if 'state_name_%i' % i in kwd:
                    name = util.restore_text( params.get( 'state_name_%i' % i, '' ) )
                    desc = util.restore_text( params.get( 'state_desc_%i' % i, '' ) )
                    sample_state = trans.model.SampleState( name, desc, request_type )
                    trans.sa_session.add( sample_state )
                    trans.sa_session.flush()
                    i += 1
                else:
                    break
        # delete existing associations
        request_type.delete_external_service_associations( trans )
        # save the external services associated with this request_type
        external_services_list = self.__get_external_services( trans, **kwd )
        for external_service in external_services_list:
            request_type.add_external_service_association( trans, external_service )
        return request_type

    def __get_populated_request_type_widgets( self, trans, **kwd ):
        request_form_definitions = self.get_all_forms( trans,
                                                       filter=dict( deleted=False ),
                                                       form_type=trans.model.FormDefinition.types.REQUEST )
        sample_form_definitions = self.get_all_forms( trans,
                                                      filter=dict( deleted=False ),
                                                      form_type=trans.model.FormDefinition.types.SAMPLE )
        if not request_form_definitions or not sample_form_definitions:
            return [], []
        params = util.Params( kwd )
        request_form_id = params.get( 'request_form_id', 'none' )
        sample_form_id = params.get( 'sample_form_id', 'none' )
        request_form_id_select_field = build_select_field( trans,
                                                           objs=request_form_definitions,
                                                           label_attr='name',
                                                           select_field_name='request_form_id',
                                                           selected_value=request_form_id,
                                                           refresh_on_change=False )
        sample_form_id_select_field = build_select_field( trans,
                                                          objs=sample_form_definitions,
                                                          label_attr='name',
                                                          select_field_name='sample_form_id',
                                                          selected_value=sample_form_id,
                                                          refresh_on_change=False )
        rt_info_widgets = [ dict( label='Name',
                                  widget=TextField( 'name', 40, util.restore_text( params.get( 'name', '' ) ) ) ),
                            dict( label='Description',
                                  widget=TextField( 'desc', 40, util.restore_text( params.get( 'desc', '' ) ) ) ),
                            dict( label='Request form',
                                  widget=request_form_id_select_field ),
                            dict( label='Sample form',
                                  widget=sample_form_id_select_field ) ]
        # Unsaved sample states being defined for this request type
        rt_states = []
        i = 0
        while True:
            if 'state_name_%i' % i in kwd:
                rt_states.append( ( util.restore_text( params.get( 'state_name_%i' % i, ''  ) ),
                                    util.restore_text( params.get( 'state_desc_%i' % i, ''  ) ) ) )
                i += 1
            else:
                break
        return rt_info_widgets, rt_states

    @web.expose
    @web.require_admin
    def view_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_type_id = kwd.get( 'id', None )
        try:
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
        # See if we have any associated templates
        widgets = request_type.get_template_widgets( trans )
        widget_fields_have_contents = self.widget_fields_have_contents( widgets )
        return trans.fill_template( '/admin/request_type/view_request_type.mako',
                                    request_type=request_type,
                                    widgets=widgets,
                                    widget_fields_have_contents=widget_fields_have_contents,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def delete_request_type( self, trans, **kwd ):
        request_type_id = kwd.get( 'id', '' )
        request_type_id_list = util.listify( request_type_id )
        for request_type_id in request_type_id_list:
            try:
                request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
            except:
                return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
            request_type.deleted = True
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
        message = '%i request types has been deleted' % len( request_type_id_list )
        return trans.response.send_redirect( web.url_for( controller='request_type',
                                                          action='browse_request_types',
                                                          message=message,
                                                          status='done' ) )

    @web.expose
    @web.require_admin
    def undelete_request_type( self, trans, **kwd ):
        request_type_id = kwd.get( 'id', '' )
        request_type_id_list = util.listify( request_type_id )
        for request_type_id in request_type_id_list:
            try:
                request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
            except:
                return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
            request_type.deleted = False
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
        status = 'done'
        message = '%i request types have been undeleted' % len( request_type_id_list )
        return trans.response.send_redirect( web.url_for( controller='request_type',
                                                          action='browse_request_types',
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_admin
    def request_type_permissions( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_type_id = kwd.get( 'id', '' )
        try:
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
        roles = trans.sa_session.query( trans.model.Role ) \
                                .filter( trans.model.Role.table.c.deleted == false() ) \
                                .order_by( trans.model.Role.table.c.name )
        if params.get( 'update_roles_button', False ):
            permissions = {}
            for k, v in trans.model.RequestType.permitted_actions.items():
                in_roles = [ trans.sa_session.query( trans.model.Role ).get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
            trans.app.security_agent.set_request_type_permissions( request_type, permissions )
            trans.sa_session.refresh( request_type )
            message = "Permissions updated for request type '%s'" % request_type.name
        return trans.fill_template( '/admin/request_type/request_type_permissions.mako',
                                    request_type=request_type,
                                    roles=roles,
                                    status=status,
                                    message=message )

    @web.expose
    @web.require_admin
    def view_form_definition( self, trans, **kwd ):
        form_definition_id = kwd.get( 'id', None )
        try:
            form_definition = trans.sa_session.query( trans.model.FormDefinition ).get( trans.security.decode_id( form_definition_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', form_definition_id, 'form definition', action='browse_request_types' )
        return trans.fill_template( '/admin/forms/view_form_definition.mako',
                                    form_definition=form_definition )

    # ===== Methods for building SelectFields used on various admin_requests forms
    def __build_external_service_select_field( self, trans, select_field_name, external_service=None ):
        if external_service:
            selected_value = trans.security.encode_id( external_service.id )
        else:
            selected_value = 'none'
        all_external_services = trans.sa_session.query( trans.model.ExternalService ).filter( trans.model.ExternalService.table.c.deleted == false() ).all()
        for e in all_external_services:
            external_service_type = e.get_external_service_type( trans )
            e.label = '%s - %s' % ( e.name, external_service_type.name )
        return build_select_field( trans,
                                   objs=all_external_services,
                                   label_attr='label',
                                   select_field_name=select_field_name,
                                   selected_value=selected_value,
                                   refresh_on_change=False )
