<%inherit file="/base_panels.mako"/>

<%def name="main_body()">
    <h3 align="center">Registered Users</h3>
    %if msg:
        <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
            <tr><td class="ok_bgr">${msg}</td></tr>
        </table>
    %endif
    <table align="center" width="40%" class="colored">
        <tr>
            <td>
                <div class="reportBody">
                    <a href="${h.url_for( controller='users', action='registered_users' )}">Registered Users</a> - displays the number of registered users
                </div>
            </td>
        </tr>
    </table>
    <br clear="left" /><br />
    <table align="center" width="40%" class="colored">
        <tr>
            <td>
                <div class="reportBody">
                    <a href="${h.url_for( controller='users', action='last_access_date' )}">Date of Last Login</a> - displays users sorted by date of last login
                </div>
            </td>
        </tr>
    </table>
</%def>
