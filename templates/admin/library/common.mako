## Render the dataset `data`
<%def name="render_dataset( data, selected, deleted )">
    <%
        ## The received data must always be a LibraryDataset object, but the object id passed to methods from the drop down menu
        ## should be the underlying ldda id to prevent id collision, which could happen when displaying children, which are always
        ## lddas and to function correctly with existing code.  We also need to make sure we're displaying the latest version of
        ## this library_dataset, so we display the attributes from the ldda.
        ldda = data.library_dataset_dataset_association
    %>
    <div class="historyItemWrapper historyItem historyItem-${data.state}" id="libraryItem-${ldda.id}">
        ## Header row for library items (name, state, action buttons)
        <div style="overflow: hidden;" class="historyItemTitleBar">     
            <table cellspacing="0" cellpadding="0" border="0" width="100%">
                <tr>
                    <td width="*">
                        %if selected:
                            <input type="checkbox" name="ldda_ids" value="${ldda.id}" checked/>
                        %else:
                            <input type="checkbox" name="ldda_ids" value="${ldda.id}"/>
                        %endif
                        <span class="historyItemTitle"><b>${ldda.name}</b></span>
                        %if not deleted:
                            <%
                                library_item_ids = {}
                                library_item_ids[ 'library_dataset_dataset_association' ] = ldda.id
                            %>
                            <a id="dataset-${ldda.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                            <div popupmenu="dataset-${ldda.id}-popup">
                                <a class="action-button" href="${h.url_for( controller='admin', action='dataset', ldda_id=ldda.id )}">Edit this dataset's attributes and permissions</a>
                                <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset', id=data.id )}">Manage this dataset's versions</a>
                                <a class="action-button" href="${h.url_for( controller='admin', action='library_item_info_template', library_dataset_dataset_association_id=ldda.id, new_element_count=5, **library_item_ids )}">Create a new template for this dataset</a>
                                %if data.has_data:
                                    <a class="action-button" href="${h.url_for( controller='admin', action='download_dataset_from_folder', id=ldda.id )}">Download this dataset</a>
                                %endif
                                ##TODO: need to revamp the way we remove datasets from disk.
                                ##<a class="action-button" confirm="Click OK to remove dataset '${ldda.name}'?" href="${h.url_for( controller='admin', action='dataset', delete=True, ldda_id=ldda.id )}">Remove this dataset from the library</a>
                            </div>
                        %endif
                    </td>
                    <td width="100">${ldda.ext}</td>
                    <td width="50"><span class="${ldda.dbkey}">${ldda.dbkey}</span></td>
                    <td width="200">${ldda.info}</td>
                </tr>
            </table>
        </div>
        
        ## Body for library items, extra info and actions, data "peek"
        <div id="info${ldda.id}" class="historyItemBody">
            <div>${ldda.blurb}</div>
            <div> 
                %if data.has_data:
                    %for display_app in data.datatype.get_display_types():
                        <% display_links = data.datatype.get_display_links( data, display_app, app, request.base ) %>
                        %if len( display_links ) > 0:
                            ${data.datatype.get_display_label(display_app)}
                            %for data.name, display_link in display_links:
                                <a target="_blank" href="${display_link}">${data.name}</a> 
                            %endfor
                        %endif
                    %endfor
                %endif
            </div>
            %if ldda.peek != "no peek":
                <div><pre id="peek${ldda.id}" class="peek">${ldda.display_peek()}</pre></div>
            %endif
            ## Recurse for child datasets
            %if len( data.visible_children ) > 0:
                <div>
                    There are ${len( data.visible_children )} secondary datasets.
                    %for idx, child in enumerate( data.visible_children ):
                        ${ render_dataset( child, selected, deleted ) }
                    %endfor
                </div>
            %endif
        </div>
    </div>
</%def>

<%def name="render_available_templates( library_item )">
    <%
        library_item_ids = {}
        available_template_assocs = []
        if isinstance( library_item, trans.app.model.Library ):
            library_item_ids[ 'library_id' ] = library_item.id
            available_template_assocs = library_item.library_info_template_associations
        elif isinstance( library_item, trans.app.model.LibraryFolder ):
            library_item_ids[ 'folder_id' ] = library_item.id
            available_template_assocs = library_item.library_folder_info_template_associations
        elif isinstance( library_item, trans.app.model.LibraryDataset ):
            library_item_ids[ 'library_dataset_id' ] = library_item.id
            available_template_assocs = library_item.library_dataset_info_template_associations
        elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
            library_item_ids[ 'library_dataset_dataset_association_id' ] = library_item.id
            available_template_assocs = library_item.library_dataset_dataset_info_template_associations
    %>
    %if available_template_assocs:
        <div class="toolForm">
            <div class="toolFormTitle">Available Templates</div>
            <div class="toolFormBody">
                %for available_template_assoc in available_template_assocs:
                    <div class="form-row">
                        <a href="${h.url_for( controller='admin', action='library_item_info_template', id=available_template_assoc.library_item_info_template.id )}">${available_template_assoc.library_item_info_template.name}</a>: ${available_template_assoc.library_item_info_template.description}
                        <div style="clear: both"></div>
                    </div>
                %endfor
            </div>
        </div>
        <p/>
    %endif
</%def>
