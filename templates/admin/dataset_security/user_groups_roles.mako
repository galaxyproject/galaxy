<%inherit file="/base.mako"/>

<%
    import galaxy.model
%>

## Render a role
<%def name="render_role( role )">
    <li>
        %if not role.type == galaxy.model.Role.types.PRIVATE:
            <a href="${h.url_for( action='role', role=role, edit=True )}">${role.name}</a>
        %else:
            ${role.name}
        %endif
    </li>
</%def>

## Render a group
<%def name="render_group( group )">
    <li><a href="${h.url_for( action='group_members', group_id=group.id )}">${group.name}</a></li>
</%def>

%if msg:
    <div class="donemessage">${msg}</div>
%endif

<h2>User '${user.email}' Groups and Roles</h2>
  
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
                        ${render_group( group )}
                    %endfor
                </ul>
            </td>
            <td>
                <ul>
                    %for role in roles:
                        ${render_role( role )}
                    %endfor
                </ul>
            </td>
        </tr>
    </table>
%endif
