<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if ( trans.user_is_admin() and cntrller == 'library_admin' ) or trans.app.security_agent.can_manage_library_item( current_user_roles, library ):
    ${render_permission_form( library, library.name, h.url_for( controller='library_common', action='library_permissions', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=show_deleted ), roles, do_not_render=[], all_roles=all_roles )}
%endif
