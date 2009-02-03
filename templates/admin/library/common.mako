## Render the dataset `data`
<%def name="render_dataset( data, selected, deleted )">
    <%
    ## The data id should be the underlying ldda id, to prevent id collision (could happen when displaying children, 
    ## which are always lddas); and to function more seemlessly with existing code
    data_id = data.id
    if isinstance( data, trans.app.model.LibraryDataset ):
        data_id = data.library_dataset_dataset_association.id
    %>
    <div class="historyItemWrapper historyItem historyItem-${data.state}" id="libraryItem-${data_id}">

        ## Header row for library items (name, state, action buttons)
    	<div style="overflow: hidden;" class="historyItemTitleBar">		
            <table cellspacing="0" cellpadding="0" border="0" width="100%">
                <tr>
                    <td width="*">
                        %if selected:
                            <input type="checkbox" name="dataset_ids" value="${data_id}" checked/>
                        %else:
                            <input type="checkbox" name="dataset_ids" value="${data_id}"/>
                        %endif
                        <span class="historyItemTitle"><b>${data.display_name()}</b></span>
                        %if not deleted:
                            <a id="dataset-${data_id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                            <div popupmenu="dataset-${data_id}-popup">
                                <a class="action-button" href="${h.url_for( controller='admin', action='dataset', id=data_id )}">Edit this dataset's attributes and permissions</a>
                                %if data.has_data:
                                    <a class="action-button" href="${h.url_for( controller='admin', action='download_dataset_from_folder', id=data_id )}">Download this dataset</a>
                                %endif
                                <a class="action-button" confirm="Click OK to remove dataset '${data.name}'?" href="${h.url_for( controller='admin', action='dataset', delete=True, id=data_id )}">Remove this dataset from the library</a>
                            </div>
                        %endif
                    </td>
                    <td width="100">${data.ext}</td>
                    <td width="50"><span class="${data.dbkey}">${data.dbkey}</span></td>
                    <td width="200">${data.info}</td>
                </tr>
            </table>
        </div>
        
        ## Body for library items, extra info and actions, data "peek"
        <div id="info${data_id}" class="historyItemBody">
            <div>${data.blurb}</div>
            <div> 
                %if data.has_data:
                    %for display_app in data.datatype.get_display_types():
                        <% display_links = data.datatype.get_display_links( data, display_app, app, request.base ) %>
                        %if len( display_links ) > 0:
                            ${data.datatype.get_display_label(display_app)}
                            %for display_name, display_link in display_links:
                                <a target="_blank" href="${display_link}">${display_name}</a> 
                            %endfor
                        %endif
                    %endfor
                %endif
            </div>
            %if data.peek != "no peek":
                <div><pre id="peek${data_id}" class="peek">${data.display_peek()}</pre></div>
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
    <div class="toolForm">
        <div class="toolFormTitle">Available Templates</div>
        <div class="toolFormBody">
            %for available_template_assoc in available_template_assocs:
                <div class="form-row">
                    <a href="${h.url_for( controller='admin', action='library_item_info_template', id=available_template_assoc.library_item_info_template.id )}">${available_template_assoc.library_item_info_template.name}</a>: ${available_template_assoc.library_item_info_template.description}
                    <div style="clear: both"></div>
                </div>
            %endfor
            <div class="form-row">
                Click <a href="${h.url_for( controller='admin', action='library_item_info_template', new_element_count=5, **library_item_ids )}">here</a> to create a new template for this library item.
                </div>
                <div style="clear: both"></div>
            </div>
        </div>
    </div>
    <p/>
</%def>
