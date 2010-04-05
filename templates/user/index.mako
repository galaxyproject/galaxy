<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

%if trans.user:
    <h2>${_('User preferences')}</h2>
    <p>You are currently logged in as ${trans.user.email}.</p>
    <ul>
        %if webapp == 'galaxy':
            <li><a href="${h.url_for( action='show_info' )}">${_('Manage your information')}</a></li>
            <li><a href="${h.url_for( action='set_default_permissions' )}">${_('Change default permissions')}</a> for new histories</li>
        %endif
        <li><a href="${h.url_for( action='logout' )}">${_('Logout')}</a></li>
    </ul>
%else:
    %if not msg:
        <p>${n_('You are currently not logged in.')}</p>
    %endif
    <ul>
        <li><a href="${h.url_for( action='login' )}">${_('Login')}</li>
        <li><a href="${h.url_for( action='create' )}">${_('Register')}</a></li>
    </ul>
%endif
