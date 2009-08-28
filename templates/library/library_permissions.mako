<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

<%
    user = trans.user
    if user:
        user_roles = user.all_roles()
    else:
        user_roles = None
%>

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library', action='browse_library', id=library.id )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if trans.app.security_agent.allow_action( user, user_roles, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=library ):
    <%
        roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all()
    %>
    ${render_permission_form( library, library.name, h.url_for( controller='library', action='library', id=library.id, permissions=True ), roles )}
%endif
