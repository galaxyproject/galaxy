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

<%def name="render_folder( parent, parent_pad, deleted, created_ldda_ids, library_id )">
    <%
        pad = parent_pad + 20
        if parent_pad == 0:
            expander = "/static/images/silk/resultset_bottom.png"
            folder = "/static/images/silk/folder_page.png"
            subfolder = False
        else:
            expander = "/static/images/silk/resultset_next.png"
            folder = "/static/images/silk/folder.png"
            subfolder = True
        root_folder = not parent.parent
        created_ldda_id_list = util.listify( created_ldda_ids )
        if created_ldda_id_list:
           created_ldda_ids = [ int( ldda_id ) for ldda_id in created_ldda_id_list ]
    %>
    %if not root_folder:
        <li class="folderRow libraryOrFolderRow" style="padding-left: ${pad}px;">
            <div class="rowTitle">
                <img src="${h.url_for( expander )}" class="expanderIcon"/><img src="${h.url_for( folder )}" class="rowIcon"/>
                ${parent.name}
                %if parent.description:
                    <i>- ${parent.description}</i>
                %endif
                <a id="folder-${parent.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            </div>
            %if not deleted:
                <%
                    library_item_ids = {}
                    library_item_ids[ 'folder' ] = parent.id
                %>
                <div popupmenu="folder-${parent.id}-popup">
                    <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', library_id=library_id, folder_id=parent.id )}">Add datasets to this folder</a>
                    <a class="action-button" href="${h.url_for( controller='admin', action='folder', new=True, id=parent.id, library_id=library_id )}">Create a new sub-folder in this folder</a>
                    <a class="action-button" href="${h.url_for( controller='admin', action='folder', information=True, id=parent.id, library_id=library_id )}">Edit this folder's information</a>
                    %if parent.library_folder_info_template_associations:
                        <% template = parent.get_library_item_info_templates( template_list=[], restrict=True )[0] %>
                        <a class="action-button" href="${h.url_for( controller='admin', action='info_template', library_id=library.id, id=template.id, edit_template=True )}">Edit this folder's information template</a>
                    %else:
                        <a class="action-button" href="${h.url_for( controller='admin', action='info_template', library_id=library.id, folder_id=parent.id, new_template=True )}">Add an information template to this folder</a>
                    %endif
                    <a class="action-button" href="${h.url_for( controller='admin', action='folder', permissions=True, id=parent.id, library_id=library_id )}">Edit this folder's permissions</a>
                    ## TODO: need to revamp the way folders and contained LibraryDatasets are deleted
                    ##%if subfolder:
                    ##    <a class="action-button" confirm="Click OK to delete the folder '${parent.name}'" href="${h.url_for( action='folder', delete=True, id=parent.id, library_id=library_id )}">Remove this folder and its contents from the library</a>
                    ##%endif
                </div>
            %endif
        </li>
    %endif
    %if subfolder:
        <ul id="subFolder">
    %else:
        <ul>
    %endif
        %if library.deleted:
            <%
                parent_folders = parent.folders
                parent_datasets = parent.datasets
            %>
        %else:
            <%
                parent_folders = parent.active_folders
                parent_datasets = parent.active_datasets
            %>
        %endif
        %for folder in name_sorted( parent_folders ):
            ${render_folder( folder, pad, library.deleted, created_ldda_ids, library.id )}
        %endfor    
        %for library_dataset in name_sorted( parent_datasets ):
            <%
                selected = created_ldda_ids and library_dataset.library_dataset_dataset_association.id in created_ldda_ids
            %>
            <li class="datasetRow" style="padding-left: ${pad + 18}px;">${render_dataset( library_dataset, selected, library )}</li>
        %endfor
    </ul>
</%def>

<h2>
    %if library.deleted:
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
                        ${library.name}
                        %if library.description:
                            <i>- ${library.description}</i>
                        %endif
                        <a id="library-${library.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        %if not library.deleted:
                            <%
                                library_item_ids = {}
                                library_item_ids[ 'library' ] = library.id
                            %>
                            <div popupmenu="library-${library.id}-popup">
                                <a class="action-button" href="${h.url_for( controller='admin', action='library', id=library.id, information=True )}">Edit this library's information</a>
                                %if library.library_info_template_associations:
                                    <% template = library.get_library_item_info_templates( template_list=[], restrict=False )[0] %>
                                    <a class="action-button" href="${h.url_for( controller='admin', action='info_template', library_id=library.id, id=template.id, edit_template=True )}">Edit this library's information template</a>
                                %else:
                                    <a class="action-button" href="${h.url_for( controller='admin', action='info_template', library_id=library.id, new_template=True )}">Add an information template to this library</a>
                                %endif
                                <a class="action-button" href="${h.url_for( controller='admin', action='library', id=library.id, permissions=True )}">Edit this library's permissions</a>
                                ## TODO: need to revamp the way libraries, folders, and contained LibraryDatasets are deleted
                                ##<a class="action-button" confirm="Current state will not be saved, so undeleting the library will restore all of its contents.  Click OK to delete the library named '${library.name}'?" href="${h.url_for( controller='admin', action='library', delete=True, id=library.id )}">Delete this library and its contents</a>
                            </div>
                        ##%else:
                        ##    <div popupmenu="library-${library.id}-popup">
                        ##        <a class="action-button" href="${h.url_for( controller='admin', action='undelete_library', id=library.id )}">Undelete this library and its contents</a>
                        ##        <a class="action-button" href="${h.url_for( controller='admin', action='purge_library', id=library.id )}">Purge this library and its contents</a>
                        ##    </div>
                        %endif
                    </th>
                    <th width="100">Format</th>
                    <th width="50">Db</th>
                    <th width="200">Info</th>
                </table>
            </div>
        </li>
        <ul>
            ${render_folder( library.root_folder, 0, library.deleted, created_ldda_ids, library.id )}
        </ul>
        <br/>
    </ul>
    %if not library.deleted:
        <p>
            <b>Perform action on selected datasets:</b>
            <select name="action" id="action_on_datasets_select">
                <option value="edit">Edit selected datasets' permissions</option>
                ##TODO: fix deleting library items<option value="delete">Remove selected datasets from this library</option>
            </select>
            <input type="submit" class="primary-button" name="action_on_datasets_button" id="action_on_datasets_button" value="Go"/>
        </p>
    %endif
</form>
