<%inherit file="/base.mako"/>
<%def name="title()">${_('Account settings')}</%def>

<h1>${_('Account settings')}</h1>

%if user:
    <p>${_('You are currently logged in as %s.') % user.email}</p>
    <ul>
        <li><a href="${h.url_for( action='change_password' )}">${_('Change your password')}</a></li>
        <li><a href="${h.url_for( action='change_email' )}">${_('Update your email address')}</a></li>
        <li><a href="${h.url_for( action='logout' )}">${_('Logout')}</a></li>
    </ul>
%else:
    <p>${n_('You are currently not logged in.')}</p>
    <ul>
        <li><a href="${h.url_for( action='login' )}">${_('Login')}</li>
        <li><a href="${h.url_for( action='create' )}">${_('Create new account')}</a></li>
    </ul>
%endif