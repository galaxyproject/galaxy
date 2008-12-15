<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

## Render a role
<%def name="render_role( group, role )">
    <li>
        %if role and not role.type == trans.app.model.Role.types.PRIVATE:
            <a href="${h.url_for( action='role', role_id=role.id, edit=True )}">${role.description}</a>
            <a id="role-${role.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            <div popupmenu="role-${role.id}-popup">
                <a class="action-button" href="${h.url_for( controller='admin', action='remove_role_from_group', group_id=group.id, role_id=role.id )}">Remove role from group</a>
            </div>
        %elif role:
            ${role.description}
        %endif
    </li>
</%def>

## Render a user
<%def name="render_user( group, user )">
    <li>
        <a href="${h.url_for( controller='admin', action='user', user_id=user.id )}">${user.email}</a>
        <a id="user-${user.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
        <div popupmenu="user-${user.id}-popup">
            <a class="action-button" href="${h.url_for( controller='admin', action='remove_user_from_group', user_id=user.id, group_id=group.id )}">Remove user from group</a>
        </div>
    </li>
</%def>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if len( users ) > 0 or len( roles ) > 0:
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <td>Users associated with ${group.name}</td>
            <td>Roles associated with ${group.name}</td>
        </tr>
        <tr>
            <td>
                <ul>
                    %for user in users:
                        ${render_user( group, user )}
                    %endfor
                </ul>
            </td>
            <td>
                <ul>
                    %for role in roles:
                        ${render_role( group, role )}
                    %endfor
                </ul>
            </td>
        </tr>
    </table>
%endif
