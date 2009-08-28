<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

<%
    user = trans.user
    if user:
        roles = user.all_roles()
    else:
        roles = None
%>

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library', action='browse_library', id=library_id )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if trans.app.security_agent.allow_action( user, roles, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=folder ):
    ${render_permission_form( folder, folder.name, h.url_for( controller='library', action='folder', id=folder.id, library_id=library_id, permissions=True ), trans.user.all_roles() )}
%endif
