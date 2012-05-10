<% _=n_ %>

<%def name="render_download_links( data, dataset_id )">
    <%
        from galaxy.datatypes.metadata import FileParameter
    %>
    %if not data.purged:
        ## Check for downloadable metadata files
        <% meta_files = [ k for k in data.metadata.spec.keys() if isinstance( data.metadata.spec[k].param, FileParameter ) ] %>
        %if meta_files:
            <div popupmenu="dataset-${dataset_id}-popup">
                <a class="action-button" href="${h.url_for( controller='dataset', action='display', dataset_id=dataset_id, \
                    to_ext=data.ext )}">Download Dataset</a>
                <a>Additional Files</a>
            %for file_type in meta_files:
                <a class="action-button" href="${h.url_for( controller='/dataset', action='get_metadata_file', \
                    hda_id=dataset_id, metadata_name=file_type )}">Download ${file_type}</a>
            %endfor
            </div>
            <div style="float:left;" class="menubutton split popup" id="dataset-${dataset_id}-popup">
        %endif
        <a href="${h.url_for( controller='dataset', action='display', dataset_id=dataset_id, to_ext=data.ext )}" title='${_("Download")}' class="icon-button disk tooltip"></a>
        %if meta_files:
            </div>
        %endif
    %endif
</%def>

## Render the dataset `data` as history item, using `hid` as the displayed id
<%def name="render_dataset( data, hid, show_deleted_on_refresh = False, for_editing = True, display_structured = False )">
    <%
        dataset_id = trans.security.encode_id( data.id )

        if data.state in ['no state','',None]:
            data_state = "queued"
        else:
            data_state = data.state
        current_user_roles = trans.get_current_user_roles()
        can_edit = not ( data.deleted or data.purged )
    %>
    %if not trans.user_is_admin() and not trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
        <div class="historyItemWrapper historyItem historyItem-${data_state} historyItem-noPermission" id="historyItem-${dataset_id}">
    %else:
        <div class="historyItemWrapper historyItem historyItem-${data_state}" id="historyItem-${dataset_id}">
    %endif
        
    %if data.deleted or data.purged or data.dataset.purged:
        <div class="warningmessagesmall"><strong>
            %if data.dataset.purged or data.purged:
                This dataset has been deleted and removed from disk.
            %else:
                This dataset has been deleted. 
                %if for_editing:
                    Click <a href="${h.url_for( controller='dataset', action='undelete', dataset_id=dataset_id )}" class="historyItemUndelete" id="historyItemUndeleter-${dataset_id}" target="galaxy_history">here</a> to undelete
                    %if trans.app.config.allow_user_dataset_purge:
                        or <a href="${h.url_for( controller='dataset', action='purge', dataset_id=dataset_id )}" class="historyItemPurge" id="historyItemPurger-${dataset_id}" target="galaxy_history">here</a> to immediately remove it from disk.
                    %else:
                        it.
                    %endif
                %endif
            %endif
        </strong></div>
    %endif

    %if data.visible is False:
        <div class="warningmessagesmall">
            <strong>This dataset has been hidden. Click <a href="${h.url_for( controller='dataset', action='unhide', dataset_id=dataset_id )}" class="historyItemUnhide" id="historyItemUnhider-${dataset_id}" target="galaxy_history">here</a> to unhide.</strong>
        </div>
    %endif

    ## Header row for history items (name, state, action buttons)
    <div style="overflow: hidden;" class="historyItemTitleBar">     
        <div class="historyItemButtons">
            %if data_state == "upload":
                ## TODO: Make these CSS, just adding a "disabled" class to the normal
                ## links should be enough. However the number of datasets being uploaded
                ## at a time is usually small so the impact of these images is also small.
                <span title='${_("Display Data")}' class='icon-button display_disabled tooltip'></span>
                %if for_editing:
                    <span title='Edit Attributes' class='icon-button edit_disabled tooltip'></span>
                %endif
            %else:
                <% 
                    if for_editing:
                        display_url = h.url_for( controller='dataset', action='display', dataset_id=dataset_id, preview=True, filename='' )
                    else:
                        # Get URL for display only.
                        if data.history.user and data.history.user.username:
                            display_url = h.url_for( controller='dataset', action='display_by_username_and_slug',
                                                     username=data.history.user.username, slug=dataset_id, filename='' )
                        else:
                            # HACK: revert to for_editing display URL when there is no user/username. This should only happen when
                            # there's no user/username because dataset is being displayed by history/view after error reported.
                            # There are no security concerns here because both dataset/display and dataset/display_by_username_and_slug
                            # check user permissions (to the same degree) before displaying.
                            display_url = h.url_for( controller='dataset', action='display', dataset_id=dataset_id, preview=True, filename='' )
                %>
                %if data.purged:
                    <span class="icon-button display_disabled tooltip" title="Cannot display datasets removed from disk"></span>
                %else:
                    <a class="icon-button display tooltip" dataset_id="${dataset_id}" title='${_("Display data in browser")}' href="${display_url}"
                    %if for_editing:
                        target="galaxy_main"
                    %endif
                    ></a>
                %endif
                %if for_editing:
                    %if data.deleted and not data.purged:
                        <span title="Undelete dataset to edit attributes" class="icon-button edit_disabled tooltip"></span>
                    %elif data.purged:
                        <span title="Cannot edit attributes of datasets removed from disk" class="icon-button edit_disabled tooltip"></span>
                    %else:
                        <a class="icon-button edit tooltip" title='${_("Edit attributes")}' href="${h.url_for( controller='dataset', action='edit', dataset_id=dataset_id )}" target="galaxy_main"></a>
                    %endif
                %endif
            %endif
            %if for_editing:
                %if can_edit:
                    <a class="icon-button delete tooltip" title='${_("Delete")}' href="${h.url_for( controller='dataset', action='delete', dataset_id=dataset_id, show_deleted_on_refresh=show_deleted_on_refresh )}" id="historyItemDeleter-${dataset_id}"></a>
                %else:
                    <span title="Dataset is already deleted" class="icon-button delete_disabled tooltip"></span>
                %endif
            %endif
        </div>
        <span class="state-icon"></span>
        <span class="historyItemTitle">${hid}: ${data.display_name()}</span>
    </div>
        
    ## Body for history items, extra info and actions, data "peek"
    
    <div id="info${data.id}" class="historyItemBody">
        %if not trans.user_is_admin() and not trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
            <div>You do not have permission to view this dataset.</div>
        %elif data_state == "upload":
            <div>Dataset is uploading</div>
        %elif data_state == "queued":
            <div>${_('Job is waiting to run')}</div>
            <div>
                <a href="${h.url_for( controller='dataset', action='show_params', dataset_id=dataset_id )}" target="galaxy_main" title='${_("View Details")}' class="icon-button information tooltip"></a>
                %if for_editing:
                    <a href="${h.url_for( controller='tool_runner', action='rerun', id=data.id )}" target="galaxy_main" title='${_("Run this job again")}' class="icon-button arrow-circle tooltip"></a>
                %endif
            </div>
        %elif data_state == "running":
            <div>${_('Job is currently running')}</div>
            <div>
                <a href="${h.url_for( controller='dataset', action='show_params', dataset_id=dataset_id )}" target="galaxy_main" title='${_("View Details")}' class="icon-button information tooltip"></a>
                %if for_editing:
                    <a href="${h.url_for( controller='tool_runner', action='rerun', id=data.id )}" target="galaxy_main" title='${_("Run this job again")}' class="icon-button arrow-circle tooltip"></a>
                %endif
            </div>
        %elif data_state == "error":
            %if not data.purged:
                <div>${data.get_size( nice_size=True )}</div>
            %endif
            <div>
                An error occurred running this job: <i>${data.display_info().strip()}</i>
            </div>
            <div>
                %if for_editing:
                    <a href="${h.url_for( controller='dataset', action='errors', id=data.id )}" target="galaxy_main" title="View or report this error" class="icon-button bug tooltip"></a>
                %endif
                %if data.has_data():
                    ${render_download_links( data, dataset_id )}
                %endif
                <a href="${h.url_for( controller='dataset', action='show_params', dataset_id=dataset_id )}" target="galaxy_main" title='${_("View Details")}' class="icon-button information tooltip"></a>
                %if for_editing:
                    <a href="${h.url_for( controller='tool_runner', action='rerun', id=data.id )}" target="galaxy_main" title='${_("Run this job again")}' class="icon-button arrow-circle tooltip"></a>
                %endif
            </div>
        %elif data_state == "discarded":
            <div>
                The job creating this dataset was cancelled before completion.
            </div>
            <div>
                <a href="${h.url_for( controller='dataset', action='show_params', dataset_id=dataset_id )}" target="galaxy_main" title='${_("View Details")}' class="icon-button information tooltip"></a>
                %if for_editing:
                    <a href="${h.url_for( controller='tool_runner', action='rerun', id=data.id )}" target="galaxy_main" title='${_("Run this job again")}' class="icon-button arrow-circle tooltip"></a>
                %endif
            </div>
        %elif data_state == 'setting_metadata':
            <div>${_('Metadata is being Auto-Detected.')}</div>
        %elif data_state == "empty":
            <div>${_('No data: ')}<i>${data.display_info()}</i></div>
            <div>
                <a href="${h.url_for( controller='dataset', action='show_params', dataset_id=dataset_id )}" target="galaxy_main" title='${_("View Details")}' class="icon-button information tooltip"></a>
                %if for_editing:
                    <a href="${h.url_for( controller='tool_runner', action='rerun', id=data.id )}" target="galaxy_main" title='${_("Run this job again")}' class="icon-button arrow-circle tooltip"></a>
                %endif
            </div>
        %elif data_state in [ "ok", "failed_metadata" ]:
            %if data_state == "failed_metadata":
                <div class="warningmessagesmall" style="margin: 4px 0 4px 0">
                    An error occurred setting the metadata for this dataset.
                    %if can_edit:
                        You may be able to <a href="${h.url_for( controller='dataset', action='edit', dataset_id=dataset_id )}" target="galaxy_main">set it manually or retry auto-detection</a>.
                    %endif
                </div>
            %endif
            <div>
                ${data.blurb}<br />
                ${_("format: ")} <span class="${data.ext}">${data.ext}</span>, 
                ${_("database: ")}
                %if data.dbkey == '?' and can_edit:
                    <a href="${h.url_for( controller='dataset', action='edit', dataset_id=dataset_id )}" target="galaxy_main">${_(data.dbkey)}</a>
                %else:
                    <span class="${data.dbkey}">${_(data.dbkey)}</span>
                %endif
            </div>
            %if data.display_info():
                <div class="info">${_('Info: ')}${data.display_info()}</div>
            %endif
            <div>
                %if data.has_data():
                    ${render_download_links( data, dataset_id )}
                    
                    <a href="${h.url_for( controller='dataset', action='show_params', dataset_id=dataset_id )}" target="galaxy_main" title='${_("View Details")}' class="icon-button information tooltip"></a>
                    
                    %if for_editing:
                        <a href="${h.url_for( controller='tool_runner', action='rerun', id=data.id )}" target="galaxy_main" title='${_("Run this job again")}' class="icon-button arrow-circle tooltip"></a>
                        %if app.config.get_bool( 'enable_tracks', False ) and data.ext in app.datatypes_registry.get_available_tracks():
                            <%
                            if data.dbkey != '?':
                                data_url = h.url_for( controller='tracks', action='list_tracks', dbkey=data.dbkey )
                                data_url = data_url.replace( 'dbkey', 'f-dbkey' )
                            else:
                                data_url = h.url_for( controller='tracks', action='list_tracks' )
                            %>
                            <a href="javascript:void(0)" data-url="${data_url}" class="icon-button chart_curve tooltip trackster-add"
                                action-url="${h.url_for( controller='tracks', action='browser', dataset_id=dataset_id)}"
                                new-url="${h.url_for( controller='tracks', action='index', dataset_id=dataset_id, default_dbkey=data.dbkey)}" title="View in Trackster"></a>
                        %endif
                        %if trans.user:
                            %if not display_structured:
                                <div style="float: right">
                                    <a href="${h.url_for( controller='tag', action='retag', item_class=data.__class__.__name__, item_id=dataset_id )}" target="galaxy_main" title="Edit dataset tags" class="icon-button tags tooltip"></a>
                                    <a href="${h.url_for( controller='dataset', action='annotate', id=dataset_id )}" target="galaxy_main" title="Edit dataset annotation" class="icon-button annotate tooltip"></a>
                                </div>
                            %endif
                            <div style="clear: both"></div>
                            <div class="tag-area" style="display: none">
                                <strong>Tags:</strong>
                                <div class="tag-elt"></div>
                            </div>
                            <div id="${dataset_id}-annotation-area" class="annotation-area" style="display: none">
                                <strong>Annotation:</strong>
                                <div id="${dataset_id}-annotation-elt" style="margin: 1px 0px 1px 0px" class="annotation-elt tooltip editable-text" title="Edit dataset annotation"></div>
                            </div>
                            
                        %endif
                    %else:
                        ## When displaying datasets for viewing, this is often needed to prevent peek from overlapping
                        ## icons.
                        <div style="clear: both"></div>
                    %endif
                    <div style="clear: both"></div>
                    %for display_app in data.datatype.get_display_types():
                        <% target_frame, display_links = data.datatype.get_display_links( data, display_app, app, request.base ) %>
                        %if len( display_links ) > 0:
                            ${data.datatype.get_display_label(display_app)}
                            %for display_name, display_link in display_links:
                                <a target="${target_frame}" href="${display_link}">${_(display_name)}</a> 
                            %endfor
                            <br />
                        %endif
                    %endfor
                    %for display_app in data.get_display_applications( trans ).itervalues():
                        ${display_app.name} 
                        %for link_app in display_app.links.itervalues():
                            <a target="${link_app.url.get( 'target_frame', '_blank' )}" href="${link_app.get_display_url( data, trans )}">${_(link_app.name)}</a> 
                        %endfor
                        <br />
                    %endfor
                %elif for_editing:
                    <a href="${h.url_for( controller='dataset', action='show_params', dataset_id=dataset_id )}" target="galaxy_main" title='${_("View Details")}' class="icon-button information tooltip"></a>
                    <a href="${h.url_for( controller='tool_runner', action='rerun', id=data.id )}" target="galaxy_main" title='${_("Run this job again")}' class="icon-button arrow-circle tooltip"></a>
                %endif
    
                </div>
                %if data.peek != "no peek":
                    <div><pre id="peek${data.id}" class="peek">${_(h.to_unicode(data.display_peek()))}</pre></div>
                %endif            
        %else:
            <div>${_('Error: unknown dataset state "%s".') % data_state}</div>
        %endif
           
        ## Recurse for child datasets
                          
        %if len( data.children ) > 0:
            ## FIXME: This should not be in the template, there should
            ##        be a 'visible_children' method on dataset.
            <%
            children = []
            for child in data.children:
                if child.visible:
                    children.append( child )
            %>
            %if len( children ) > 0:
                <div>
                    There are ${len( children )} secondary datasets.
                    %for idx, child in enumerate(children):
                        ${render_dataset( child, idx + 1, show_deleted_on_refresh = show_deleted_on_refresh )}
                    %endfor
                </div>
            %endif
        %endif

    <div style="clear: both;"></div>

    </div>
        
        
    </div>

</%def>
