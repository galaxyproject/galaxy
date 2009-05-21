<%inherit file="/base.mako"/>
<%namespace file="common.mako" import="render_dataset" />
<%namespace file="/message.mako" import="render_msg" />
<% from galaxy import util %>

<%def name="stylesheets()">
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
    <link href="${h.url_for('/static/style/library.css')}" rel="stylesheet" type="text/css" />
</%def>

<%
def name_sorted( l ):
    return sorted( l, lambda a, b: cmp( a.name.lower(), b.name.lower() ) )
%>

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
        // Hide all dataset bodies
        $("div.historyItemBody").hide();
        // Handle the dataset body hide/show link.
        $("div.historyItemWrapper").each( function() {
            var id = this.id;
            var li = $(this).parent();
            var body = $(this).children( "div.historyItemBody" );
            var peek = body.find( "pre.peek" )
            $(this).children( ".historyItemTitleBar" ).find( ".historyItemTitle" ).wrap( "<a href='#'></a>" ).click( function() {
                if ( body.is(":visible") ) {
                    if ( $.browser.mozilla ) { peek.css( "overflow", "hidden" ) }
                    body.slideUp( "fast" );
                    li.removeClass( "datasetHighlighted" );
                } 
                else {
                    body.slideDown( "fast", function() { 
                        if ( $.browser.mozilla ) { peek.css( "overflow", "auto" ); } 
                    });
                    li.addClass( "datasetHighlighted" );
                }
                return false;
            });
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
</script>

<%def name="render_folder( folder, folder_pad, deleted, show_deleted, created_ldda_ids, library_id )">
    <%
        root_folder = not folder.parent
        if root_folder:
            pad = folder_pad
        else:
            pad = folder_pad + 20
        if folder_pad == 0:
            expander = "/static/images/silk/resultset_bottom.png"
            folder_img = "/static/images/silk/folder_page.png"
            subfolder = False
        else:
            expander = "/static/images/silk/resultset_next.png"
            folder_img = "/static/images/silk/folder.png"
            subfolder = True
        created_ldda_id_list = util.listify( created_ldda_ids )
        if created_ldda_id_list:
           created_ldda_ids = [ int( ldda_id ) for ldda_id in created_ldda_id_list ]
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
                <%
                    library_item_ids = {}
                    library_item_ids[ 'folder' ] = folder.id
                %>
                <div popupmenu="folder-${folder.id}-popup">
                    <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', library_id=library_id, folder_id=folder.id )}">Add datasets to this folder</a>
                    <a class="action-button" href="${h.url_for( controller='admin', action='folder', new=True, id=folder.id, library_id=library_id )}">Create a new sub-folder in this folder</a>
                    <a class="action-button" href="${h.url_for( controller='admin', action='folder', information=True, id=folder.id, library_id=library_id )}">Edit this folder's information</a>
                    %if folder.library_folder_info_template_associations:
                        <% template = folder.get_library_item_info_templates( template_list=[], restrict=True )[0] %>
                        <a class="action-button" href="${h.url_for( controller='admin', action='info_template', library_id=library_id, id=template.id, edit_template=True )}">Edit this folder's information template</a>
                    %elif not folder.library_folder_info_associations:
                        ## Only allow adding a new template to the folder if a previously inherited template has not already been used
                        <a class="action-button" href="${h.url_for( controller='admin', action='info_template', library_id=library_id, folder_id=folder.id, new_template=True )}">Add an information template to this folder</a>
                    %endif
                    <a class="action-button" href="${h.url_for( controller='admin', action='folder', permissions=True, id=folder.id, library_id=library_id )}">Edit this folder's permissions</a>
                    <a class="action-button" confirm="Click OK to delete the folder '${folder.name}.'" href="${h.url_for( controller='admin', action='delete_library_item', library_id=library_id, library_item_id=folder.id, library_item_type='folder' )}">Delete this folder and its contents</a>
                </div>
            %elif not deleted and folder.deleted and not folder.purged:
                <div popupmenu="folder-${folder.id}-popup">
                    <a class="action-button" href="${h.url_for( controller='admin', action='undelete_library_item', library_id=library_id, library_item_id=folder.id, library_item_type='folder' )}">Undelete this folder</a>
                </div>
            %endif
        </li>
    %endif
    %if subfolder:
        <ul id="subFolder">
    %else:
        <ul>
    %endif
        %if show_deleted:
            <%
                parent_folders = folder.activatable_folders
                parent_datasets = folder.activatable_datasets
            %>
        %else:
            <%
                parent_folders = folder.active_folders
                parent_datasets = folder.active_datasets
            %>
        %endif
        %for folder in name_sorted( parent_folders ):
            ${render_folder( folder, pad, deleted, show_deleted, created_ldda_ids, library_id )}
        %endfor    
        %for library_dataset in name_sorted( parent_datasets ):
            <%
                selected = created_ldda_ids and library_dataset.library_dataset_dataset_association.id in created_ldda_ids
            %>
            <li class="datasetRow" style="padding-left: ${pad + 18}px;">${render_dataset( library_dataset, selected, library, deleted, show_deleted )}</li>
        %endfor
    </ul>
</%def>

<h2>
    %if deleted:
        Deleted 
    %endif
    Library '${library.name}'
</h2>

<ul class="manage-table-actions">
    %if not deleted:
        <li>
            <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', library_id=library.id, folder_id=library.root_folder.id )}"><span>Add datasets to this library</span></a>
        </li>
        <li>
            <a class="action-button" href="${h.url_for( controller='admin', action='folder', new=True, id=library.root_folder.id, library_id=library.id )}">Add a folder to this library</a>
        </li>
    %endif
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<form name="update_multiple_datasets" action="${h.url_for( controller='admin', action='datasets', library_id=library.id )}" onSubmit="javascript:return checkForm();" method="post">
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
                            <%
                                library_item_ids = {}
                                library_item_ids[ 'library' ] = library.id
                            %>
                            
                                <a class="action-button" href="${h.url_for( controller='admin', action='library', id=library.id, information=True )}">Edit this library's information</a>
                                %if library.library_info_template_associations:
                                    <% template = library.get_library_item_info_templates( template_list=[], restrict=False )[0] %>
                                    <a class="action-button" href="${h.url_for( controller='admin', action='info_template', library_id=library.id, id=template.id, edit_template=True )}">Edit this library's information template</a>
                                %else:
                                    <a class="action-button" href="${h.url_for( controller='admin', action='info_template', library_id=library.id, new_template=True )}">Add an information template to this library</a>
                                %endif
                                <a class="action-button" href="${h.url_for( controller='admin', action='library', id=library.id, permissions=True )}">Edit this library's permissions</a>
                                <a class="action-button" confirm="Click OK to delete the library named '${library.name}'." href="${h.url_for( controller='admin', action='delete_library_item', library_id=library.id, library_item_id=library.id, library_item_type='library' )}">Delete this library and its contents</a>
                                %if show_deleted:
                                	<a class="action-button" href="${h.url_for( controller='admin', action='browse_library', id=library.id, show_deleted=False )}">Hide deleted library items</a>
                                %else:
                                	<a class="action-button" href="${h.url_for( controller='admin', action='browse_library', id=library.id, show_deleted=True )}">Show deleted library items</a>
                                %endif
                        %elif not library.purged:
                              <a class="action-button" href="${h.url_for( controller='admin', action='undelete_library_item', library_id=library.id, library_item_id=library.id, library_item_type='library' )}">Undelete this library</a>
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
            ${render_folder( library.root_folder, 0, deleted, show_deleted, created_ldda_ids, library.id )}
        </ul>
        <br/>
    </ul>
    %if not deleted and not show_deleted:
        <p>
            <b>Perform action on selected datasets:</b>
            <select name="action" id="action_on_datasets_select">
                <option value="edit">Edit selected datasets' permissions</option>
                <option value="delete">Delete selected datasets</option>
            </select>
            <input type="submit" class="primary-button" name="action_on_datasets_button" id="action_on_datasets_button" value="Go"/>
        </p>
    %endif
</form>
