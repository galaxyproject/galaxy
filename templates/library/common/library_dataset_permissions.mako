<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />>

<%
    if cntrller == 'library':
        user, roles = trans.get_user_and_roles()
%>

%if library_dataset == library_dataset.library_dataset_dataset_association.library_dataset:
    <b><i>This is the latest version of this library dataset</i></b>
%else:
    <font color="red"><b><i>This is an expired version of this library dataset</i></b></font>
%endif
<p/>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=library_id )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if trans.app.security_agent.can_manage_library_item( user, user_roles, library_dataset ):
    <%
        roles = trans.sa_session.query( trans.app.model.Role ) \
                                .filter( trans.app.model.Role.table.c.deleted==False ) \
                                .order_by( trans.app.model.Role.table.c.name )
    %>
    ${render_permission_form( library_dataset, library_dataset.name, h.url_for( controller='library_common', action='library_dataset_permissions', id=trans.security.encode_id( library_dataset.id ), library_id=library_id ), roles )}
%endif
