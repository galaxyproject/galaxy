<%def name="render_select( current_actions, action_key, action, all_roles )">
    <%
        in_roles = []
        for a in current_actions:
            if a.action == action.action:
                in_roles.append( a.role )
        out_roles = filter( lambda x: x not in in_roles, all_roles )
    %>
    <p><label>${action.action}:</label> ${action.description}</p>
    <div style="width: 100%; white-space: nowrap;">
        <div style="float: left; width: 50%;">
            Roles associated:<br/>
            <select name="${action_key}_in" id="${action_key}_in_select" class="in_select" style="max-width: 98%; width: 98%; height: 150px; font-size: 100%;" multiple>
                %for role in in_roles:
                    <option value="${role.id}">${role.name}</option>
                %endfor
            </select> <br/>
            <div style="width: 98%; text-align: right"><input type="submit" id="${action_key}_remove_button" class="role_remove_button" value=">>"/></div>
        </div>
        <div style="width: 50%;">
            Roles not associated:<br/>
            <select name="${action_key}_out" id="${action_key}_out_select" style="max-width: 98%; width: 98%; height: 150px; font-size: 100%;" multiple>
                %for role in out_roles:
                    <option value="${role.id}">${role.name}</option>
                %endfor
            </select> <br/>
            <input type="submit" id="${action_key}_add_button" class="role_add_button" value="<<"/>
        </div>
    </div>
</%def>

<%def name="render_permission_form( obj, obj_name, form_url, id_name, id, all_roles )">
    <%
        if isinstance( obj, trans.app.model.User ):
            current_actions = obj.default_permissions
            obj_str = 'user %s' % obj_name
        elif isinstance( obj, trans.app.model.History ):
            current_actions = obj.default_permissions
            obj_str = 'history %s' % obj_name
        elif isinstance( obj, trans.app.model.Dataset ):
            current_actions = obj.actions
            obj_str = obj_name
        else:
            current_actions = obj.dataset.actions
            obj_str = 'unknown object %s' %obj_name
    %>
    <script type="text/javascript">
        var q = jQuery.noConflict();
        q( document ).ready( function () {
            q( '.role_add_button' ).click( function() {
                var action = this.id.substring( 0, this.id.lastIndexOf( '_add_button' ) )
                var in_select = '#' + action + '_in_select';
                var out_select = '#' + action + '_out_select';
                return !q( out_select + ' option:selected' ).remove().appendTo( in_select );
            });
            q( '.role_remove_button' ).click( function() {
                var action = this.id.substring( 0, this.id.lastIndexOf( '_remove_button' ) )
                var in_select = '#' + action + '_in_select';
                var out_select = '#' + action + '_out_select';
                return !q( in_select + ' option:selected' ).remove().appendTo( out_select );
            });
            q( 'form#edit_role_associations' ).submit( function() {
                q( '.in_select option' ).each(function( i ) {
                    q( this ).attr( "selected", "selected" );
                });
            });
        });
    </script>
    <div class="toolForm">
        <div class="toolFormTitle">Manage permissions and role associations for ${obj_str}</div>
        <div class="toolFormBody">
            <form name="edit_role_associations" id="edit_role_associations" action="${form_url}" method="post">
                <input type="hidden" name="${id_name}" value="${id}"/>
                <div class="form-row"></div>
                %for k, v in trans.app.model.Dataset.permitted_actions.items():
                    <div class="form-row">
                        ${render_select( current_actions, k, v, all_roles )}
                    </div>
                %endfor
                <div class="form-row">
                    <input type="submit" name="update_roles" value="Save"/>
                </div>
            </form>
        </div>
    </div>
    <p/>
</%def>
