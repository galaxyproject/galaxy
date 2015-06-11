<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">Workflows Per User</h3>
        <table align="center" width="60%" class="colored">
            %if len( workflows ) == 0:
                <tr><td colspan="2">There are no workflows</td></tr>
            %else:
                <tr class="header">
                    <td>
                        ${get_sort_url(sort_id, order, 'user_email', 'workflows', 'per_user', 'User')}
                        <span class='dir_arrow user_email'>${arrow}</span>
                    
                    </td>
                    <td>
                        ${get_sort_url(sort_id, order, 'total_workflows', 'workflows', 'per_user', 'Total Workflows')}
                        <span class='dir_arrow total_workflows'>${arrow}</span>
                    </td>
                </tr>
                <% ctr = 0 %>
                %for workflow in workflows:
                    <%
                        from galaxy import util
                        email = workflow[0]
                        total = workflow[1]
                        user = trans.sa_session.query( trans.model.User ) \
                                               .filter_by( email=email ) \
                                               .one()
                    %>
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td><a href="${h.url_for( controller='workflows', action='user_per_month', id=trans.security.encode_id( user.id ), email=util.sanitize_text( user.email ), sort_id='default', order='default')}">${email}</a></td>
                        <td>${total}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
