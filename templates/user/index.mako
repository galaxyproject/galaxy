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
            <li><a href="${h.url_for( controller='user', action='show_info' )}">${_('Manage your information')}</a></li>
            <li><a href="${h.url_for( controller='user', action='set_default_permissions' )}">${_('Change default permissions')}</a> for new histories</li>
            %if trans.app.config.enable_api:
                <li><a href="${h.url_for( controller='user', action='api_keys' )}">${_('Manage your API keys')}</a></li>
            %endif
            %if trans.app.config.enable_openid:
                <li><a href="${h.url_for( controller='user', action='openid_manage' )}">${ ('Manage OpenIDs')}</a> linked to your account</li>
            %endif
        %else:
            <li><a href="${h.url_for( controller='user', action='show_info', webapp='community' )}">${_('Manage your information')}</a></li>
        %endif
    </ul>
%else:
    %if not message:
        <p>${n_('You are currently not logged in.')}</p>
    %endif
    <ul>
        <li><a href="${h.url_for( action='login' )}">${_('Login')}</li>
        <li><a href="${h.url_for( action='create' )}">${_('Register')}</a></li>
    </ul>
%endif
