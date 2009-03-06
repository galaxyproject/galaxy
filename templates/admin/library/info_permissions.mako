<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='browse_library', id=library_id )}"><span>Browse this library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%
    roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all()
%>

${render_permission_form( library_item_info_element, library_item_info_element.library_item_info_template_element.name, h.url_for( controller='admin', action='library_item_info', id=library_item_info_element.library_item_info.id, library_id=library_id, library_item_type='library_item_info_elememt', permissions=True ), roles )}
