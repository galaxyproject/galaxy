<%inherit file="/base.mako"/>
<%def name="title()">User preferences</%def>

<h2>${_('User preferences')}</h2>

%if user:
    <p>You are currently logged in as ${user.email}.</p>
    <ul>
        <li><a href="${h.url_for( action='change_password' )}">${_('Change your password')}</a></li>
        <li><a href="${h.url_for( action='change_email' )}">${_('Update your email address')}</a></li>
        <li><a href="${h.url_for( action='set_default_permissions' )}">${_('Change default permissions')}</a> for new histories</li>
        <li><a href="${h.url_for( action='logout' )}">${_('Logout')}</a></li>
    </ul>
%else:
    <p>${n_('You are currently not logged in.')}</p>
    <ul>
        <li><a href="${h.url_for( action='login' )}">${_('Login')}</li>
        <li><a href="${h.url_for( action='create' )}">${_('Register')}</a></li>
    </ul>
%endif
