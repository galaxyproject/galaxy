<%inherit file="/base.mako"/>

## Render a user row
<%def name="render_user_row( user, ctr )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td><input type="checkbox" name="users" value="${user.id}"/> ${user.email}</td>
    </tr>
</%def>

## Render a group row
<%def name="render_group_row( group, ctr, anchored, curr_anchor )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            %if not anchored:
                <div style="float: right;"><a href="#TOP">top</a></div>
                <a name="${curr_anchor}"><input type="checkbox" name="groups" value="${group.id}"/> ${group.name}</a>
            %else:
                <input type="checkbox" name="groups" value="${group.id}"/> ${group.name}
            %endif
        </td>
    </tr>
</%def>

%if msg:
    <div class="donemessage">${msg}</div>
%endif

<a name="TOP"><h2>Create Role</h2></a>
  

<form name="role_create" action="${h.url_for( controller='admin', action='new_role' )}" method="post" >
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr>
            <td>Name: <input  name="name" type="textfield" value="" size=40"></td>
            <td>Description: <input  name="description" type="textfield" value="" size=40"></td>
        </tr>
        <%
            render_quick_find = len( users ) > 50
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
                <td colspan="2" style="border-bottom: 1px solid #D8B365; text-align: center;">
                    Jump to letter:
                    %for a in anchors:
                        | <a href="#${a}">${a}</a>
                    %endfor
                </td>
            </tr>
        %endif
        <tr class="header">
            <td>Check to add user</td>
            <td>Check to add group</td>
        </tr>
        <tr>
            ## Render users
            <td valign="top">
                <table border="0" cellspacing="0" cellpadding="0" width="100%">
                    %for ctr, user in enumerate( users ):
                        ${render_user_row( user, ctr )}
                    %endfor
                </table>
            </td>
            ## Render roles
            <td valign="top">
                <% curr_anchor = 'A' %>
                <table border="0" cellspacing="0" cellpadding="0" width="100%">
                    %for ctr, group in enumerate( groups ):
                        %if render_quick_find and not group.name.upper().startswith( curr_anchor ):
                          <% anchored = False %>
                        %endif 
                        %if render_quick_find and group.name.upper().startswith( curr_anchor ):
                            %if not anchored:
                                ${render_group_row( group, ctr, anchored, curr_anchor )}
                                <% anchored = True %>
                            %else:
                                ${render_group_row( group, ctr, anchored, curr_anchor )}
                            %endif
                        %elif render_quick_find:
                            %for anchor in anchors[ anchor_loc: ]:
                                %if group.name.upper().startswith( anchor ):
                                    %if not anchored:
                                        <% curr_anchor = anchor %>
                                        ${render_group_row( group, ctr, anchored, curr_anchor )}
                                        <% anchored = True %>
                                    %else:
                                        ${render_group_row( group, ctr, anchored, curr_anchor )}
                                    %endif
                                    <% 
                                        anchor_loc = anchors.index( anchor )
                                        break 
                                    %>
                                %endif
                            %endfor
                        %else:
                            ${render_group_row( group, ctr, True, '' )}
                        %endif
                    %endfor
                </table>
            </td>
        </tr>
        <tr><td colspan="2"><button name="create_role_button" value="role_create">Create</button></td></tr>
    </table>
</form>
