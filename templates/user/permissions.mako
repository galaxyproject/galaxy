<%inherit file="/base.mako"/>
<%def name="title()">Change Default Permissions on New Histories</%def>
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller='user', cntrller=cntrller, action='index')}">User preferences</a>
    </li>
</ul>
%if trans.user:
    ${render_permission_form( trans.user, trans.user.email, h.url_for(), trans.user.all_roles() )}
%endif
