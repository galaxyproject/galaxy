<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />>

%if library_dataset == library_dataset.library_dataset_dataset_association.library_dataset:
    <b><i>This is the latest version of this library dataset</i></b>
%else:
    <font color="red"><b><i>This is an expired version of this library dataset</i></b></font>
%endif
<p/>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=library_id, use_panels=use_panels, show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if ( trans.user_is_admin() and cntrller == 'library_admin' ) or trans.app.security_agent.can_manage_library_item( current_user_roles, library_dataset ):
    ## LIBRARY_ACCESS is a special permission that is set only at the library level.
    ${render_permission_form( library_dataset, library_dataset.name, h.url_for( controller='library_common', action='library_dataset_permissions', cntrller=cntrller, id=trans.security.encode_id( library_dataset.id ), library_id=library_id, show_deleted=show_deleted ), roles, do_not_render=[ 'LIBRARY_ACCESS' ] )}
%endif
