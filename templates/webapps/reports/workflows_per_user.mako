<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">Workflows Per User</h3>
        <table align="center" width="60%" class="colored">
            %if len( workflows ) == 0:
                <tr><td colspan="2">There are no workflows</td></tr>
            %else:
                <tr class="header">
                    <td>User</td>
                    <td>Total Workflows</td>
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
                        <td><a href="${h.url_for( controller='workflows', action='user_per_month', id=trans.security.encode_id( user.id ), email=util.sanitize_text( user.email ) )}">${email}</a></td>
                        <td>${total}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
