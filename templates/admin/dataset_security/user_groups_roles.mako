<%inherit file="/base.mako"/>

<% 
    from galaxy.web.controllers.admin import entities, unentities
    from xml.sax.saxutils import escape, unescape
    import galaxy.model
%>

## Render a role - role is a tuple: ( id, name, description, type )
<%def name="render_role( role )">
    <li>
        %if not role[3] == galaxy.model.Role.types.PRIVATE:
            <a href="${h.url_for( action='role', id=role[0], edit=True )}">${unescape( role[1], unentities )}</a>
        %else:
            ${unescape( role[1], unentities )}
        %endif
    </li>
</%def>

## Render a group - group is a tuple: ( id, name )
<%def name="render_group( group )">
    <li>
        <a href="${h.url_for( action='group_members', group_id=group[0], group_name=group[1] )}">${unescape( group[1], unentities )}</a>
    </li>
</%def>

<% email = unescape( user_email, unentities ) %>

%if msg:
    <div class="donemessage">${msg}</div>
%endif

<h2>User '${email}' Groups and Roles</h2>
  
%if len( groups ) == 0 and len( roles ) == 0:
    User '${email}' belongs to no groups and is associated with no roles
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
