<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common/common.mako" import="render_template_info" />
<% from galaxy import util %>

<%
    if ldda == ldda.library_dataset.library_dataset_dataset_association:
        current_version = True
    else:
        current_version = False
%>

%if current_version:
    <b><i>This is the latest version of this library dataset</i></b>
%else:
    <font color="red"><b><i>This is an expired version of this library dataset</i></b></font>
%endif
<p/>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%
    if ldda.user:
        uploaded_by = ldda.user.email
    else:
        uploaded_by = 'anonymous'
%>

<div class="toolForm">
    <div class="toolFormTitle">
        Information about ${ldda.name}
        %if not library.deleted and not ldda.library_dataset.folder.deleted and not ldda.deleted:
            <a id="dataset-${ldda.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            <div popupmenu="dataset-${ldda.id}-popup">
                %if cntrller=='library_admin' or trans.app.security_agent.can_modify_library_item( current_user_roles, ldda.library_dataset ):
                    <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_edit_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), id=trans.security.encode_id( ldda.id ), show_deleted=show_deleted )}">Edit this dataset's information</a>
                %endif
                %if cntrller=='library_admin' or trans.app.security_agent.can_manage_dataset( current_user_roles, ldda.dataset ) and trans.app.security_agent.can_manage_library_item( current_user_roles, ldda.library_dataset ):
                    <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_permissions', library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), id=trans.security.encode_id( ldda.id ), show_deleted=show_deleted )}">Edit this dataset's permissions</a>
                %endif
                %if current_version and ( cntrller=='library_admin' or trans.app.security_agent.can_modify_library_item( current_user_roles, ldda.library_dataset ) ):
                    <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), replace_id=trans.security.encode_id( ldda.library_dataset.id ), show_deleted=show_deleted )}">Upload a new version of this dataset</a>
                %endif
                %if cntrller=='library' and ldda.has_data:
                    <a class="action-button" href="${h.url_for( controller='library_common', action='act_on_multiple_datasets', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), ldda_ids=trans.security.encode_id( ldda.id ), do_action='add', show_deleted=show_deleted )}">Import this dataset into your current history</a>
                    <a class="action-button" href="${h.url_for( controller='library', action='download_dataset_from_folder', cntrller=cntrller, id=trans.security.encode_id( ldda.id ), library_id=trans.security.encode_id( library.id ), show_deleted=show_deleted )}">Download this dataset</a>
                %endif
            </div>
        %endif
    </div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Message:</label>
            ${ldda.message}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Uploaded by:</label>
            ${uploaded_by}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Date uploaded:</label>
            ${ldda.create_time.strftime( "%Y-%m-%d" )}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Build:</label>
            ${ldda.dbkey}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Miscellaneous information:</label>
            ${ldda.info}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <div>${ldda.blurb}</div>
        </div>
        %if ldda.peek != "no peek":
            <div class="form-row">
               <div id="info${ldda.id}" class="historyItemBody">
                    <label>Peek:</label>
                    <div><pre id="peek${ldda.id}" class="peek">${ldda.display_peek()}</pre></div>
                </div>
            </div>
        %endif
    </div>
    %if widgets:
        ${render_template_info( cntrller=cntrller, item_type='ldda', library_id=library_id, widgets=widgets, folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), ldda_id=trans.security.encode_id( ldda.id ), editable=False )}
    %endif
    %if current_version:
        <% expired_lddas = [ e_ldda for e_ldda in ldda.library_dataset.expired_datasets ] %>
        %if expired_lddas:
            <div class="toolFormTitle">Expired versions of ${ldda.name}</div>
            %for expired_ldda in expired_lddas:
                <div class="form-row">
                    <a href="${h.url_for( controller='library_common', action='ldda_display_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( expired_ldda.library_dataset.folder.id ), id=trans.security.encode_id( expired_ldda.id ), show_deleted=show_deleted )}">${expired_ldda.name}</a>
                </div>
            %endfor
        %endif
    %endif
</div>
