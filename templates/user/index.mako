<%inherit file="/base.mako"/>
<%def name="title()">User preferences</%def>

<h2>User preferences</h2>

%if user:
    <p>You are currently logged in as ${user.email}.</p>
    <ul>
        <li><a href="${h.url_for( action='change_password' )}">Change your password</a></li>
        <li><a href="${h.url_for( action='change_email' )}">Update your email address</a></li>
        <li><a href="${h.url_for( action='set_default_permissions' )}">Change default permissions</a> for new histories</li>
        <li><a href="${h.url_for( action='logout' )}">Logout</a></li>
    </ul>
%else:
    <p>You are currently not logged in.</p>
    <ul>
        <li><a href="${h.url_for( action='login' )}">Login</li>
        <li><a href="${h.url_for( action='create' )}">Register</a></li>
    </ul>
%endif
