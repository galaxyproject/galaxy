<%inherit file="/base.mako"/>

<% 
    from galaxy.web.controllers.admin import entities, unentities
    from xml.sax.saxutils import escape, unescape 
%>

## Render a row
<%def name="render_row( group_name, group, ctr, anchored, curr_anchor )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>${group_name}</td>
        <td><a href="${h.url_for( controller='admin', action='group_members', group_id=group[0], group_name=group[1] )}">${group[2]}</a></td>
        <td>
            <a href="${h.url_for( controller='admin', action='mark_group_deleted', group_id=group[0] )}">Mark group deleted</a>
            %if not anchored:
                <a name="${curr_anchor}"></a>
                <div style="float: right;"><a href="#TOP">top</a></div>
            %endif
        </td>
    </tr>
</%def>

%if msg:
    <div class="donemessage">${msg}</div>
%endif

<a name="TOP"><h2>Groups</h2></a>

<ul class="manage-table-actions">
    <li><a class="action-button" href="${h.url_for( controller='admin', action='create_group' )}">Create a new group</a></li>
    <li><a class="action-button" href="${h.url_for( controller='admin', action='deleted_groups' )}">Manage deleted groups</a></li>
</ul>

%if len( groups ) == 0:
    There are no Galaxy groups
%else:
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
                <td colspan="3" style="text-align: center; border-bottom: 1px solid #D8B365">
                    Jump to letter:
                    %for a in anchors:
                        | <a href="#${a}">${a}</a>
                    %endfor
                </td>
            </tr>
        %endif
        <tr class="header">
            <td>Name</td>
            <td>Members</td>
            <td>&nbsp;</td>
        </tr>
        %for ctr, group in enumerate( groups ):
            <% group_name = unescape( group[1], unentities ) %>
            %if render_quick_find and not group_name.upper().startswith( curr_anchor ):
                <% anchored = False %>
            %endif
            %if render_quick_find and group_name.upper().startswith( curr_anchor ):
                %if not anchored:
                    ${render_row( group_name, group, ctr, anchored, curr_anchor )}
                    <% anchored = True %>
                %else:
                    ${render_row( group_name, group, ctr, anchored, curr_anchor )}
                %endif
            %elif render_quick_find:
                %for anchor in anchors[ anchor_loc: ]:
                    %if group_name.upper().startswith( anchor ):
                        %if not anchored:
                            <% curr_anchor = anchor %>
                            ${render_row( group_name, group, ctr, anchored, curr_anchor )}
                            <%  anchored = True %>
                        %else:
                            ${render_row( group_name, group, ctr, anchored, curr_anchor )}
                        %endif
                        <% 
                            anchor_loc = anchors.index( anchor )
                            break 
                        %>
                    %endif
                %endfor
            %else:
                ${render_row( group_name, group, ctr, True, '' )}
            %endif
        %endfor
    </table>
%endif
