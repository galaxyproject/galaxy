<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">Sequencing Requests Per User</h3>
        <table align="center" width="60%" class="colored">
            %if len( requests ) == 0:
                <tr><td colspan="2">There are no requests</td></tr>
            %else:
                <tr class="header">
                    <td>User</td>
                    <td>Total Requests</td>
                </tr>
                <% ctr = 0 %>
                %for request in requests:
                    <%
                        from galaxy import util
                        email = request[0]
                        total = request[1]
                        user = trans.sa_session.query( trans.model.User ) \
                                               .filter_by( email=email ) \
                                               .one()
                    %>
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td><a href="${h.url_for( controller='sample_tracking', action='user_per_month', id=trans.security.encode_id( user.id ), email=util.sanitize_text( user.email ) )}">${email}</a></td>
                        <td>${total}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
