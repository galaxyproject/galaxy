<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

<%
    if not trans.user_is_admin():
        roles = trans.get_current_user_roles()
%>

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ) )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if trans.user_is_admin or trans.app.security_agent.can_manage_library_item( user_roles, library ):
    <%
        roles = trans.sa_session.query( trans.app.model.Role ) \
                                .filter( trans.app.model.Role.table.c.deleted==False ) \
                                .order_by( trans.app.model.Role.table.c.name )
    %>
    ${render_permission_form( library, library.name, h.url_for( controller='library_common', action='library_permissions', cntrller=cntrller, id=trans.security.encode_id( library.id ), cntrller=cntrller ), roles )}
%endif
