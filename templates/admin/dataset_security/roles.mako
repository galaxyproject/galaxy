<%inherit file="/base.mako"/>

<% 
    from galaxy.web.controllers.admin import entities, unentities
    from xml.sax.saxutils import escape, unescape
    import galaxy.model
%>

## Render a row
<%def name="render_row( role )">
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
                <li>${x.user.email}</li>
            %endfor
        </ul>
    </td>
    <td>
        <ul>
            %for x in role.groups:
                <li>${x.group.name}</li>
            %endfor
        </ul>
    </td>
</%def>

%if msg:
    <div class="donemessage">${msg}</div>
%endif

<h2>Roles</h2>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='roles', create=True )}">Create a new role</a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='deleted_roles' )}">Manage deleted roles</a>
    </li>
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
        %for role in roles:
            %if render_quick_find and not role.name.upper().startswith( curr_anchor ):
                <% anchored = False %>
            %endif
            %if ctr % 2 == 1:
                <div class="odd_row">
            %endif
            %if render_quick_find and role.name.upper().startswith( curr_anchor ):
                %if not anchored:
                    <tr>
                        <td colspan="4" class=panel-body">
                            <a name="${curr_anchor}"></a>
                            <div style="float: right;"><a href="#TOP">quick find</a></div>
                            <% anchored = True %>
                        </td>
                    </tr>
                %endif
                <tr>${render_row( role )}</tr>
            %elif render_quick_find:
                %for anchor in anchors[ anchor_loc: ]:
                    %if role.name.upper().startswith( anchor ):
                        %if not anchored:
                            <tr>
                                <td colspan="6" class="panel-body">
                                    <a name="${anchor}"></a>
                                    <div style="float: right;"><a href="#TOP">quick find</a></div>
                                    <% 
                                        curr_anchor = anchor
                                        anchored = True 
                                    %>
                                </td>
                            </tr>
                        %endif
                        <tr>${render_row( role )}</tr>
                        <% 
                            anchor_loc = anchors.index( anchor )
                            break 
                        %>
                    %endif
                %endfor
            %else:
                <tr>${render_row( role )}</tr>
            %endif
            %if ctr % 2 == 1:
                </div>
            %endif
            <% ctr += 1 %>
        %endfor
    </table>
%endif
</div>
