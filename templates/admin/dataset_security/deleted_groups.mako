<%inherit file="/base.mako"/>

## Render a row
<%def name="render_row( group, members, roles, ctr, anchored, curr_anchor )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            ${group.name}
            <a id="group-${group.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            <div popupmenu="group-${group.id}-popup">
                <a class="action-button" href="${h.url_for( action='undelete_group', group_id=group.id )}">Undelete</a>
                <a class="action-button" href="${h.url_for( action='purge_group', group_id=group.id )}">Purge</a>
            </div>
        </td>
        <td>
            <ul>
                %for user in members:
                    <li>${user.email}</li>
                %endfor
            </ul>
        </td>
        <td>
            <ul>
                %for role in roles:
                    <li>${role.name}</li>
                %endfor
            </ul>
            %if not anchored:
                <a name="${curr_anchor}"></a>
                <div style="float: right;"><a href="#TOP">top</a></div>
            %endif
        </td>
    </tr>
</%def>

%if msg:
    <div class="donemessage">${msg}</div>
%endif

<a name="TOP"><h2>Deleted Groups</h2></a>

%if len( groups_members_roles ) == 0:
    There are no deleted Galaxy groups
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
                <td colspan="3" style="text-align: center; border-bottom: 1px solid #D8B365">
                    Jump to letter:
                    %for a in anchors:
                        | <a href="#${a}">${a}</a>
                    %endfor
                </td>
            </tr>
        %endif
        <tr class="header">
            <td>Name</td>
            <td>Members</td>
            <td>Roles</td>
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
                    ${render_row( group, members, roles, ctr, roles, anchored, curr_anchor )}
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
