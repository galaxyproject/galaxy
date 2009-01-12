<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

## Render a row
<%def name="render_row( user, groups, roles, ctr, anchored, curr_anchor )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            <a href="${h.url_for( controller='admin', action='user', user_id=user.id )}">${user.email}</a>
            <a id="user-${user.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            <div popupmenu="user-${user.id}-popup">
                <a class="action-button" href="${h.url_for( action='reset_user_password', user_id=user.id )}">Reset password</a>
                <a class="action-button" href="${h.url_for( controller='admin', action='user', user_id=user.id )}">Change associated groups and roles</a>
                %if allow_user_deletion:
                    <a class="action-button" href="${h.url_for( action='mark_user_deleted', user_id=user.id )}">Mark user deleted</a>
                %endif
            </div>
        </td>
        <td>
            <ul>
                %for group in groups:
                    <li>
                        <a href="${h.url_for( controller='admin', action='group', group_id=group.id )}">${group.name}</a>
                        <a id="group-${group.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        <div popupmenu="group-${group.id}-popup">
                            <a class="action-button" href="${h.url_for( controller='admin', action='remove_group_from_user', user_id=user.id, group_id=group.id )}">Remove group from user</a>
                        </div>
                    </li>
                %endfor
            </ul>
        </td>
        <td>
            <ul>
                %for role in roles:
                    <li>
                        <a href="${h.url_for( controller='admin', action='role', role_id=role.id )}">${role.name}</a>
                        <a id="role-${role.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        <div popupmenu="role-${role.id}-popup">
                            <a class="action-button" href="${h.url_for( controller='admin', action='remove_role_from_user', user_id=user.id, role_id=role.id )}">Remove role from user</a>
                        </div>
                    </li>
                %endfor
            </ul>
            %if not anchored:
                <a name="${curr_anchor}"></a>
                <div style="float: right;"><a href="#TOP">top</a></div>
            %endif
        </td>
    </tr>
</%def>

<a name="TOP"><h2>Users</h2></a>

<ul class="manage-table-actions">
    <li><a class="action-button" href="${h.url_for( controller='admin', action='create_new_user' )}">Create a new user</a></li>
    %if allow_user_deletion:
        <li><a class="action-button" href="${h.url_for( controller='admin', action='deleted_users' )}">Manage deleted users</a></li>
    %endif
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if len( users_groups_roles ) == 0:
    There are no Galaxy users
%else:
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <%
            render_quick_find = len( users_groups_roles ) > 50
            ctr = 0
        %>
        %if render_quick_find:
            <%
                anchors = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
                anchor_loc = 0
                anchored = False
                curr_anchor = 'A'
            %>
            <tr style="background: #EEE">
                <td colspan="3" style="border-bottom: 1px solid #D8B365; text-align: center;">
                    Jump to letter:
                    %for a in anchors:
                        | <a href="#${a}">${a}</a>
                    %endfor
                </td>
            </tr>
        %endif
        <tr class="header">
            <td>Email</td>
            <td>Associated Groups</td>
            <td>Associated Roles</td>
        </tr>
        %for ctr, user_tuple in enumerate( users_groups_roles ):
            <%
                user = user_tuple[0]
                groups = user_tuple[1]
                roles = user_tuple[2]
            %>
            %if render_quick_find and not user.email.upper().startswith( curr_anchor ):
                <% anchored = False %>
            %endif
            %if render_quick_find and user.email.upper().startswith( curr_anchor ):
                %if not anchored:
                    ${render_row( user, groups, roles, ctr, anchored, curr_anchor )}
                    <% anchored = True %>
                %else:
                    ${render_row( user, groups, roles, ctr, anchored, curr_anchor )}
                %endif
            %elif render_quick_find:   
                %for anchor in anchors[ anchor_loc: ]:
                    %if user.email.upper().startswith( anchor ):
                        %if not anchored:
                            <% curr_anchor = anchor %>
                            ${render_row( user, groups, roles, ctr, anchored, curr_anchor )}
                            <%  anchored = True %>
                        %else:
                            ${render_row( user, groups, roles, ctr, anchored, curr_anchor )}
                        %endif
                        <% 
                            anchor_loc = anchors.index( anchor )
                            break 
                        %>
                    %endif
                %endfor
            %else:
                ${render_row( user, groups, roles, ctr, True, '' )}
            %endif
        %endfor
    </table>
%endif
