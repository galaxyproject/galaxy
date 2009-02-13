## Render the dataset `data`
<%def name="render_dataset( data, selected )">
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
                        <a id="dataset-${ldda.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        <div popupmenu="dataset-${ldda.id}-popup">
                            <%
                                if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=ldda ) or \
                                    trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=ldda ) or \
                                    trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset=ldda.dataset ):
                                    menu_label = "Edit this dataset's information"
                                else:
                                    menu_label = "View this dataset's information"
                            %>
                            <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', id=ldda.id )}">${menu_label}</a>
                            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=data ):
                                <%
                                    library_item_ids = {}
                                    library_item_ids[ 'library_dataset' ] = data.id
                                %>
                                <a class="action-button" href="${h.url_for( controller='library', action='library_item_info_template', library_dataset_id=data.id, new_element_count=5, **library_item_ids )}">Create a new information template for this dataset</a>
                            %endif
                            %if data.has_data:
                                <a class="action-button" href="${h.url_for( controller='library', action='download_dataset_from_folder', id=ldda.id )}">Download this dataset</a>
                            %endif
                        </div>
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
                        ${render_dataset( child, selected )}
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
            ##%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library_item ):
            ##    <div class="form-row">
            ##        Add <a href="${h.url_for( controller='library', action='library_item_info', do_action='new_info', library_item_id=library_item.id, library_item_type=library_item_type )}">new</a> info
            ##    </div>
            ##%endif
        </div>
    </div>
</%def>

<%def name="render_available_templates( library_item )">
    <%
        library_item_type = None
        if isinstance( library_item, trans.app.model.Library ):
            library_item_type = 'library'
            library_item_desc = 'library'
        elif isinstance( library_item, trans.app.model.LibraryFolder ):
            library_item_type = 'folder'
            library_item_desc = 'folder'
        elif isinstance( library_item, trans.app.model.LibraryDataset ):
            library_item_type = 'library_dataset'
            library_item_desc = 'library dataset'
        elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
            library_item_type = 'library_dataset_dataset_association'
            library_item_desc = 'library dataset <-> dataset association'
    %>
    <div class="toolForm">
        <div class="toolFormTitle">Available templates that provide information about this ${library_item_desc}</div>
        <div class="toolFormBody">
            ## TODO: add the following new feature
            ##%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library_item ):
            ##    <div class="form-row">
            ##        <a class="action-button" href="${h.url_for( controller='library', action='library_item_info_template', new_element_count=1, **library_item_ids )}"><span>Create a new template</span></a></li>
            ##    </div>
            ##%endif
            %for available_template in library_item.get_library_item_info_templates( [] ):
                ##if we don't provide an empty list, strange things happen on reloads.... (why? - some sort of mako caching?)
                %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library_item ):
                    <form name="add_template_info" action="${h.url_for( controller='library', action='library_item_info', do_action='new_info' )}" method="post">
                        <input type="hidden" name="library_item_id" value="${library_item.id}"/>
                        <input type="hidden" name="library_item_type" value="${library_item_type}"/>
                        <input type="hidden" name="library_item_info_template_id" value="${available_template.id}"/>
                        <div class="toolForm">
                            <div class="toolFormTitle">${available_template.name}: ${available_template.description}</div>
                            <div class="toolFormBody">
                                <b>Add more information about this ${library_item_desc} using this template</b>
                                <p/>
                                %for info_elem in available_template.elements:
                                    <div class="form-row">
                                        <b>${info_elem.name}</b>
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
                %else:
                    <div class="toolForm">
                        <div class="toolFormTitle">${available_template.name}: ${available_template.description}</div>
                        <div class="toolFormBody">
                            %for info_elem in available_template.elements:
                                <div class="form-row">
                                    <label>${info_elem.name}</label>
                                    <div class="toolParamHelp" style="clear: both;">
                                        ${info_elem.description}
                                    </div>
                                    <div style="clear: both"></div>
                                </div>
                            %endfor
                        </div>
                    </div>
                %endif
            %endfor
            <p/>
        </div>
    </div>
</%def>
