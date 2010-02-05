<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common/common.mako" import="render_template_info" />

<%
    if cntrller in [ 'library', 'requests' ]:
        can_add = trans.app.security_agent.can_add_library_item( current_user_roles, library )
        can_modify = trans.app.security_agent.can_modify_library_item( current_user_roles, library )
        can_manage = trans.app.security_agent.can_manage_library_item( current_user_roles, library )
    info_association, inherited = library.get_info_association()
%>

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if cntrller == 'library_admin' or can_modify:
    <div class="toolForm">
        <div class="toolFormTitle">Change library name and description</div>
        <div class="toolFormBody">
            <form name="library" action="${h.url_for( controller='library_common', action='library_info', id=trans.security.encode_id( library.id ), cntrller=cntrller, show_deleted=show_deleted )}" method="post" >
                <div class="form-row">
                    <label>Name:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="name" value="${library.name}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Description:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="description" value="${library.description}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <input type="submit" name="rename_library_button" value="Save"/>
                </div>
            </form>
        </div>
    </div>
    <p/>
%else:
    <div class="toolForm">
        <div class="toolFormTitle">
            %if cntrller == 'library_admin' or can_add or can_manage:
                <th style="padding-left: 42px;">
                    <a href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}"><b>${library.name[:50]}</b></a>
                    <a id="library-${library.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                    <div popupmenu="library-${library.id}-popup">
                        %if not library.deleted:
                            %if ( cntrller == 'library_admin' or can_add ) and not library.info_association:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='add_info_template', cntrller=cntrller, item_type='library', library_id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}">Add template</a>
                            %endif
                            %if cntrller == 'library_admin' and info_association:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='delete_info_template', cntrller=cntrller, item_type='library', library_id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}">Delete template</a>
                            %endif
                            %if cntrller == 'library_admin' or can_manage:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='library_permissions', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}">Edit permissions</a>
                            %endif
                            %if cntrller == 'library_admin':
                                <a class="action-button" confirm="Click OK to delete the library named '${library.name}'." href="${h.url_for( controller='library_admin', action='delete_library_item', library_id=trans.security.encode_id( library.id ), library_item_id=trans.security.encode_id( library.id ), library_item_type='library' )}">Delete this data library and its contents</a>
                            %endif
                        %elif cntrller == 'library_admin' and not library.purged:
                            <a class="action-button" href="${h.url_for( controller='library_admin', action='undelete_library_item', library_id=trans.security.encode_id( library.id ), library_item_id=trans.security.encode_id( library.id ), library_item_type='library' )}">Undelete this data library</a>
                        %endif
                    </div>
                </th>
            %else:
                <th style="padding-left: 42px;">
                    <a href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}"><b>${library.name[:50]}</b></a>
                </th>
            %endif
        </div>
        <div class="toolFormBody">
            <div class="form-row">
                <label>Name:</label>
                ${library.name}
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Description:</label>
                ${library.description}
            </div>
            <div style="clear: both"></div>
        </div>
    </div>
%endif

%if widgets:
    ${render_template_info( cntrller=cntrller, item_type='library', library_id=trans.security.encode_id( library.id ), widgets=widgets )}
%endif
