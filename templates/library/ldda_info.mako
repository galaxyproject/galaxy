<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common.mako" import="render_available_templates" />
<%namespace file="/library/common.mako" import="render_library_item_info" />
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
        <a class="action-button" href="${h.url_for( controller='library', action='browse_library', id=library_id )}"><span>Browse this library</span></a>
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
            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=ldda.library_dataset ):
                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library_id, folder_id=ldda.library_dataset.folder.id, id=ldda.id, edit_info=True )}">Edit this dataset's information</a>
            %else:
                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library_id, folder_id=ldda.library_dataset.folder.id, id=ldda.id, information=True )}">View this dataset's information</a>
            %endif
            ## We're disabling the ability to add templates at the LDDA and LibraryDataset level, but will leave this here for possible future use
            ##%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=ldda.library_dataset ):
            ##    <a class="action-button" href="${h.url_for( controller='library', action='info_template', library_id=library_id, library_dataset_id=ldda.library_dataset.id, new_template=True )}">Add an information template to this dataset</a>
            ##%endif
            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset=ldda.dataset ) and trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=ldda.library_dataset ):
                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library_id, folder_id=ldda.library_dataset.folder.id, id=ldda.id, permissions=True )}">Edit this dataset's permissions</a>
            %if current_version and trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=ldda.library_dataset ):
                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library_id, folder_id=ldda.library_dataset.folder.id, replace_id=ldda.library_dataset.id )}">Upload a new version of this dataset</a>
            %endif
            %endif
            %if ldda.has_data:
                <a class="action-button" href="${h.url_for( controller='library', action='datasets', library_id=library_id, ldda_ids=str( ldda.id ), do_action='add' )}">Import this dataset into your current history</a>
                <a class="action-button" href="${h.url_for( controller='library', action='download_dataset_from_folder', id=ldda.id, library_id=library_id )}">Download this dataset</a>
            %endif
        </div>
    </div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Message:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${ldda.message}
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Uploaded by:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${uploaded_by}
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Date uploaded:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${ldda.create_time.strftime( "%Y-%m-%d" )}
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Build:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${ldda.dbkey}
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Miscellaneous information:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${ldda.info}
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <div>${ldda.blurb}</div>
        </div>
        <div class="form-row">
           <div id="info${ldda.id}" class="historyItemBody">
                %if ldda.peek != "no peek":
                    <label>Peek:</label>
                    <div><pre id="peek${ldda.id}" class="peek">${ldda.display_peek()}</pre></div>
                %endif
                ## Recurse for child datasets
                %if len( ldda.visible_children ) > 0:
                    <div>
                        There are ${len( ldda.visible_children )} secondary datasets.
                        %for idx, child in enumerate( ldda.visible_children ):
                            ## TODO: do we need to clarify if the child is deleted?
                            %if not child.purged:
                                ${ render_dataset( child, selected, library ) }
                            %endif
                        %endfor
                    </div>
                %endif
            </div>
        </div>
    </div>
    %if ldda.library_dataset_dataset_info_associations:
        ${render_library_item_info( ldda, library_id )}
    %endif
    %if current_version:
        <% expired_lddas = [ e_ldda for e_ldda in ldda.library_dataset.expired_datasets ] %>
        %if expired_lddas:
            <div class="toolFormTitle">Expired versions of ${ldda.name}</div>
            %for expired_ldda in expired_lddas:
                <div class="form-row">
                    <a href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library_id, folder_id=expired_ldda.library_dataset.folder.id, id=expired_ldda.id, info=True )}">${expired_ldda.name}</a>
                </div>
            %endfor
        %endif
    %endif
</div>
