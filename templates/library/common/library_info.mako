<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common/common.mako" import="render_template_info" />

<%
    if cntrller in [ 'library', 'requests' ]:
        can_add = trans.app.security_agent.can_add_library_item( current_user_roles, library )
        can_modify = trans.app.security_agent.can_modify_library_item( current_user_roles, library )
        can_manage = trans.app.security_agent.can_manage_library_item( current_user_roles, library )
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

<div class="toolForm">
    %if cntrller == 'library_admin' or can_add or can_modify or can_manage:
        <div class="toolFormTitle">
            <a href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}"><b>${library.name[:50]}</b></a>
            <a id="library-${library.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            <div popupmenu="library-${library.id}-popup">
                %if not library.deleted:
                    %if ( cntrller == 'library_admin' or can_add ) and not library.info_association:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type='library', library_id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}">Add template</a>
                    %endif
                    %if cntrller == 'library_admin' or can_manage:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='library_permissions', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}">Edit permissions</a>
                    %endif
                    %if cntrller == 'library_admin':
                        <a class="action-button" confirm="Click OK to delete the library named '${library.name}'." href="${h.url_for( controller='library_admin', action='delete_library_item', library_id=trans.security.encode_id( library.id ), item_id=trans.security.encode_id( library.id ), item_type='library' )}">Delete this data library</a>
                    %endif
                %elif cntrller == 'library_admin' and not library.purged:
                    <a class="action-button" href="${h.url_for( controller='library_admin', action='undelete_library_item', library_id=trans.security.encode_id( library.id ), item_id=trans.security.encode_id( library.id ), item_type='library' )}">Undelete this data library</a>
                %elif library.purged:
                    <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}">This data library has been purged</a>
                %endif
            </div>
        </div>
    %endif
    <div class="toolFormBody">
        %if not library.deleted and ( cntrller == 'library_admin' or can_modify ):
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
                    <div class="toolParamHelp" style="clear: both;">
                        Displayed when browsing all libraries
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Synopsis:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="synopsis" value="${library.synopsis}" size="40"/>
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        Displayed when browsing this library
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <input type="submit" name="rename_library_button" value="Save"/>
                </div>
            </form>
        %else:
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
            <div class="form-row">
                <label>Synopsis:</label>
                ${library.synopsis}
            </div>
            <div style="clear: both"></div>
        %endif
    </div>
</div>

%if widgets:
    ${render_template_info( cntrller=cntrller, item_type='library', library_id=trans.security.encode_id( library.id ), widgets=widgets, info_association=info_association, inherited=inherited, editable=not( library.deleted ) )}
%endif
