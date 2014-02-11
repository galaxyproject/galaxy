<%inherit file="/base.mako"/>

%if message:
    ${render_msg( message, status )}
%endif


%if users:
    <div class="toolForm">
            <div class="toolFormTitle">Users informations</div>
            <table class="grid">
                <thead><th>UID</th><th>email</th></thead>
                <tbody>
                %for user in users:
                     <tr>
                        <td>${user['uid']}</td>
                        <td>${user['email']}</td>
                        <td>${user['key']}</td>
                        <td>
                          <form action="${h.url_for( controller='userskeys', action='admin_api_keys', cntrller=cntrller )}" method="POST">
                          <input type="hidden" name="uid" value=${user['uid']} />
                          <input type="submit" name="new_api_key_button" value="Generate a new key now" />
                          </form>
                        </td>
                     </tr>
                %endfor
                </tbody>
                </table>
            <div style="clear: both"></div>
    </div>
%else:
	<div>No informations available</div>
%endif


<p/>

