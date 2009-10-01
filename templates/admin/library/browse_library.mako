<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/library_item_info.mako" import="render_library_item_info" />
<%
    from time import strftime
    from galaxy import util
    from galaxy.web.controllers.library_common import active_folders_and_lddas, activatable_folders_and_lddas
%>

<%def name="stylesheets()">
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
    <link href="${h.url_for('/static/style/library.css')}" rel="stylesheet" type="text/css" />
</%def>

<% tracked_datasets = {} %>

<script type="text/javascript">
    $( document ).ready( function () {
        // Hide all the folder contents
        $("ul").filter("ul#subFolder").hide();
        // Handle the hide/show triangles
        $("li.libraryOrFolderRow").wrap( "<a href='#' class='expandLink'></a>" ).click( function() {
            var contents = $(this).parent().next("ul");
            if ( this.id == "libraryRow" ) {
                var icon_open = "${h.url_for( '/static/images/silk/book_open.png' )}";
                var icon_closed = "${h.url_for( '/static/images/silk/book.png' )}";
            } else {
                var icon_open = "${h.url_for( '/static/images/silk/folder_page.png' )}";
                var icon_closed = "${h.url_for( '/static/images/silk/folder.png' )}";
            }
            if ( contents.is(":visible") ) {
                contents.slideUp("fast");
                $(this).children().find("img.expanderIcon").each( function() { this.src = "${h.url_for( '/static/images/silk/resultset_next.png' )}"; });
                $(this).children().find("img.rowIcon").each( function() { this.src = icon_closed; });
            } else {
                contents.slideDown("fast");
                $(this).children().find("img.expanderIcon").each( function() { this.src = "${h.url_for( '/static/images/silk/resultset_bottom.png' )}"; });
                $(this).children().find("img.rowIcon").each( function() { this.src = icon_open; });
            }
        });
    });
    function checkForm() {
        if ( $("select#action_on_datasets_select option:selected").text() == "delete" ) {
            if ( confirm( "Click OK to delete these datasets?" ) ) {
                return true;
            } else {
                return false;
            }
        }
    }
    // Looks for changes in dataset state using an async request. Keeps
    // calling itself (via setTimeout) until all datasets are in a terminal
    // state.
    var updater = function ( tracked_datasets ) {
        // Check if there are any items left to track
        var empty = true;
        for ( i in tracked_datasets ) {
            empty = false;
            break;
        }
        if ( ! empty ) {
            setTimeout( function() { updater_callback( tracked_datasets ) }, 3000 );
        }
    };
    var updater_callback = function ( tracked_datasets ) {
        // Build request data
        var ids = []
        var states = []
        $.each( tracked_datasets, function ( id, state ) {
            ids.push( id );
            states.push( state );
        });
        // Make ajax call
        $.ajax( {
            type: "POST",
            url: "${h.url_for( controller='library_common', action='library_item_updates' )}",
            dataType: "json",
            data: { ids: ids.join( "," ), states: states.join( "," ) },
            success : function ( data ) {
                $.each( data, function( id, val ) {
                    // Replace HTML
                    var cell = $("#libraryItem-" + id).find("#libraryItemInfo");
                    cell.html( val.html );
                    // If new state was terminal, stop tracking
                    if (( val.state == "ok") || ( val.state == "error") || ( val.state == "empty") || ( val.state == "deleted" ) || ( val.state == "discarded" )) {
                        delete tracked_datasets[ parseInt(id) ];
                    } else {
                        tracked_datasets[ parseInt(id) ] = val.state;
                    }
                });
                updater( tracked_datasets ); 
            },
            error: function() {
                // Just retry, like the old method, should try to be smarter
                updater( tracked_datasets );
            }
        });
    };
</script>

<%def name="render_dataset( ldda, library_dataset, selected, library, folder, deleted, show_deleted )">
    <%
        ## The received data must always be a LibraryDatasetDatasetAssociation object.  The object id passed to methods
        ## from the drop down menu should be the ldda id to prevent id collision ( which could happen when displaying
        ## children, which are always lddas ).  We also need to make sure we're displaying the latest version of this
        ## library_dataset, so we display the attributes from the ldda.
        if ldda.user:
            uploaded_by = ldda.user.email
        else:
            uploaded_by = 'anonymous'
        if ldda == library_dataset.library_dataset_dataset_association:
            current_version = True
        else:
            current_version = False
        if current_version and ldda.state not in ( 'ok', 'error', 'empty', 'deleted', 'discarded' ):
            tracked_datasets[ldda.id] = ldda.state
    %>
    %if current_version:
        <div class="libraryItemWrapper libraryItem" id="libraryItem-${ldda.id}">
            ## Header row for library items (name, state, action buttons)
            <div class="libraryItemTitleBar"> 
                <table cellspacing="0" cellpadding="0" border="0" width="100%">
                    <tr>
                        <td width="*">
                            %if selected:
                                <input type="checkbox" name="ldda_ids" value="${ldda.id}" checked/>
                            %else:
                                <input type="checkbox" name="ldda_ids" value="${ldda.id}"/>
                            %endif
                            <span class="libraryItemDeleted-${ldda.deleted}">
                                <a href="${h.url_for( controller='library_admin', action='ldda_display_info', library_id=library.id, folder_id=folder.id, obj_id=ldda.id, deleted=deleted, show_deleted=show_deleted )}"><b>${ldda.name[:50]}</b></a>
                            </span>
                            <a id="dataset-${ldda.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                            %if not library.deleted and not folder.deleted and not library_dataset.deleted:
                                <div popupmenu="dataset-${ldda.id}-popup">
                                    <a class="action-button" href="${h.url_for( controller='library_admin', action='ldda_edit_info', library_id=library.id, folder_id=folder.id, obj_id=ldda.id )}">Edit this dataset's information</a>
                                    <a class="action-button" href="${h.url_for( controller='library_admin', action='ldda_manage_permissions', library_id=library.id, folder_id=folder.id, obj_id=ldda.id, permissions=True )}">Edit this dataset's permissions</a>
                                    <a class="action-button" href="${h.url_for( controller='library_admin', action='upload_library_dataset', library_id=library.id, folder_id=folder.id, replace_id=library_dataset.id )}">Upload a new version of this dataset</a>
                                    %if ldda.has_data:
                                        <a class="action-button" href="${h.url_for( controller='library_admin', action='download_dataset_from_folder', obj_id=ldda.id, library_id=library.id )}">Download this dataset</a>
                                    %endif
                                    <a class="action-button" confirm="Click OK to delete dataset '${ldda.name}'." href="${h.url_for( controller='library_admin', action='delete_library_item', library_id=library.id, library_item_id=library_dataset.id, library_item_type='library_dataset' )}">Delete this dataset</a>
                                </div>
                            %elif not library.deleted and not folder.deleted and library_dataset.deleted:
                                <div popupmenu="dataset-${ldda.id}-popup">
                                    <a class="action-button" href="${h.url_for( controller='library_admin', action='undelete_library_item', library_id=library.id, library_item_id=library_dataset.id, library_item_type='library_dataset' )}">Undelete this dataset</a>
                                </div>
                            %endif
                        </td>
                        <td width="300" id="libraryItemInfo">${render_library_item_info( ldda )}</td>
                        <td width="150">${uploaded_by}</td>
                        <td width="60">${ldda.create_time.strftime( "%Y-%m-%d" )}</td>
                    </tr>
                </table>
            </div>
        </div>
    %endif
</%def>

<%def name="render_folder( folder, folder_pad, deleted, show_deleted, created_ldda_ids, library_id, root_folder=False )">
    <%
        if root_folder:
            pad = folder_pad
            expander = "/static/images/silk/resultset_bottom.png"
            folder_img = "/static/images/silk/folder_page.png"
        else:
            pad = folder_pad + 20
            expander = "/static/images/silk/resultset_next.png"
            folder_img = "/static/images/silk/folder.png"
        if created_ldda_ids:
            created_ldda_ids = [ int( ldda_id ) for ldda_id in util.listify( created_ldda_ids ) ]
    %>
    %if not root_folder:
        <li class="folderRow libraryOrFolderRow" style="padding-left: ${pad}px;">
            %if not folder.deleted or show_deleted:
                <div class="rowTitle libraryItemDeleted-${deleted}">
                    <img src="${h.url_for( expander )}" class="expanderIcon"/><img src="${h.url_for( folder_img )}" class="rowIcon"/>
                    ${folder.name}
                    %if folder.description:
                        <i>- ${folder.description}</i>
                    %endif
                    <a id="folder-${folder.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </div>
            %endif
            %if not folder.deleted:
                <div popupmenu="folder-${folder.id}-popup">
                    <a class="action-button" href="${h.url_for( controller='library_admin', action='upload_library_dataset', library_id=library_id, folder_id=folder.id )}">Add datasets to this folder</a>
                    <a class="action-button" href="${h.url_for( controller='library_admin', action='folder', new=True, obj_id=folder.id, library_id=library_id )}">Create a new sub-folder in this folder</a>
                    <a class="action-button" href="${h.url_for( controller='library_admin', action='folder', information=True, obj_id=folder.id, library_id=library_id )}">Edit this folder's information</a>
                    ## Editing templates disabled until we determine optimal approach to re-linking library item to new version of form definition
                    ##%if folder.info_association:
                    ##    <% form_id = folder.info_association[0].template.id %>
                    ##    <a class="action-button" href="${h.url_for( controller='forms', action='edit', form_id=form_id, show_form=True )}">Edit this folder's information template</a>
                    ##%else:
                    %if not folder.info_association:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='info_template', cntrller='library_admin', library_id=library.id, response_action='folder', folder_id=folder.id )}">Add an information template to this folder</a>
                    %endif
                    <a class="action-button" href="${h.url_for( controller='library_admin', action='folder', permissions=True, obj_id=folder.id, library_id=library_id )}">Edit this folder's permissions</a>
                    <a class="action-button" confirm="Click OK to delete the folder '${folder.name}.'" href="${h.url_for( controller='library_admin', action='delete_library_item', library_id=library_id, library_item_id=folder.id, library_item_type='folder' )}">Delete this folder and its contents</a>
                </div>
            %elif not deleted and folder.deleted and not folder.purged:
                <div popupmenu="folder-${folder.id}-popup">
                    <a class="action-button" href="${h.url_for( controller='library_admin', action='undelete_library_item', library_id=library_id, library_item_id=folder.id, library_item_type='folder' )}">Undelete this folder</a>
                </div>
            %endif
        </li>
    %endif
    %if pad > 0:
        <ul id="subFolder">
    %else:
        <ul>
    %endif
        %if show_deleted:
            <%
                sub_folders, lddas = activatable_folders_and_lddas( trans, folder )
            %>
        %else:
            <%
                sub_folders, lddas = active_folders_and_lddas( trans, folder )
            %>
        %endif
        %for sub_folder in sub_folders:
            ${render_folder( sub_folder, pad, deleted, show_deleted, created_ldda_ids, library_id )}
        %endfor 
        %for ldda in lddas:
            <%
                library_dataset = ldda.library_dataset
                selected = created_ldda_ids and ldda.id in created_ldda_ids
            %>
            <li class="datasetRow" style="padding-left: ${pad + 18}px;">
                ${render_dataset( ldda, library_dataset, selected, library, folder, deleted, show_deleted )}
            </li>
        %endfor
    </ul>
</%def>

<h2>
    %if deleted:
        Deleted 
    %endif
    Data Library &ldquo;${library.name}&rdquo;
</h2>

<ul class="manage-table-actions">
    %if not deleted:
        <li>
            <a class="action-button" href="${h.url_for( controller='library_admin', action='upload_library_dataset', library_id=library.id, folder_id=library.root_folder.id )}"><span>Add datasets to this data library</span></a>
        </li>
        <li>
            <a class="action-button" href="${h.url_for( controller='library_admin', action='folder', new=True, obj_id=library.root_folder.id, library_id=library.id )}">Add a folder to this data library</a>
        </li>
    %endif
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<form name="update_multiple_datasets" action="${h.url_for( controller='library_admin', action='datasets', library_id=library.id )}" onSubmit="javascript:return checkForm();" method="post">
    <ul>
        <li class="libraryRow libraryOrFolderRow" id="libraryRow">
            <div class="rowTitle">
                <table cellspacing="0" cellpadding="0" border="0" width="100%" class="libraryTitle">
                    <th width="*">
                        <img src="${h.url_for( '/static/images/silk/resultset_bottom.png' )}" class="expanderIcon"/><img src="${h.url_for( '/static/images/silk/book_open.png' )}" class="rowIcon"/>
                        <span class="libraryItemDeleted-${deleted}">
                            ${library.name}
                            %if library.description:
                                <i>- ${library.description}</i>
                            %endif
                        </span>
                        <a id="library-${library.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        <div popupmenu="library-${library.id}-popup">
                        %if not deleted:
                            <a class="action-button" href="${h.url_for( controller='library_admin', action='library', obj_id=library.id, information=True )}">Edit this data library's information</a>
                            ## Editing templates disabled until we determine optimal approach to re-linking library item to new version of form definition
                            ##%if library.info_association:
                            ##    <% form_id = library.info_association[0].template.id %>
                            ##    <a class="action-button" href="${h.url_for( controller='forms', action='edit', form_id=form_id, show_form=True )}">Edit this data library's information template</a>
                            ##%else:
                            %if not library.info_association:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='info_template', cntrller='library_admin', library_id=library.id, response_action='browse_library' )}">Add an information template to this data library</a>
                            %endif
                            <a class="action-button" href="${h.url_for( controller='library_admin', action='library', obj_id=library.id, permissions=True )}">Edit this data library's permissions</a>
                            <a class="action-button" confirm="Click OK to delete the library named '${library.name}'." href="${h.url_for( controller='library_admin', action='delete_library_item', library_id=library.id, library_item_id=library.id, library_item_type='library' )}">Delete this data library and its contents</a>
                            %if show_deleted:
                            	<a class="action-button" href="${h.url_for( controller='library_admin', action='browse_library', obj_id=library.id, show_deleted=False )}">Hide deleted data library items</a>
                            %else:
                            	<a class="action-button" href="${h.url_for( controller='library_admin', action='browse_library', obj_id=library.id, show_deleted=True )}">Show deleted data library items</a>
                            %endif
                        %elif not library.purged:
                              <a class="action-button" href="${h.url_for( controller='library_admin', action='undelete_library_item', library_id=library.id, library_item_id=library.id, library_item_type='library' )}">Undelete this data library</a>
                        %endif
                        </div>
                    </th>
                    <th width="300">Information</th>
                    <th width="150">Uploaded By</th>
                    <th width="60">Date</th>
                </table>
            </div>
        </li>
        <ul>
            ${render_folder( library.root_folder, 0, deleted, show_deleted, created_ldda_ids, library.id, root_folder=True )}
        </ul>
        <br/>
    </ul>
    %if not deleted and not show_deleted:
        <p>
            <b>Perform action on selected datasets:</b>
            <select name="action" id="action_on_datasets_select">
                <option value="manage_permissions">Edit selected datasets' permissions</option>
                <option value="delete">Delete selected datasets</option>
            </select>
            <input type="submit" class="primary-button" name="action_on_datasets_button" id="action_on_datasets_button" value="Go"/>
        </p>
    %endif
</form>

%if tracked_datasets:
    <script type="text/javascript">
        // Updater
        updater({${ ",".join( [ '"%s" : "%s"' % ( k, v ) for k, v in tracked_datasets.iteritems() ] ) }});
    </script>
    <!-- running: do not change this comment, used by TwillTestCase.library_wait -->
%endif
