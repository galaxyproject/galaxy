<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/library/common.mako" import="render_template_info" />
<% from galaxy import util %>

<%
    if ldda == ldda.library_dataset.library_dataset_dataset_association:
        current_version = True
    else:
        current_version = False
    user, roles = trans.get_user_and_roles()
%>

%if current_version:
    <b><i>This is the latest version of this library dataset</i></b>
%else:
    <font color="red"><b><i>This is an expired version of this library dataset</i></b></font>
%endif
<p/>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library', action='browse_library', obj_id=library_id )}"><span>Browse this data library</span></a>
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
        <a id="dataset-${ldda.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
        <div popupmenu="dataset-${ldda.id}-popup">
            %if trans.app.security_agent.can_modify_library_item( user, roles, ldda.library_dataset ):
                <a class="action-button" href="${h.url_for( controller='library', action='ldda_edit_info', library_id=library_id, folder_id=ldda.library_dataset.folder.id, obj_id=ldda.id )}">Edit this dataset's information</a>
            %else:
                <a class="action-button" href="${h.url_for( controller='library', action='ldda_display_info', library_id=library_id, folder_id=ldda.library_dataset.folder.id, obj_id=ldda.id )}">View this dataset's information</a>
            %endif
            %if trans.app.security_agent.can_manage_dataset( roles, ldda.dataset ) and trans.app.security_agent.can_manage_library_item( user, roles, ldda.library_dataset ):
                <a class="action-button" href="${h.url_for( controller='library', action='ldda_manage_permissions', library_id=library_id, folder_id=ldda.library_dataset.folder.id, obj_id=ldda.id, permissions=True )}">Edit this dataset's permissions</a>
            %endif
            %if current_version and trans.app.security_agent.can_modify_library_item( user, roles, ldda.library_dataset ):
                <a class="action-button" href="${h.url_for( controller='library', action='upload_library_dataset', library_id=library_id, folder_id=ldda.library_dataset.folder.id, replace_id=ldda.library_dataset.id )}">Upload a new version of this dataset</a>
            %endif
            %if ldda.has_data:
                <a class="action-button" href="${h.url_for( controller='library', action='datasets', library_id=library_id, ldda_ids=str( ldda.id ), do_action='add' )}">Import this dataset into your current history</a>
                <a class="action-button" href="${h.url_for( controller='library', action='download_dataset_from_folder', obj_id=ldda.id, library_id=library_id )}">Download this dataset</a>
            %endif
        </div>
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
        ${render_template_info( ldda, library_id, 'ldda_display_info', widgets, editable=False )}
    %endif
    %if current_version:
        <% expired_lddas = [ e_ldda for e_ldda in ldda.library_dataset.expired_datasets ] %>
        %if expired_lddas:
            <div class="toolFormTitle">Expired versions of ${ldda.name}</div>
            %for expired_ldda in expired_lddas:
                <div class="form-row">
                    <a href="${h.url_for( controller='library', action='ldda_display_info', library_id=library_id, folder_id=expired_ldda.library_dataset.folder.id, obj_id=expired_ldda.id )}">${expired_ldda.name}</a>
                </div>
            %endfor
        %endif
    %endif
</div>
