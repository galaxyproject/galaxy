<% from time import strftime %>

<%def name="render_dataset( library_dataset, selected, library, deleted, show_deleted )">
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
                        <span class="libraryItemDeleted-${library_dataset.deleted}">
                            <a href="${h.url_for( controller='admin', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, id=ldda.id, info=True, deleted=deleted, show_deleted=show_deleted )}"><b>${ldda.name[:50]}</b></a>
                        </span>
                        <a id="dataset-${ldda.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        %if not library.deleted and not library_dataset.folder.deleted and not library_dataset.deleted:
                            <%
                                library_item_ids = {}
                                library_item_ids[ 'ldda' ] = ldda.id
                            %>
                            <div popupmenu="dataset-${ldda.id}-popup">
                                <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, id=ldda.id, edit_info=True )}">Edit this dataset's information</a>
                                ## We're disabling the ability to add templates at the LDDA and LibraryDataset level, but will leave this here for possible future use
                                ##<a class="action-button" href="${h.url_for( controller='admin', action='info_template', library_id=library.id, library_dataset_id=library_dataset.id, new_template=True )}">Add an information template to this dataset</a>
                                <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, id=ldda.id, permissions=True )}">Edit this dataset's permissions</a>
                                %if current_version:
                                    <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', library_id=library.id, folder_id=library_dataset.folder.id, replace_id=library_dataset.id )}">Upload a new version of this dataset</a>
                                %endif
                                %if ldda.has_data:
                                    <a class="action-button" href="${h.url_for( controller='admin', action='download_dataset_from_folder', id=ldda.id, library_id=library.id )}">Download this dataset</a>
                                %endif
                                <a class="action-button" confirm="Click OK to delete dataset '${ldda.name}'." href="${h.url_for( controller='admin', action='delete_library_item', library_id=library.id, library_item_id=library_dataset.id, library_item_type='library_dataset' )}">Delete this dataset</a>
                            </div>
                        %elif not library.deleted and not library_dataset.folder.deleted and library_dataset.deleted:
                            <div popupmenu="dataset-${ldda.id}-popup">
                                <a class="action-button" href="${h.url_for( controller='admin', action='undelete_library_item', library_id=library.id, library_item_id=library_dataset.id, library_item_type='library_dataset' )}">Undelete this dataset</a>
                            </div>
                        %endif
                    </td>
                    <td width="300">${ldda.message}</td>
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
                %if editable:
                    <form name="edit_info" action="${h.url_for( controller='admin', action='edit_template_info', library_id=library_id, num_widgets=len( widgets ) )}" method="post">
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
