## Render the dataset `data`
<%def name="render_dataset( data, selected, library )">
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
                        %if not library.deleted:
                            <%
                                library_item_ids = {}
                                library_item_ids[ 'ldda' ] = ldda.id
                            %>
                            <a id="dataset-${ldda.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                            <div popupmenu="dataset-${ldda.id}-popup">
                                <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', id=ldda.id, library_id=library.id )}">Edit this dataset's information</a>
                                <a class="action-button" href="${h.url_for( controller='admin', action='library_item_info_template', library_dataset_id=data.id, new_element_count=5, **library_item_ids )}">Create a new information template for this dataset</a>
                                <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset', id=data.id, library_id=library.id )}">Manage this dataset's versions</a>
                                %if data.has_data:
                                    <a class="action-button" href="${h.url_for( controller='admin', action='download_dataset_from_folder', id=ldda.id, library_id=library.id )}">Download this dataset</a>
                                %endif
                                ##TODO: need to revamp the way we remove datasets from disk.
                                ##<a class="action-button" confirm="Click OK to remove dataset '${ldda.name}'?" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', delete=True, id=ldda.id, library_id=library.id )}">Remove this dataset from the library</a>
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
                        ${ render_dataset( child, selected, library.deleted ) }
                    %endfor
                </div>
            %endif
        </div>
    </div>
</%def>

<%def name="render_existing_library_item_info( library_item )">
    <%
        library_item_type = None
        library_item_info_associations = []
        if isinstance( library_item, trans.app.model.Library ):
            library_item_type = 'library'
            library_item_desc = 'library'
            library_item_info_associations = library_item.library_info_associations
        elif isinstance( library_item, trans.app.model.LibraryFolder ):
            library_item_type = 'folder'
            library_item_desc = 'folder'
            library_item_info_associations = library_item.library_folder_info_associations
        elif isinstance( library_item, trans.app.model.LibraryDataset ):
            library_item_type = 'library_dataset'
            library_item_desc = 'library dataset'
            library_item_info_associations = library_item.library_dataset_info_associations
        elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
            library_item_type = 'library_dataset_dataset_association'
            library_item_desc = 'library dataset <-> dataset association'
            library_item_info_associations = library_item.library_dataset_dataset_info_associations
    %>
    <div class="toolForm">
        <div class="toolFormTitle">Other information about ${library_item_desc} ${library_item.name}</div>
        <div class="toolFormBody">
            %for available_info_assoc in library_item_info_associations:
                %for template_info_element in available_info_assoc.library_item_info.library_item_info_template.elements:
                    <div class="form-row">
                        <b>${template_info_element.name}:</b>
                        ${available_info_assoc.library_item_info.get_element_by_template_element( template_info_element ).contents}
                        <div style="clear: both"></div>
                    </div>
                %endfor
                <div style="clear: both"></div>
            %endfor
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
            library_item_desc = 'library'
        elif isinstance( library_item, trans.app.model.LibraryFolder ):
            library_item_ids[ 'folder_id' ] = library_item.id
            available_template_assocs = library_item.library_folder_info_template_associations
            library_item_desc = 'folder'
        elif isinstance( library_item, trans.app.model.LibraryDataset ):
            library_item_ids[ 'library_dataset_id' ] = library_item.id
            available_template_assocs = library_item.library_dataset_info_template_associations
            library_item_desc = 'library dataset'
        elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
            library_item_ids[ 'ldda_id' ] = library_item.id
            available_template_assocs = library_item.library_dataset_dataset_info_template_associations
            library_item_desc = 'library dataset <-> dataset association'
    %>
    <div class="toolForm">
        <div class="toolFormTitle">Available templates that provide information about ${library_item_desc} ${library_item.name}</div>
        <div class="toolFormBody">
            %for available_template_assoc in available_template_assocs:
                <div class="form-row">
                    <a href="${h.url_for( controller='admin', action='library_item_info_template', id=available_template_assoc.library_item_info_template.id )}">${available_template_assoc.library_item_info_template.name}</a>: ${available_template_assoc.library_item_info_template.description}
                    <div style="clear: both"></div>
                </div>
            %endfor
            <div class="form-row">
                <form name="library_item_template" action="${h.url_for( controller='admin', action='library_item_info_template', **library_item_ids )}" method="post">
                    ##<a class="action-button" href="${h.url_for( controller='admin', action='library_item_info_template', new_element_count=5, **library_item_ids )}"><span>Create a new template</span></a></li>
                    Create a new template with <input type="text" size="3" name="new_element_count" value="5"/> elements for ${library_item_desc} ${library_item.name}
                    <input type="submit" class="primary-button" name="library_item_template_button" id="library_item_template_button" value="Go"/>
                </form>
            </div>
        </div>
    </div>
    <p/>
</%def>
