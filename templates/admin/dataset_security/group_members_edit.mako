<%inherit file="/base.mako"/>

## Render a row
<%def name="render_row( user, ctr, anchored, curr_anchor, check )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            %if check:
                <input type="checkbox" name="members" value="${user.id}" checked/> ${user.email}
            %else:
                <input type="checkbox" name="members" value="${user.id}"/> ${user.email}
            %endif
        </td>
    </tr>
</%def>

%if msg:
    <div class="donemessage">${msg}</div>
%endif

<a name="TOP"><h2>Members of group '${group.name}'</h2></a>

%if len( users ) == 0:
    <tr><td>There are no Galaxy users</td></tr>
%else:
    <form name="update_group_members" action="${h.url_for( controller='admin', action='update_group_members', group_id=group.id )}" method="post" >
        <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
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
                    <td style="border-bottom: 1px solid #D8B365; text-align: center;">
                        Jump to letter:
                        %for a in anchors:
                            | <a href="#${a}">${a}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            <tr class="header"><td>Check to add member</td></tr>
            %for ctr, user in enumerate( users ):
                <% check = False %>
                %for member in members:
                    %if member.email == user.email:
                        <% 
                            check = True
                            break
                        %>
                    %endif
                %endfor
                %if render_quick_find and not user.email.upper().startswith( curr_anchor ):
                  <% anchored = False %>
                %endif 
                %if render_quick_find and user.email.upper().startswith( curr_anchor ):
                    %if not anchored:
                        ${render_row( user, ctr, anchored, curr_anchor, check )}
                        <% anchored = True %>
                    %else:
                        ${render_row( user, ctr, anchored, curr_anchor, check )}
                    %endif
                %elif render_quick_find:
                    %for anchor in anchors[ anchor_loc: ]:
                        %if user.email.upper().startswith( anchor ):
                            %if not anchored:
                                <% curr_anchor = anchor %>
                                ${render_row( user, ctr, anchored, curr_anchor, check )}
                                <% anchored = True %>
                            %else:
                                ${render_row( user, ctr, anchored, curr_anchor, check )}
                            %endif
                            <% 
                                anchor_loc = anchors.index( anchor )
                                break 
                            %>
                        %endif
                    %endfor
                %else:
                    ${render_row( user, ctr, True, '', check )}
                %endif
            %endfor
            <tr><td><button name="group_members_edit_button" value="update_group_members">Update Members</button></td></tr>
        </table>
    </form>
%endif

