<%inherit file="/base.mako"/>

%if trans.user:
    <h2>${_('User preferences')}</h2>
    <p>You are currently logged in as ${trans.user.email|h}.</p>
    <ul>
        <li><a href="${h.url_for( controller='user', action='manage_user_info', cntrller=cntrller )}">${_('Manage your information')}</a></li>
        <li><a href="${h.url_for( controller='user', action='change_password', id=trans.app.security.encode_id(trans.user.id) )}">${_('Change your password')}</a></li>
        <li><a href="${h.url_for( controller='user', action='api_keys', cntrller=cntrller )}">${_('Manage your API keys')}</a></li>
        <li><a href="${h.url_for( controller='repository', action='manage_email_alerts', cntrller=cntrller )}">${_('Manage your email alerts')}</a></li>
        <li><a href="${h.url_for( controller='user', action='logout', logout_all=True )}" target="_top">${_('Logout')}</a> ${_('of all user sessions')}</li>
    </ul>
%else:
    %if not message:
        <p>${n_('You are currently not logged in.')}</p>
    %endif
    <ul>
        <li><a href="${h.url_for( controller='user', action='login' )}">${_('Login')}</li>
        <li><a href="${h.url_for( controller='user', action='create', cntrller='user' )}">${_('Register')}</a></li>
    </ul>
%endif
