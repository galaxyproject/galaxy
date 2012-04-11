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
            <li><a href="${h.url_for( controller='user', action='manage_user_info', cntrller=cntrller, webapp=webapp )}">${_('Manage your information')}</a></li>
            <li><a href="${h.url_for( controller='user', action='set_default_permissions', cntrller=cntrller, webapp=webapp )}">${_('Change default permissions')}</a> for new histories</li>
            <li><a href="${h.url_for( controller='user', action='api_keys', cntrller=cntrller, webapp=webapp )}">${_('Manage your API keys')}</a></li>
            %if trans.app.config.enable_openid:
                <li><a href="${h.url_for( controller='user', action='openid_manage', cntrller=cntrller, webapp=webapp )}">${_('Manage OpenIDs')}</a> linked to your account</li>
            %endif
            %if trans.app.config.use_remote_user:
                %if trans.app.config.remote_user_logout_href:
                    <li><a href="${trans.app.config.remote_user_logout_href}" target="_top">${_('Logout')}</a></li>
                %endif
            %else:
                <li><a href="${h.url_for( controller='user', action='logout', webapp=webapp, logout_all=True )}" target="_top">${_('Logout')}</a> ${_('of all user sessions')}</li>
            %endif
        %else:
            <li><a href="${h.url_for( controller='user', action='manage_user_info', cntrller=cntrller,  webapp=webapp )}">${_('Manage your information')}</a></li>
            <li><a href="${h.url_for( controller='repository', action='manage_email_alerts', cntrller=cntrller,  webapp=webapp )}">${_('Manage your email alerts')}</a></li>
            <li><a href="${h.url_for( controller='user', action='logout', webapp=webapp, logout_all=True )}" target="_top">${_('Logout')}</a> ${_('of all user sessions')}</li>
        %endif
    </ul>
    %if webapp == 'galaxy':
        <p>
            You are using <strong>${trans.user.get_disk_usage( nice_size=True )}</strong> of disk space in this Galaxy instance.
            %if trans.app.config.enable_quotas:
                Your disk quota is: <strong>${trans.app.quota_agent.get_quota( trans.user, nice_size=True )}</strong>.
            %endif
            Is your usage more than expected?  See the <a href="http://wiki.g2.bx.psu.edu/Learn/Managing%20Datasets" target="_blank">documentation</a> for tips on how to find all of the data in your account.
        </p>
    %endif
%else:
    %if not message:
        <p>${n_('You are currently not logged in.')}</p>
    %endif
    <ul>
        <li><a href="${h.url_for( action='login', webapp=webapp )}">${_('Login')}</li>
        <li><a href="${h.url_for( action='create', cntrller='user', webapp=webapp )}">${_('Register')}</a></li>
    </ul>
%endif
