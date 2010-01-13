<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=library_id )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<% roles = trans.get_current_user_roles() %>

%if cntrller=='library_admin' or trans.app.security_agent.can_manage_library_item( roles, folder ):
    ## LIBRARY_ACCESS is a special permission that is set only at the library level.
    ${render_permission_form( folder, folder.name, h.url_for( controller='library_common', action='folder_permissions', cntrller=cntrller, id=trans.security.encode_id( folder.id ), library_id=library_id ), roles, do_not_render=[ 'LIBRARY_ACCESS' ] )}
%endif
