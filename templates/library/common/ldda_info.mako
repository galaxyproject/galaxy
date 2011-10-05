<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/common/template_common.mako" import="render_template_fields" />
<%
    from galaxy import util
    from galaxy.web.controllers.library_common import branch_deleted, get_containing_library_from_library_dataset
    from galaxy.web.framework.helpers import time_ago

    if ldda == ldda.library_dataset.library_dataset_dataset_association:
        current_version = True
    else:
        current_version = False
    if ldda.user:
        uploaded_by = ldda.user.email
    else:
        uploaded_by = 'anonymous'
    if trans.user_is_admin() and cntrller == 'library_admin':
        can_modify = can_manage = True
    elif cntrller in [ 'library', 'requests' ]:
        can_modify = trans.app.security_agent.can_modify_library_item( current_user_roles, ldda.library_dataset )
        can_manage = trans.app.security_agent.can_manage_library_item( current_user_roles, ldda.library_dataset )
    else:
        can_modify = can_manage = False
    form_type = trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
%>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

%if current_version:
    <b><i>This is the latest version of this library dataset</i></b>
%else:
    <font color="red"><b><i>This is an expired version of this library dataset</i></b></font>
%endif
<p/>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">
        Information about <div class="menubutton popup" id="dataset-${ldda.id}-popup">${ldda.name}</div>
        %if not library.deleted and not branch_deleted( ldda.library_dataset.folder ) and not ldda.library_dataset.deleted:
            <div popupmenu="dataset-${ldda.id}-popup">
                %if can_modify:
                    <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_edit_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit information</a>
                    %if not info_association:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type='ldda', form_type=form_type, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), ldda_id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Use template</a>
                    %else:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='edit_template', cntrller=cntrller, item_type='ldda', form_type=form_type, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), ldda_id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit template</a>
                        <a class="action-button" href="${h.url_for( controller='library_common', action='delete_template', cntrller=cntrller, item_type='ldda', form_type=form_type, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), ldda_id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Unuse template</a>
                    %endif
                %endif
                %if can_manage:
                    <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_permissions', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit permissions</a>
                %endif
                %if current_version and can_modify:
                    <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), replace_id=trans.security.encode_id( ldda.library_dataset.id ) )}">Upload a new version of this dataset</a>
                %endif
                %if ldda.has_data():
                    <a class="action-button" href="${h.url_for( controller='library_common', action='import_datasets_to_histories', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), ldda_ids=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Import this dataset into selected histories</a>
                    <a class="action-button" href="${h.url_for( controller='library_common', action='download_dataset_from_folder', cntrller=cntrller, id=trans.security.encode_id( ldda.id ), library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Download this dataset</a>
                %endif
                %if show_associated_hdas_and_lddas:
                    <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), id=trans.security.encode_id( ldda.id ), show_associated_hdas_and_lddas=False, use_panels=use_panels, show_deleted=show_deleted )}">Hide items using this dataset's disk file</a>
                %else:
                    <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), id=trans.security.encode_id( ldda.id ), show_associated_hdas_and_lddas=True, use_panels=use_panels, show_deleted=show_deleted )}">Show items using this dataset's disk file</a>
                %endif
            </div>
        %endif
    </div>
    <div class="toolFormBody">
        %if ldda.message:
            <div class="form-row">
                <label>Message:</label>
                <pre>${ldda.message}</pre>
                <div style="clear: both"></div>
            </div>
        %endif
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
            <label>File size:</label>
            ${ldda.get_size( nice_size=True )}
            <div style="clear: both"></div>
        </div>
        %if ldda.tool_version:
            <div class="form-row">
                <label>Tool version:</label>
                ${ldda.tool_version}
                <div style="clear: both"></div>
            </div>
        %endif
        <div class="form-row">
            <label>Data type:</label>
            ${ldda.ext}
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
        %if ldda.creating_job_associations:
            <% job = ldda.creating_job_associations[0].job %>
            %if job.stdout and job.stdout.strip() != '':
                <div class="form-row">
                    <label>Job Standard Output</label>
                    <pre>${job.stdout}</pre>
                    <div style="clear: both"></div>
                </div>
            %endif
            %if job.stderr and job.stderr.strip() != '':
                <div class="form-row">
                    <label>Job Standard Error</label>
                    <pre>${job.stderr}</pre>
                    <div style="clear: both"></div>
                </div>
            %endif
        %endif
        <div class="form-row">
            <div>${ldda.blurb}</div>
        </div>
        ## We want to display all metadata item here, whether marked visible or not since they are all pretty useful
        %for name, spec in ldda.metadata.spec.items():
            <div class="form-row">
                <label>${spec.desc.replace( ' (click box & select)', '' )}:</label>
                <%
                    metadata_val = ldda.metadata.get( name )
                    if isinstance( metadata_val, trans.model.MetadataFile ):
                        metadata_val = metadata_val.file_name
                    elif isinstance( metadata_val, list ):
                        # Make sure list items are strings
                        metadata_val = [ str( item ) for item in metadata_val ]
                        metadata_val = ', '.join( metadata_val )
                %>
                ${metadata_val}
                <div style="clear: both"></div>
            </div>
        %endfor
        %if ldda.peek != "no peek":
            <div class="form-row">
                <div id="info${ldda.id}" class="historyItemBody">
                    <label>Peek:</label>
                    <div><pre id="peek${ldda.id}" class="peek">${ldda.display_peek()}</pre></div>
                </div>
            </div>
        %endif
        %if trans.user_is_admin() and cntrller == 'library_admin':
            <div class="form-row">
                <label>Disk file:</label>
                ${ldda.file_name}
                <div style="clear: both"></div>
            </div>
        %endif
    </div>
</div>
%if widgets:
    ${render_template_fields( cntrller=cntrller, item_type='ldda', widgets=widgets, widget_fields_have_contents=widget_fields_have_contents, library_id=library_id, folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ), ldda_id=trans.security.encode_id( ldda.id ), info_association=info_association, inherited=inherited, editable=False )}
%endif
%if show_associated_hdas_and_lddas:
    %if associated_hdas:
        <p/>
        <b>Active (undeleted) history items that use this library dataset's disk file</b>
        <div class="toolForm">
            <table class="grid">
                <thead>
                    <tr>
                        <th>History</th>
                        <th>History Item</th>
                        <th>Last Updated</th>
                        <th>User</th>
                    </tr>
                </thead>
                %for hda in associated_hdas:
                    <tr>
                        <td>
                            %if hda.history:
                                <a target="_blank" href="${h.url_for( controller='history', action='view', id=trans.security.encode_id( hda.history_id ) )}">${hda.history.get_display_name()}</a>
                            %else:
                                no history
                            %endif
                        </td>
                        <td>${hda.get_display_name()}</td>
                        <td>${time_ago( hda.update_time )}</td>
                        <td>
                            %if hda.history and hda.history.user:
                                ${hda.history.user.email}
                            %else:
                                anonymous
                            %endif
                        </td>
                    </tr>
                %endfor
            </table>
        </div>
        <p/>
    %endif
    %if associated_lddas:
        <p/>
        <b>Other active (undeleted) library datasets that use this library dataset's disk file</b>
        <div class="toolForm">
            <table class="grid">
                <thead>
                    <tr>
                        <th>Library</th>
                        <th>Library Folder</th>
                        <th>Library Dataset</th>
                        <th>Last Updated</th>
                        <th>User</th>
                    </tr>
                </thead>
                %for copied_ldda in associated_lddas:
                    <% containing_library = get_containing_library_from_library_dataset( trans, copied_ldda.library_dataset ) %>
                    <tr>
                        <td>
                            <%
                                if containing_library:
                                    library_display_name = containing_library.get_display_name()
                                else:
                                    library_display_name = 'no library'
                            %>
                            %if containing_library:
                                <a href="${h.url_for( controller='library_common', action='browse_library', id=trans.security.encode_id( containing_library.id ), cntrller=cntrller, use_panels=use_panels )}">${library_display_name}</a>
                            %else:
                                ${library_display_name}
                            %endif
                        </td>
                        <td>
                            <%
                                library_dataset = copied_ldda.library_dataset
                                folder = library_dataset.folder
                                folder_display_name = folder.get_display_name()
                                if folder_display_name == library_display_name:
                                    folder_display_name = 'library root'
                            %>
                            ${folder_display_name}
                            ${copied_ldda.library_dataset.folder.get_display_name()}
                        </td>
                        <td>${copied_ldda.get_display_name()}</td>
                        <td>${time_ago( copied_ldda.update_time )}</td>
                        <td>
                            %if copied_ldda.user:
                                ${copied_ldda.user.email}
                            %else:
                                anonymous
                            %endif
                        </td>
                    </tr>
                %endfor
            </table>
        </div>
        <p/>
    %endif
%endif
%if current_version:
    <% expired_lddas = [ e_ldda for e_ldda in ldda.library_dataset.expired_datasets ] %>
    %if expired_lddas:
        <br/>
        <div class="toolFormTitle">Expired versions of ${ldda.name}</div>
        %for expired_ldda in expired_lddas:
            <div class="form-row">
                <a href="${h.url_for( controller='library_common', action='ldda_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( expired_ldda.library_dataset.folder.id ), id=trans.security.encode_id( expired_ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">${expired_ldda.name}</a>
            </div>
        %endfor
    %endif
%endif
