<% from time import strftime %>

<%def name="render_dataset( library_dataset, selected, library )">
    <%
        ## The received data must always be a LibraryDataset object, but the object id passed to methods from the drop down menu
        ## should be the underlying ldda id to prevent id collision ( which could happen when displaying children, which are always
        ## lddas ).  We also need to make sure we're displaying the latest version of this library_dataset, so we display the attributes
        ## from the ldda.
        ldda = library_dataset.library_dataset_dataset_association
        if ldda.user:
            uploaded_by = ldda.user.email
        else:
            uploaded_by = 'anonymous'
        if ldda == ldda.library_dataset.library_dataset_dataset_association:
            current_version = True
        else:
            current_version = False
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
                        <a href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, id=ldda.id, info=True )}"><b>${ldda.name[:60]}</b></a>
                        <a id="dataset-${ldda.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        <div popupmenu="dataset-${ldda.id}-popup">
                            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=ldda.library_dataset ):
                                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, id=ldda.id, edit_info=True )}">Edit this dataset's information</a>
                            %else:
                                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, id=ldda.id, information=True )}">View this dataset's information</a>
                            %endif
                            ## We're disabling the ability to add templates at the LDDA and LibraryDataset level, but will leave this here for possible future use
                            ##%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=ldda.library_dataset ):
                            ##    <a class="action-button" href="${h.url_for( controller='library', action='info_template', library_id=library.id, library_dataset_id=library_dataset.id, new_template=True )}">Add an information template to this dataset</a>
                            ##%endif
                            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset=ldda.dataset ) and trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=ldda.library_dataset ):
                                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, id=ldda.id, permissions=True )}">Edit this dataset's permissions</a>
                            %if current_version and trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=ldda.library_dataset ):
                                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, replace_id=library_dataset.id )}">Upload a new version of this dataset</a>
                            %endif
                            %endif
                            %if ldda.has_data:
                                <a class="action-button" href="${h.url_for( controller='library', action='datasets', library_id=library.id, ldda_ids=str( ldda.id ), do_action='add' )}">Import this dataset into your current history</a>
                                <a class="action-button" href="${h.url_for( controller='library', action='download_dataset_from_folder', id=ldda.id, library_id=library.id )}">Download this dataset</a>
                            %endif
                        </div>
                    </td>
                    <td width="500">${ldda.message}</td>
                    <td width="150">${uploaded_by}</td>
                    <td width="60">${ldda.create_time.strftime( "%Y-%m-%d" )}</td>
                </tr>
            </table>
        </div>
    </div>
</%def>

<%def name="render_library_item_info_for_edit( library_item, library_id )">
    <%
        library_item_type = 'unknown type'
        library_item_desc = ''
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
        elif isinstance( library_item, trans.app.model.LibraryItemInfoElement ):
            library_item_type = 'library_item_info'
            library_item_desc = 'information'
            library_item_info_associations = None
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
                                    <textarea name="info_element_${element.id}" rows="3" cols="35">${element.contents}</textarea>
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

<%def name="render_library_item_info( library_item, library_id )">
    <%
        library_item_type = 'unknown type'
        library_item_desc = ''
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
        elif isinstance( library_item, trans.app.model.LibraryItemInfoElement ):
            library_item_type = 'library_item_info'
            library_item_desc = 'information'
            library_item_info_associations = None
    %>
    %if library_item_info_associations:
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Other information about ${library_item_desc} ${library_item.name}</div>
            <div class="toolFormBody">
                %for library_item_info_association in library_item_info_associations:
                    %for template_element in library_item_info_association.library_item_info.library_item_info_template.elements:
                        <% element = library_item_info_association.library_item_info.get_element_by_template_element( template_element ) %>
                        <div class="form-row">
                            <label>${template_element.name}:</label>
                            <div style="float: left; width: 250px; margin-right: 10px;">
                                ${element.contents}
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    %endfor
                    <div style="clear: both"></div>
                %endfor
            </div>
        </div>
    %endif
</%def>

<%def name="render_available_templates( library_item, library_id, restrict=False, upload=False )">
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
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Other information about ${library_item_desc} ${library_item.name}</div>
            <div class="toolFormBody">
                %for available_template in available_templates:
                    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=available_template ):
                        %if upload in [ False, 'False' ]:
                            ## Only render a form if we're not within the upload form
                            <form name="add_template_info" action="${h.url_for( controller='library', action='library_item_info', library_id=library_id, new_info=True )}" method="post">
                        %endif
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
                        %if upload in [ False, 'False' ]:
                            <div class="form-row">
                                <input type="submit" name="create_new_info_button" value="Save"/>
                            </div>
                            </form>
                        %endif
                    %endif
                %endfor
            </div>
        </div>
    %endif
</%def>
