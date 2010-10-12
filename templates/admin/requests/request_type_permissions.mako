<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if message:
    ${render_msg( message, status )}
%endif

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
        $( 'form#request_type_permissions' ).submit( function() {
            $( '.in_select option' ).each(function( i ) {
                $( this ).attr( "selected", "selected" );
            });
        });
    });
</script>


<div class="toolForm">
    <div class="toolFormTitle">Manage permissions on "${request_type.name}"</div>
    <div class="toolFormBody">
        <form name="request_type_permissions" id="request_type_permissions" action="${h.url_for( controller='requests_admin', action='request_type_permissions', id=trans.security.encode_id( request_type.id ) )}" method="post">
            <div class="form-row">
                <%
                    obj_name = request_type.name
                    current_actions = request_type.actions
                    permitted_actions = trans.app.model.RequestType.permitted_actions.items()
                    action = trans.app.model.RequestType.permitted_actions.REQUEST_TYPE_ACCESS
                    obj_str = 'request_type %s' % obj_name
                    obj_type = 'request_type'
                    all_roles = roles
                    action_key = 'REQUEST_TYPE_ACCESS'
                    
                    import sets
                    in_roles = sets.Set()
                    for a in current_actions:
                        if a.action == action.action:
                            in_roles.add( a.role )
                    out_roles = filter( lambda x: x not in in_roles, all_roles )
                %>
                <p>
                    <b>access sequencer configuration:</b> Restrict access to this sequencer configuration to only role members
                </p>
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
##            </%def>
            </div>
            <div class="form-row">
                <input type="submit" name="update_roles_button" value="Save"/>
            </div>
        </form>
    </div>
</div>