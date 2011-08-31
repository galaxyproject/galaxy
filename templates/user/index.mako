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
            <li><a href="${h.url_for( controller='user', action='manage_user_info', cntrller=cntrller )}">${_('Manage your information')}</a></li>
            <li><a href="${h.url_for( controller='user', action='set_default_permissions', cntrller=cntrller )}">${_('Change default permissions')}</a> for new histories</li>
            %if trans.app.config.enable_api:
                <li><a href="${h.url_for( controller='user', action='api_keys', cntrller=cntrller )}">${_('Manage your API keys')}</a></li>
            %endif
            %if trans.app.config.enable_openid:
                <li><a href="${h.url_for( controller='user', action='openid_manage', cntrller=cntrller )}">${ ('Manage OpenIDs')}</a> linked to your account</li>
            %endif
        %else:
            <li><a href="${h.url_for( controller='user', action='manage_user_info', cntrller=cntrller,  webapp='community' )}">${_('Manage your information')}</a></li>
        %endif
    </ul>
    <p>
        You are using <strong>${trans.user.get_disk_usage( nice_size=True )}</strong> of disk space in this Galaxy instance.
        %if trans.app.config.enable_quotas:
            Your disk quota is: <strong>${trans.app.quota_agent.get_quota( trans.user, nice_size=True )}</strong>.
        %endif
    </p>
%else:
    %if not message:
        <p>${n_('You are currently not logged in.')}</p>
    %endif
    <ul>
        <li><a href="${h.url_for( action='login' )}">${_('Login')}</li>
        <li><a href="${h.url_for( action='create', cntrller='user' )}">${_('Register')}</a></li>
    </ul>
%endif
