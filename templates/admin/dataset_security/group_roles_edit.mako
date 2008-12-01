<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

## Render a row
<%def name="render_row( role, ctr, anchored, curr_anchor, check )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            %if check:
                <input type="checkbox" name="roles" value="${role.id}" checked/> ${role.description}
            %else:
                <input type="checkbox" name="roles" value="${role.id}"/> ${role.description}
            %endif
        </td>
    </tr>
</%def>

<a name="TOP"><h2>Roles associated with group '${group.name}'</h2></a>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if len( roles ) == 0:
    <tr><td>There are no Galaxy roles</td></tr>
%else:
    <form name="update_group_roles" action="${h.url_for( controller='admin', action='update_group_roles', group_id=group.id )}" method="post" >
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
                    <td style="border-bottom: 1px solid #D8B365; text-align: center;">
                        Jump to letter:
                        %for a in anchors:
                            | <a href="#${a}">${a}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            <tr class="header"><td>Check to add role</td></tr>
            %for ctr, role in enumerate( roles ):
                <% check = False %>
                %for group_role in group_roles:
                    %if group_role.name == role.name:
                        <% 
                            check = True
                            break
                        %>
                    %endif
                %endfor
                %if render_quick_find and not role.description.upper().startswith( curr_anchor ):
                  <% anchored = False %>
                %endif 
                %if render_quick_find and role.description.upper().startswith( curr_anchor ):
                    %if not anchored:
                        ${render_row( role, ctr, anchored, curr_anchor, check )}
                        <% anchored = True %>
                    %else:
                        ${render_row( role, ctr, anchored, curr_anchor, check )}
                    %endif
                %elif render_quick_find:
                    %for anchor in anchors[ anchor_loc: ]:
                        %if role.description.upper().startswith( anchor ):
                            %if not anchored:
                                <% curr_anchor = anchor %>
                                ${render_row( role, ctr, anchored, curr_anchor, check )}
                                <% anchored = True %>
                            %else:
                                ${render_row( role, ctr, anchored, curr_anchor, check )}
                            %endif
                            <% 
                                anchor_loc = anchors.index( anchor )
                                break 
                            %>
                        %endif
                    %endfor
                %else:
                    ${render_row( role, ctr, True, '', check )}
                %endif
            %endfor
            <tr><td><button name="group_roles_edit_button" value="update_group_roles">Update Role Associations</button></td></tr>
        </table>
    </form>
%endif

