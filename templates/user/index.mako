<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

%if trans.user:
    <h2>${_('User preferences')}</h2>
    <p>You are currently logged in as ${trans.user.email}.</p>
    <ul>
        %if t.webapp.name == 'galaxy':
            %if not trans.app.config.use_remote_user:
                <li><a href="${h.url_for( controller='user', action='manage_user_info', cntrller=cntrller )}">${_('Manage your information')}</a> (email, password, etc.)</li>
            %endif
            <li><a href="${h.url_for( controller='user', action='set_default_permissions', cntrller=cntrller )}">${_('Change default permissions')}</a> for new histories</li>
            <li><a href="${h.url_for( controller='user', action='api_keys', cntrller=cntrller )}">${_('Manage your API keys')}</a></li>
            <li><a href="${h.url_for( controller='user', action='toolbox_filters', cntrller=cntrller )}">${_('Manage your ToolBox filters')}</a></li>
            %if trans.app.config.enable_openid and not trans.app.config.use_remote_user:
                <li><a href="${h.url_for( controller='user', action='openid_manage', cntrller=cntrller )}">${_('Manage OpenIDs')}</a> linked to your account</li>
            %endif
            <li><a href="${h.url_for( controller='user', action='logout', logout_all=True )}" target="_top">${_('Logout')}</a> ${_('of all user sessions')}</li>
        %else:
            <li><a href="${h.url_for( controller='user', action='manage_user_info', cntrller=cntrller )}">${_('Manage your information')}</a></li>
            <li><a href="${h.url_for( controller='user', action='api_keys', cntrller=cntrller )}">${_('Manage your API keys')}</a></li>
            <li><a href="${h.url_for( controller='repository', action='manage_email_alerts', cntrller=cntrller )}">${_('Manage your email alerts')}</a></li>
            <li><a href="${h.url_for( controller='user', action='logout', logout_all=True )}" target="_top">${_('Logout')}</a> ${_('of all user sessions')}</li>
        %endif
    </ul>
    %if t.webapp.name == 'galaxy':
        <p>
            You are using <strong>${trans.user.get_disk_usage( nice_size=True )}</strong> of disk space in this Galaxy instance.
            %if trans.app.config.enable_quotas:
                Your disk quota is: <strong>${trans.app.quota_agent.get_quota( trans.user, nice_size=True )}</strong>.
            %endif
            Is your usage more than expected?  See the <a href="https://wiki.galaxyproject.org/Learn/ManagingDatasets" target="_blank">documentation</a> for tips on how to find all of the data in your account.
        </p>
    %endif
%else:
    %if not message:
        <p>${n_('You are currently not logged in.')}</p>
    %endif
    <ul>
        <li><a href="${h.url_for( controller='user', action='login' )}">${_('Login')}</li>
        <li><a href="${h.url_for( controller='user', action='create', cntrller='user' )}">${_('Register')}</a></li>
    </ul>
%endif
