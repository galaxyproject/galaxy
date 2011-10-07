<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

<%def name="title()">Change Default Permissions on New Histories</%def>

%if message:
    ${render_msg( message, status )}
%endif

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller='user', cntrller=cntrller, action='index')}">User preferences</a>
    </li>
</ul>
%if trans.user:
    ${render_permission_form( trans.user, trans.user.email, h.url_for( controller='user', action='set_default_permissions', cntrller=cntrller ), trans.user.all_roles() )}
%endif
