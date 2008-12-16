<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

## Render a row
<%def name="render_row( user, ctr, anchored, curr_anchor )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            ${user.email}
            <a id="user-${user.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            <div popupmenu="user-${user.id}-popup">
                <a class="action-button" href="${h.url_for( controller="admin", action='undelete_user', user_id=user.id )}">Undelete</a>
                <a class="action-button" confirm="Purging a user will delete all of their histories, datasets, and group and role associations.  Click OK to purge the user '${user.email}'" href="${h.url_for( controller="admin", action='purge_user', user_id=user.id )}">Purge</a>
            </div>
            %if not anchored:
                <a name="${curr_anchor}"></a>
                <div style="float: right;"><a href="#TOP">top</a></div>
            %endif
        </td>
    </tr>
</%def>

<a name="TOP"><h2>Deleted Users</h2></a>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if len( users ) == 0:
    There are no deleted Galaxy users
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
                <td colspan="3" style="text-align: center; border-bottom: 1px solid #D8B365">
                    Jump to letter:
                    %for a in anchors:
                        | <a href="#${a}">${a}</a>
                    %endfor
                </td>
            </tr>
        %endif
        <tr class="header">
            <td>Email</td>
        </tr>
        %for ctr, user in enumerate( users ):
            %if render_quick_find and not user.email.upper().startswith( curr_anchor ):
                <% anchored = False %>
            %endif
            %if render_quick_find and user.email.upper().startswith( curr_anchor ):
                %if not anchored:
                    ${render_row( user, ctr, anchored, curr_anchor )}
                    <% anchored = True %>
                %else:
                    ${render_row( user, ctr, anchored, curr_anchor )}
                %endif
            %elif render_quick_find:
                %for anchor in anchors[ anchor_loc: ]:
                    %if user.email.upper().startswith( anchor ):
                        %if not anchored:
                            <% curr_anchor = anchor %>
                            ${render_row( user, ctr, anchored, curr_anchor )}
                            <%  anchored = True %>
                        %else:
                            ${render_row( user, ctr, anchored, curr_anchor )}
                        %endif
                        <% 
                            anchor_loc = anchors.index( anchor )
                            break 
                        %>
                    %endif
                %endfor
            %else:
                ${render_row( user, ctr, True, '' )}
            %endif
        %endfor
    </table>
%endif
