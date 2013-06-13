<%def name="render_select( current_actions, action_key, action, roles )">
    <%
        import sets
        in_roles = sets.Set()
        for a in current_actions:
            if a.action == action.action:
                in_roles.add( a.role )
        out_roles = filter( lambda x: x not in in_roles, roles )
    %>
    <p>
        <b>${action.action}:</b> ${action.description}
        %if action == trans.app.security_agent.permitted_actions.DATASET_ACCESS:
            <br/>
            NOTE: Users must have every role associated with this dataset in order to access it
        %endif
    </p>
    <div style="width: 100%; white-space: nowrap;">
        <div style="float: left; width: 50%;">
            Roles associated:<br />
            <select name="${action_key}_in" id="${action_key}_in_select" class="in_select" style="max-width: 98%; width: 98%; height: 150px; font-size: 100%;" multiple>
                %for role in in_roles:
                    <option value="${role.id}">${role.name}</option>
                %endfor
            </select> <br />
            <div style="width: 98%; text-align: right"><input type="submit" id="${action_key}_remove_button" class="role_remove_button" value=">>"/></div>
        </div>
        <div style="width: 50%;">
            Roles not associated:<br />
            <select name="${action_key}_out" id="${action_key}_out_select" style="max-width: 98%; width: 98%; height: 150px; font-size: 100%;" multiple>
                %for role in out_roles:
                    <option value="${role.id}">${role.name}</option>
                %endfor
            </select> <br />
            <input type="submit" id="${action_key}_add_button" class="role_add_button" value="<<"/>
        </div>
    </div>
</%def>

## Any permission ( e.g., 'DATASET_ACCESS' ) included in the do_not_render param will not be rendered on the page.
<%def name="render_permission_form( obj, obj_name, form_url, roles, do_not_render=[], all_roles=[] )">
    <%
        if isinstance( obj, trans.app.model.User ):
            current_actions = obj.default_permissions
            permitted_actions = trans.app.model.Dataset.permitted_actions.items()
            obj_str = 'user %s' % obj_name
            obj_type = 'dataset'
        elif isinstance( obj, trans.app.model.History ):
            current_actions = obj.default_permissions
            permitted_actions = trans.app.model.Dataset.permitted_actions.items()
            obj_str = 'history %s' % obj_name
            obj_type = 'dataset'
        elif isinstance( obj, trans.app.model.Dataset ):
            current_actions = obj.actions
            permitted_actions = trans.app.model.Dataset.permitted_actions.items()
            obj_str = obj_name
            obj_type = 'dataset'
        elif isinstance( obj, trans.app.model.LibraryDatasetDatasetAssociation ):
            current_actions = obj.actions + obj.dataset.actions
            permitted_actions = trans.app.model.Dataset.permitted_actions.items() + trans.app.model.Library.permitted_actions.items()
            obj_str = obj_name
            obj_type = 'dataset'
        elif isinstance( obj, trans.app.model.Library ):
            current_actions = obj.actions
            permitted_actions = trans.app.model.Library.permitted_actions.items()
            obj_str = 'library %s' % obj_name
            obj_type = 'library'
        elif isinstance( obj, trans.app.model.LibraryDataset ):
            current_actions = obj.actions
            permitted_actions = trans.app.model.Library.permitted_actions.items()
            obj_str = 'library dataset %s' % obj_name
            obj_type = 'library'
        elif isinstance( obj, trans.app.model.LibraryFolder ):
            current_actions = obj.actions
            permitted_actions = trans.app.model.Library.permitted_actions.items()
            obj_str = 'library folder %s' % obj_name
            obj_type = 'library'
        else:
            current_actions = []
            permitted_actions = {}.items()
            obj_str = 'unknown object %s' %obj_name
            obj_type = ''
    %>
    <script type="text/javascript">
        $( document ).ready( function () {
            $( '.role_add_button' ).click( function() {
                var action = this.id.substring( 0, this.id.lastIndexOf( '_add_button' ) )
                var in_select = '#' + action + '_in_select';
                var out_select = '#' + action + '_out_select';
                return !$( out_select + ' option:selected' ).remove().appendTo( in_select );
            });
            $( '.role_remove_button' ).click( function() {
                var action = this.id.substring( 0, this.id.lastIndexOf( '_remove_button' ) )
                var in_select = '#' + action + '_in_select';
                var out_select = '#' + action + '_out_select';
                return !$( in_select + ' option:selected' ).remove().appendTo( out_select );
            });
            $( 'form#edit_role_associations' ).submit( function() {
                $( '.in_select option' ).each(function( i ) {
                    $( this ).attr( "selected", "selected" );
                });
            });
            // Temporary removal of select2 for all permissions forms
            $('#edit_role_associations select').select2("destroy");
        });
    </script>
    <div class="toolForm">
        <div class="toolFormTitle">Manage ${obj_type} permissions on ${obj_str}</div>
        <div class="toolFormBody">
            <form name="edit_role_associations" id="edit_role_associations" action="${form_url}" method="post">
                <div class="form-row"></div>
                %for k, v in permitted_actions:
                    %if k not in do_not_render:
                        <div class="form-row">
                            ## LIBRARY_ACCESS is a special case because we need to render all roles instead of
                            ## roles derived from the roles associated with LIBRARY_ACCESS.
                            <% render_all_roles = k == 'LIBRARY_ACCESS' %>
                            %if render_all_roles:
                                ${render_select( current_actions, k, v, all_roles )}
                            %else:
                                ${render_select( current_actions, k, v, roles )}
                            %endif
                        </div>
                    %endif
                %endfor
                <div class="form-row">
                    <input type="submit" name="update_roles_button" value="Save"/>
                </div>
            </form>
        </div>
    </div>
    <p/>
</%def>
