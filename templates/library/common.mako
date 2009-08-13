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
        <div class="historyItemTitleBar">     
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

<%def name="render_template_info( library_item, library_id, widgets, editable=True )">
    <%
        library_item_type = 'unknown type'
        library_item_desc = ''
        if isinstance( library_item, trans.app.model.Library ):
            library_item_type = 'library'
            library_item_desc = 'library'
        elif isinstance( library_item, trans.app.model.LibraryFolder ):
            library_item_type = 'folder'
            library_item_desc = 'folder'
        elif isinstance( library_item, trans.app.model.LibraryDataset ):
            library_item_type = 'library_dataset'
            library_item_desc = 'dataset'
        elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
            library_item_type = 'library_dataset_dataset_association'
            library_item_desc = 'library dataset'
    %>
    %if widgets:
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Other information about ${library_item_desc} ${library_item.name}</div>
            <div class="toolFormBody">
                %if editable and trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=library_item ):
                    <form name="edit_info" action="${h.url_for( controller='library', action='edit_template_info', library_id=library_id, num_widgets=len( widgets ) )}" method="post">
                        <input type="hidden" name="library_item_id" value="${library_item.id}"/>
                        <input type="hidden" name="library_item_type" value="${library_item_type}"/>
                        %for i, field in enumerate( widgets ):
                            <div class="form-row">
                                <label>${field[ 'label' ]}</label>
                                ${field[ 'widget' ].get_html()}
                                <div class="toolParamHelp" style="clear: both;">
                                    ${field[ 'helptext' ]}
                                </div>
                                <div style="clear: both"></div>
                            </div>
                        %endfor 
                        <div class="form-row">
                            <input type="submit" name="edit_info_button" value="Save"/>
                        </div>
                    </form>
                %else:
                    %for i, field in enumerate( widgets ):
                        %if field[ 'widget' ].value:
                            <div class="form-row">
                                <label>${field[ 'label' ]}</label>
                                ${field[ 'widget' ].value}
                                <div class="toolParamHelp" style="clear: both;">
                                    ${field[ 'helptext' ]}
                                </div>
                                <div style="clear: both"></div>
                            </div>
                        %endif
                    %endfor
                %endif
            </div>
        </div>
    %endif
</%def>
