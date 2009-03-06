<%def name="render_dataset( library_dataset, selected, library )">
    <%
        ## The received data must always be a LibraryDataset object, but the object id passed to methods from the drop down menu
        ## should be the underlying ldda id to prevent id collision ( which could happen when displaying children, which are always
        ## lddas ).  We also need to make sure we're displaying the latest version of this library_dataset, so we display the attributes
        ## from the ldda.
        ldda = library_dataset.library_dataset_dataset_association
    %>
    <div class="historyItemWrapper historyItem historyItem-${ldda.state}" id="libraryItem-${ldda.id}">
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
                            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=ldda.library_dataset ):
                                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, id=ldda.id, information=True )}">Edit this dataset's information</a>
                            %else:
                                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, id=ldda.id, information=True )}">View this dataset's information</a>
                            %endif
                            ## We're disabling the ability to add templates at the LDDA and LibraryDataset level, but will leave this here for possible future use
                            ##%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=ldda.library_dataset ):
                            ##    <a class="action-button" href="${h.url_for( controller='library', action='info_template', library_id=library.id, library_dataset_id=library_dataset.id, new_template=True )}">Add an information template to this dataset</a>
                            ##%endif
                            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset=ldda.dataset ) and trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=ldda.library_dataset ):
                                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, id=ldda.id, permissions=True )}">Edit this dataset's permissions</a>
                            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=ldda.library_dataset ):
                                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset', id=library_dataset.id, library_id=library.id, versions=True )}">Manage this dataset's versions</a>
                            %endif
                            %endif
                            %if ldda.has_data:
                                <a class="action-button" href="${h.url_for( controller='library', action='datasets', library_id=library.id, ldda_ids=str( ldda.id ), do_action='add' )}">Import this dataset into your current history</a>
                                <a class="action-button" href="${h.url_for( controller='library', action='download_dataset_from_folder', id=ldda.id, library_id=library.id )}">Download this dataset</a>
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
                %if ldda.has_data:
                    %for display_app in ldda.datatype.get_display_types():
                        <% display_links = ldda.datatype.get_display_links( ldda, display_app, app, request.base ) %>
                        %if len( display_links ) > 0:
                            ${ldda.datatype.get_display_label( display_app )}
                            %for ldda.name, display_link in display_links:
                                <a target="_blank" href="${display_link}">${ldda.name}</a> 
                            %endfor
                        %endif
                    %endfor
                %endif
            </div>
            %if ldda.peek != "no peek":
                <div><pre id="peek${ldda.id}" class="peek">${ldda.display_peek()}</pre></div>
            %endif
            ## Recurse for child datasets
            %if len( ldda.visible_children ) > 0:
                <div>
                    There are ${len( ldda.visible_children )} secondary datasets.
                    %for idx, child in enumerate( ldda.visible_children ):
                        ${render_dataset( child, selected, library )}
                    %endfor
                </div>
            %endif
        </div>
    </div>
</%def>

<%def name="render_existing_library_item_info( library_item, library_id )">
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
            library_item_desc = 'dataset'
            library_item_info_associations = library_item.library_dataset_info_associations
        elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
            library_item_type = 'library_dataset_dataset_association'
            library_item_desc = 'library dataset'
            library_item_info_associations = library_item.library_dataset_dataset_info_associations
    %>
    %if library_item_info_associations:
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Other information about ${library_item_desc} ${library_item.name}</div>
            <div class="toolFormBody">
                <form name="edit_info" action="${h.url_for( controller='library', action='library_item_info', library_id=library_id, edit_info=True )}" method="post">
                    <input type="hidden" name="library_item_id" value="${library_item.id}"/>
                    <input type="hidden" name="library_item_type" value="${library_item_type}"/>
                    <% render_submit_button = False %>
                    %for library_item_info_association in library_item_info_associations:
                        %for template_element in library_item_info_association.library_item_info.library_item_info_template.elements:
                            <% element = library_item_info_association.library_item_info.get_element_by_template_element( template_element ) %>
                            <input type="hidden" name="id" value="${element.id}"/>
                            <%
                                can_add = trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=element.library_item_info )
                                can_modify = trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=element.library_item_info )
                                can_manage = trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=element.library_item_info )
                            %>
                            <div class="form-row">
                                %if can_manage:
                                    <label>
                                        ${template_element.name}:
                                        <a id="element-${element.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                                        <div popupmenu="element-${element.id}-popup">
                                            <a class="action-button" href="${h.url_for( controller='admin', action='library_item_info', library_id=library_id, id=element.id, library_item_type='library_item_info_elememt', permissions=True )}">Edit this information's permissions</a>
                                        </div>
                                    </label>
                                %else:
                                    <label>${template_element.name}:</label>
                                %endif
                                %if can_modify:
                                    <input type="text" name="info_element_${element.id}" value="${element.contents}" size="40"/>
                                    <% render_submit_button = True %>
                                %else:
                                    ${element.contents}
                                %endif
                                <div style="clear: both"></div>
                            </div>
                        %endfor
                        <div style="clear: both"></div>
                    %endfor
                    %if render_submit_button:
                        <div class="form-row">
                            <input type="submit" name="edit_info_button" value="Save"/>
                        </div>
                    %endif
                </form>
            </div>
        </div>
    %endif
</%def>

<%def name="render_available_templates( library_item, library_id, restrict=False )">
    <%
        available_templates = library_item.get_library_item_info_templates( template_list=[], restrict=restrict )
        if available_templates:
            library_item_ids = {}
            if isinstance( library_item, trans.app.model.Library ):
                library_item_type = 'library'
                library_item_desc = 'library'
            elif isinstance( library_item, trans.app.model.LibraryFolder ):
                library_item_ids[ 'folder_id' ] = library_item.id
                library_item_type = 'folder'
                library_item_desc = 'folder'
            elif isinstance( library_item, trans.app.model.LibraryDataset ):
                library_item_ids[ 'library_dataset_id' ] = library_item.id
                library_item_type = 'library_dataset'
                library_item_desc = 'dataset'
            elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
                library_item_ids[ 'ldda_id' ] = library_item.id
                library_item_type = 'library_dataset_dataset_association'
                library_item_desc = 'library dataset'
            # Always pass a library_id
            library_item_ids[ 'library_id' ] = library_id
    %>
    %if available_templates:
        ## There should only be 1 template here
        %for available_template in available_templates:
            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=available_template ):
                <p/>
                <div class="toolForm">
                    <div class="toolFormTitle">Other information about ${library_item_desc} ${library_item.name}</div>
                    <div class="toolFormBody">
                        <form name="add_template_info" action="${h.url_for( controller='library', action='library_item_info', library_id=library_id, new_info=True )}" method="post">
                            <input type="hidden" name="library_item_id" value="${library_item.id}"/>
                            <input type="hidden" name="library_item_type" value="${library_item_type}"/>
                            <input type="hidden" name="library_item_info_template_id" value="${available_template.id}"/>
                            <p/>
                            %for info_elem in available_template.elements:
                                <div class="form-row">
                                    <label>${info_elem.name}</label>
                                    <input type="text" name="info_element_${available_template.id}_${info_elem.id}" value="" size="40"/>
                                    <div class="toolParamHelp" style="clear: both;">
                                        ${info_elem.description}
                                    </div>
                                    <div style="clear: both"></div>
                                </div>
                            %endfor
                            <div class="form-row">
                                <input type="submit" name="create_new_info_button" value="Save"/>
                            </div>
                        </form>
                    </div>
                </div>
            %endif
        %endfor
    %endif
</%def>
