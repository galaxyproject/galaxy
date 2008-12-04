<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

## Render a row
<%def name="render_row( group, ctr, anchored, curr_anchor, check )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            %if check:
                <input type="checkbox" name="groups" value="${group.id}" checked/> ${group.name}
            %else:
                <input type="checkbox" name="groups" value="${group.id}"/> ${group.name}
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

%if len( groups ) == 0:
    <tr><td>There are no Galaxy groups</td></tr>
%else:
    <form name="update_user_groups" action="${h.url_for( controller='admin', action='update_user_groups', user_id=user.id )}" method="post" >
        <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
            <%
                render_quick_find = len( groups ) > 50
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
            <tr class="header"><td>Select to add ${user.email} to group</td></tr>
            %for ctr, group in enumerate( groups ):
                <% check = False %>
                %for user_group in user_groups:
                    %if user_group.id == group.id:
                        <% 
                            check = True
                            break
                        %>
                    %endif
                %endfor
                %if render_quick_find and not group.name.upper().startswith( curr_anchor ):
                  <% anchored = False %>
                %endif 
                %if render_quick_find and group.name.upper().startswith( curr_anchor ):
                    %if not anchored:
                        ${render_row( group, ctr, anchored, curr_anchor, check )}
                        <% anchored = True %>
                    %else:
                        ${render_row( group, ctr, anchored, curr_anchor, check )}
                    %endif
                %elif render_quick_find:
                    %for anchor in anchors[ anchor_loc: ]:
                        %if group.name.upper().startswith( anchor ):
                            %if not anchored:
                                <% curr_anchor = anchor %>
                                ${render_row( group, ctr, anchored, curr_anchor, check )}
                                <% anchored = True %>
                            %else:
                                ${render_row( group, ctr, anchored, curr_anchor, check )}
                            %endif
                            <% 
                                anchor_loc = anchors.index( anchor )
                                break 
                            %>
                        %endif
                    %endfor
                %else:
                    ${render_row( group, ctr, True, '', check )}
                %endif
            %endfor
            <tr><td><input type="submit" name="user_groups_edit_button" value="Add user to selected groups" /></td></tr>
        </table>
    </form>
%endif
