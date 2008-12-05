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
                <input type="checkbox" name="roles" value="${role.id}" checked/> ${role.name}
            %else:
                <input type="checkbox" name="roles" value="${role.id}"/> ${role.name}
            %endif
            %if not anchored:
                <a name="${curr_anchor}"></a>
                <div style="float: right;"><a href="#TOP">top</a></div>
            %endif
        </td>
    </tr>
</%def>

<a name="TOP">&nbsp;</a>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if len( roles ) == 0:
    <tr><td>There are no Galaxy roles</td></tr>
%else:
    <form name="user_roles_edit" action="${h.url_for( controller='admin', action='user_roles_edit' )}" method="post" >
        <input type="hidden" name="user_id" value="${user.id}" />
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
                    <td colspan="3" style="border-bottom: 1px solid #D8B365; text-align: center;">
                        Jump to letter:
                        %for a in anchors:
                            | <a href="#${a}">${a}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            <tr class="header"><td>Select to associate role with ${user.email}</td></tr>
            %for ctr, role in enumerate( roles ):
                <% check = False %>
                %for user_role in user_roles:
                    %if user_role.id == role.id:
                        <% 
                            check = True
                            break
                        %>
                    %endif
                %endfor
                %if render_quick_find and not role.name.upper().startswith( curr_anchor ):
                  <% anchored = False %>
                %endif 
                %if render_quick_find and role.name.upper().startswith( curr_anchor ):
                    %if not anchored:
                        ${render_row( role, ctr, anchored, curr_anchor, check )}
                        <% anchored = True %>
                    %else:
                        ${render_row( role, ctr, anchored, curr_anchor, check )}
                    %endif
                %elif render_quick_find:
                    %for anchor in anchors[ anchor_loc: ]:
                        %if role.name.upper().startswith( anchor ):
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
            <tr><td><input type="submit" name="user_roles_edit_button" value="Associate user with selected roles" /></td></tr>
        </table>
    </form>
%endif
