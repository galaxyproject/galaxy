<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    import galaxy.model
%>

## Render a role
<%def name="render_role( user, role )">
    <li>
        %if not role.type == galaxy.model.Role.types.PRIVATE:
            <a href="${h.url_for( action='role', role=role, edit=True )}">${role.name}</a>
        %else:
            ${role.name}
        %endif
        <a id="role-${role.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
        <div popupmenu="role-${role.id}-popup">
            <a class="action-button" href="${h.url_for( action='remove_user_from_role', user_id=user.id, role_id=role.id )}">Remove user from role</a>
        </div>
    </li>
</%def>

## Render a group
<%def name="render_group( user, group )">
    <li>
        <a href="${h.url_for( action='group_members_edit', group_id=group.id )}">${group.name}</a>
        <a id="group-${group.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
        <div popupmenu="group-${group.id}-popup">
            <a class="action-button" href="${h.url_for( action='remove_user_from_group', user_id=user.id, group_id=group.id )}">Remove user from group</a>
        </div>
    </li>
</%def>

<h2>User '${user.email}'</h2>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if len( groups ) == 0 and len( roles ) == 0:
    User '${user.email}' belongs to no groups and is associated with no roles
%else:
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <td>Groups</td>
            <td>Roles</td>
        </tr>
        <tr>
            <td>
                <ul>
                    %for group in groups:
                        ${render_group( user, group )}
                    %endfor
                </ul>
            </td>
            <td>
                <ul>
                    %for role in roles:
                        ${render_role( user, role )}
                    %endfor
                </ul>
            </td>
        </tr>
    </table>
%endif
