<%inherit file="/base.mako"/>

%if msg:
    <div class="donemessage">${msg}</div>
%endif

<a name="TOP"><h2>Users</h2></a>

%if len( users ) == 0:
    There are no Galaxy users
%else:
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
        <tr class="header"><td>Email</td></tr>
        %for ctr, user in enumerate( users ):
            %if render_quick_find and not user.email.upper().startswith( curr_anchor ):
                <% anchored = False %>
            %endif
            %if ctr % 2 == 0:
                <tr class="odd_row">
            %else:
                <tr>
            %endif
                <td>
                    %if render_quick_find and user.email.upper().startswith( curr_anchor ):
                        %if not anchored:
                            <a name="${curr_anchor}"></a>
                            <div style="float: right;"><a href="#TOP">top</a></div>
                            <% anchored = True %>
                        %endif
                        <a href="${h.url_for( controller='admin', action='user_groups_roles', user_id=user.id )}">${user.email}</a>
                    %elif render_quick_find:
                        %for anchor in anchors[ anchor_loc: ]:   
                            %if email.upper().startswith( anchor ):
                                %if not anchored:
                                    <a name="${anchor}"></a>
                                    <div style="float: right;"><a href="#TOP">top</a></div>
                                    <% 
                                        curr_anchor = anchor
                                        anchored = True 
                                    %>
                                %endif
                                <a href="${h.url_for( controller='admin', action='user_groups_roles', user_id=user.id )}">${user.email}</a>
                                <% 
                                    anchor_loc = anchors.index( anchor )
                                    break 
                                %>
                            %endif
                        %endfor
                    %else:
                        <a href="${h.url_for( controller='admin', action='user_groups_roles', user_id=user.id )}">${user.email}</a>
                    %endif
                </td>
            </tr>
        %endfor
    </table>
%endif
