<%inherit file="/base.mako"/>

<% 
    from galaxy.web.controllers.admin import entities, unentities
    from xml.sax.saxutils import escape, unescape
    import galaxy.model
%>

## Render a row
<%def name="render_row( role, ctr, anchored, curr_anchor )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            %if not role.type == galaxy.model.Role.types.PRIVATE:
                <a href="${h.url_for( action='role', id=role.id, edit=True )}">${role.name}</a>
            %else:
                ${role.name}
            %endif
        </td>
        <td>${role.type}</td>
        <td>
            <ul>
                %for x in role.users:
                    <li><a href="${h.url_for( action='user_groups_roles', user_id=x.user.id, user_email=x.user.email )}">${x.user.email}</a></li>
                %endfor
            </ul>
        </td>
        <td>
            <ul>
                %for x in role.groups:
                    <li><a href="${h.url_for( action='group_members', group_id=x.group.id, group_name=escape( x.group.name, entities ) )}">${x.group.name}</a></li>
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

<a name="TOP"><h2>Roles</h2></a>

<ul class="manage-table-actions">
    <li><a class="action-button" href="${h.url_for( controller='admin', action='roles', create=True )}">Create a new role</a></li>
    <li><a class="action-button" href="${h.url_for( controller='admin', action='deleted_roles' )}">Manage deleted roles</a></li>
</ul>

%if len( roles ) == 0:
    There are no Galaxy roles
%else:
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <% 
            render_quick_find = len( roles ) > 50
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
                <td colspan="4" style="text-align: center; border-bottom: 1px solid #D8B365">
                    Jump to letter:
                    %for a in anchors:
                        | <a href="#${a}">${a}</a>
                    %endfor
                </td>
            </tr>
        %endif
        <tr class="header">
            <td>Name</td>
            <td>Type</td>
            <td>Users</td>
            <td>Groups</td>
        </tr>
        %for ctr, role in enumerate( roles ):
            %if render_quick_find and not role.name.upper().startswith( curr_anchor ):
                <% anchored = False %>
            %endif
            %if render_quick_find and role.name.upper().startswith( curr_anchor ):
                %if not anchored:
                    ${render_row( role, ctr, anchored, curr_anchor )}
                    <% anchored = True %>
                %else:
                    ${render_row( role, ctr, anchored, curr_anchor )}
                %endif
            %elif render_quick_find:
                %for anchor in anchors[ anchor_loc: ]:
                    %if role.name.upper().startswith( anchor ):
                        %if not anchored:
                            <% curr_anchor = anchor %>
                            ${render_row( role, ctr, anchored, curr_anchor )}
                            <% anchored = True %>
                        %else:
                            ${render_row( role, ctr, anchored, curr_anchor )}
                        %endif
                        <% 
                            anchor_loc = anchors.index( anchor )
                            break 
                        %>
                    %endif
                %endfor
            %else:
                ${render_row( role, ctr, True, '' )}
            %endif
        %endfor
    </table>
%endif
