## Render the dataset `data`
<%def name="render_dataset( data )">
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
                        <input type="checkbox" name="import_ids" value="${data_id}"/>
                        <span class="historyItemTitle"><b>${data.display_name()}</b></span>
                        <a id="dataset-${data_id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        <div popupmenu="dataset-${data_id}-popup">
                            <a class="action-button" href="${h.url_for( controller='root', action='edit', lid=data_id )}">View or edit this dataset's attributes and permissions</a>
                            %if data.has_data:
                                <a class="action-button" href="${h.url_for( controller='library', action='download_dataset_from_folder', id=data_id )}">Download this dataset</a>
                            %endif
                        </div>
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
                        ${render_dataset( child )}
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
            library_item_info_associations = library_item.library_info_associations
        elif isinstance( library_item, trans.app.model.LibraryFolder ):
            library_item_type = 'folder'
            library_item_info_associations = library_item.library_folder_info_associations
        elif isinstance( library_item, trans.app.model.LibraryDataset ):
            library_item_type = 'library_dataset'
            library_item_info_associations = library_item.library_dataset_info_associations
        elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
            library_item_type = 'library_dataset_dataset_association'
            library_item_info_associations = library_item.library_dataset_dataset_info_associations
    %>
    <div class="toolForm">
        <div class="toolFormTitle">Available Library Item Info</div>
        <div class="toolFormBody">
            %for available_info_assoc in library_item_info_associations:
                <div class="form-row">
                    <a href="${h.url_for( controller='library',
                                          action='library_item_info',
                                          do_action='display',
                                          id=available_info_assoc.library_item_info.id )}">${available_info_assoc.library_item_info.library_item_info_template.name}</a>
                </div>
                <div style="clear: both"></div>
            %endfor
            %if trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_ADD, library_item ):
                <div class="form-row">
                    Add <a href="${h.url_for( controller='library', action='library_item_info', do_action='new_info', library_item_id=library_item.id, library_item_type=library_item_type )}">new</a> info
                </div>
            %endif
        </div>
    </div>
</%def>

<%def name="render_available_templates( library_item )">
    <%
        library_item_type = None
        if isinstance( library_item, trans.app.model.Library ):
            library_item_type = 'library'
        elif isinstance( library_item, trans.app.model.LibraryFolder ):
            library_item_type = 'folder'
        elif isinstance( library_item, trans.app.model.LibraryDataset ):
            library_item_type = 'library_dataset'
        elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
            library_item_type = 'library_dataset_dataset_association'
    %>
    <div class="toolForm">
        <div class="toolFormTitle">Available Info Templates to be filled in</div>
        <div class="toolFormBody">
            %for available_template in library_item.get_library_item_info_templates( [] ):
                ##if we don't provide an empty list, strange things happen on reloads.... (why? - some sort of mako caching?)
                <form name="edit_attributes" action="${h.url_for( controller='library', action='library_item_info', do_action='new_info' )}" method="post">
                    <input type="hidden" name="library_item_id" value="${library_item.id}"/>
                    <input type="hidden" name="library_item_type" value="${library_item_type}"/>
                    <input type="hidden" name="library_item_info_template_id" value="${available_template.id}"/>
                    <div class="toolForm">
                        <div class="toolFormTitle">${available_template.name}: ${available_template.description}</div>
                        <div class="toolFormBody">
                            %for info_elem in available_template.elements:
                                <div class="form-row">
                                    <label>${info_elem.name}</label>
                                    <div class="toolParamHelp" style="clear: both;">
                                        ${info_elem.description}
                                    </div>
                                    <div style="float: left; width: 250px; margin-right: 10px;">
                                        <input type="text" name="info_element_${available_template.id}_${info_elem.id}" value="" size="40"/>
                                    </div>
                                    <div style="clear: both"></div>
                                </div>
                            %endfor
                            <div class="form-row">
                                <input type="submit" name="create_new_info_button" value="Save"/>
                            </div>
                        </div>
                    </div>
                </form>
            %endfor
            <p/>
        </div>
    </div>
</%def>
