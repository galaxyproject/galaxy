<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

## Render a row
<%def name="render_row( group, members, roles, ctr, anchored, curr_anchor )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            <a href="${h.url_for( controller='admin', action='group', group_id=group.id )}">${group.name}</a>
            <a id="group-${group.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            <div popupmenu="group-${group.id}-popup">
                <a class="action-button" href="${h.url_for( controller='admin', action='group_members_edit', group_id=group.id )}">Change associated users</a>
                <a class="action-button" href="${h.url_for( controller='admin', action='group_roles_edit', group_id=group.id )}">Change associated roles</a>
                <a class="action-button" href="${h.url_for( controller='admin', action='mark_group_deleted', group_id=group.id )}">Mark group deleted</a>
            </div>
        </td>
        <td>
            <ul>
                %for user in members:
                    <li><a href="${h.url_for( controller='admin', action='user', user_id=user.id )}">${user.email}</a></li>
                %endfor
            </ul>
        </td>
        <td>
            <ul>
                %for role in roles:
                    <li>
                        %if not role.type == trans.app.model.Role.types.PRIVATE:
                            <a href="${h.url_for( controller='admin', action='role', role_id=role.id )}">${role.description}</a>
                        %else:
                            ${role.description}
                        %endif
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

<a name="TOP"><h2>Groups</h2></a>

<ul class="manage-table-actions">
    <li><a class="action-button" href="${h.url_for( controller='admin', action='create_group' )}">Create a new group</a></li>
    <li><a class="action-button" href="${h.url_for( controller='admin', action='deleted_groups' )}">Manage deleted groups</a></li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if len( groups_members_roles ) == 0:
    There are no Galaxy groups
%else:
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <% 
            render_quick_find = len( groups_members_roles ) > 50
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
            <td>Name</td>
            <td>Associated Users</td>
            <td>Associated Roles</td>
        </tr>
        %for ctr, group_tuple in enumerate( groups_members_roles ):
            <%
                group = group_tuple[0]
                members = group_tuple[1]
                roles = group_tuple[2]
            %>
            %if render_quick_find and not group.name.upper().startswith( curr_anchor ):
                <% anchored = False %>
            %endif
            %if render_quick_find and group.name.upper().startswith( curr_anchor ):
                %if not anchored:
                    ${render_row( group, members, roles, ctr, anchored, curr_anchor )}
                    <% anchored = True %>
                %else:
                    ${render_row( group, members, roles, ctr, anchored, curr_anchor )}
                %endif
            %elif render_quick_find:
                %for anchor in anchors[ anchor_loc: ]:
                    %if group.name.upper().startswith( anchor ):
                        %if not anchored:
                            <% curr_anchor = anchor %>
                            ${render_row( group, members, roles, ctr, anchored, curr_anchor )}
                            <%  anchored = True %>
                        %else:
                            ${render_row( group, members, roles, ctr, anchored, curr_anchor )}
                        %endif
                        <% 
                            anchor_loc = anchors.index( anchor )
                            break 
                        %>
                    %endif
                %endfor
            %else:
                ${render_row( group, members, roles, ctr, True, '' )}
            %endif
        %endfor
    </table>
%endif
