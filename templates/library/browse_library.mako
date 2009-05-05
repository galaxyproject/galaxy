<%inherit file="/base.mako"/>
<%namespace file="common.mako" import="render_dataset" />
<%namespace file="/message.mako" import="render_msg" />
<% from galaxy import util %>

<%def name="title()">Browse Library</%def>
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
        // Check/uncheck boxes in subfolders.
        $("input.folderCheckbox").click( function() {
            if ( $(this).is(":checked") ) {
                //$(this).parent().children().find("input[type=checkbox]").each( function() { this.checked = true; });
                $(this).parent().next("ul").find("input[type=checkbox]").each( function() { this.checked = true; });
            } else {
                //$(this).parent().children().find("input[type=checkbox]").each( function() { this.checked = false; });
                $(this).parent().next("ul").find("input[type=checkbox]").each( function() { this.checked = false; });
            }
        });
        // If you uncheck a lower level checkbox, uncheck the boxes above it
        // (since deselecting a child means the parent is not fully selected any
        // more).
        $("input[type=checkbox]").click( function() {
            if ( ! $(this).is(":checked") ) {
                //var folder_rows = $(this).parents("ul").next("li.folderRow");
                //var folder_rows = $(this).parents("ul").children("li.folderRow");
                var folder_rows = $(this).parents("ul").prev("li.folderRow");
                //$(folder_rows).children("input[type=checkbox]").not(this).each( function() {
                $(folder_rows).find("input[type=checkbox]").each( function() {
                    this.checked = false;
                });
            }
        });
        // Handle the hide/show triangles
        $("span.expandLink").wrap( "<a href='#' class='expandLink'></a>" ).click( function() {
            var contents = $(this).parents("li:first").next("ul");
            if ( this.id == "libraryRow" ) {
                var icon_open = "${h.url_for( '/static/images/silk/book_open.png' )}";
                var icon_closed = "${h.url_for( '/static/images/silk/book.png' )}";
            } else {
                var icon_open = "${h.url_for( '/static/images/silk/folder_page.png' )}";
                var icon_closed = "${h.url_for( '/static/images/silk/folder.png' )}";
            }
            if ( contents.is(":visible") ) {
                contents.slideUp("fast");
                $(this).find("img.expanderIcon").each( function() { this.src = "${h.url_for( '/static/images/silk/resultset_next.png' )}"; });
                $(this).find("img.rowIcon").each( function() { this.src = icon_closed; });
            } else {
                contents.slideDown("fast");
                $(this).find("img.expanderIcon").each( function() { this.src = "${h.url_for( '/static/images/silk/resultset_bottom.png' )}"; });
                $(this).find("img.rowIcon").each( function() { this.src = icon_open; });
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
</script>

<![if gte IE 7]>
<script type="text/javascript">
    $( document ).ready( function() {
        // Add rollover effect to any image with a 'rollover' attribute
        preload_images = {}
        $( "img[rollover]" ).each( function() {
            var r = $(this).attr('rollover');
            var s = $(this).attr('src');
            preload_images[r] = true;
            $(this).hover( 
                function() { $(this).attr( 'src', r ) },
                function() { $(this).attr( 'src', s ) }
            )
        })
        for ( r in preload_images ) { $( "<img>" ).attr( "src", r ) }
    })
</script>
<![endif]>

<%def name="render_folder( parent, parent_pad, created_ldda_ids, library_id )">
    <%
        def show_folder():
            if trans.app.security_agent.check_folder_contents( trans.user, parent ) or trans.app.security_agent.show_library_item( trans.user, parent ):
                return True
            return False
        if not show_folder:
            return ""
        root_folder = not parent.parent
        if root_folder:
            pad = parent_pad
        else:
            pad = parent_pad + 20
        if parent_pad == 0:
            expander = "/static/images/silk/resultset_bottom.png"
            folder = "/static/images/silk/folder_page.png"
            subfolder = False
        else:
            expander = "/static/images/silk/resultset_next.png"
            folder = "/static/images/silk/folder.png"
            subfolder = True
        created_ldda_id_list = util.listify( created_ldda_ids )
        if created_ldda_id_list:
           created_ldda_ids = [ int( ldda_id ) for ldda_id in created_ldda_id_list ]
    %>
    %if not root_folder:
        <li class="folderRow libraryOrFolderRow" style="padding-left: ${pad}px;">
            <input type="checkbox" class="folderCheckbox" style="float: left;"/>
            <div class="rowTitle">
                <span class="expandLink"><img src="${h.url_for( expander )}" class="expanderIcon"/><img src="${h.url_for( folder )}" class="rowIcon"/>
                ${parent.name}
                %if parent.description:
                    <i>- ${parent.description}</i>
                %endif
                <a id="folder-${parent.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                <div popupmenu="folder-${parent.id}-popup">
                    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=parent ):
                        <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library_id, folder_id=parent.id )}">Add datasets to this folder</a>
                        <a class="action-button" href="${h.url_for( controller='library', action='folder', new=True, id=parent.id, library_id=library_id )}">Create a new sub-folder in this folder</a>
                    %endif
                    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=parent ):
                        <a class="action-button" href="${h.url_for( controller='library', action='folder', information=True, id=parent.id, library_id=library_id )}">Edit this folder's information</a>
                    %else:
                        <a class="action-button" href="${h.url_for( controller='library', action='folder', information=True, id=parent.id, library_id=library_id )}">View this folder's information</a>
                    %endif
                    %if parent.library_folder_info_template_associations:
                        %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=parent ):
                            <% template = parent.get_library_item_info_templates( template_list=[], restrict=True )[0] %>
                            <a class="action-button" href="${h.url_for( controller='library', action='info_template', library_id=library.id, id=template.id, edit_template=True )}">Edit this folder's information template</a>
                        %endif
                    %else:
                        %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=parent ):
                            <a class="action-button" href="${h.url_for( controller='library', action='info_template', library_id=library.id, folder_id=parent.id, new_template=True )}">Add an information template to this folder</a>
                        %endif
                    %endif
                    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=parent ):
                        <a class="action-button" href="${h.url_for( controller='library', action='folder', permissions=True, id=parent.id, library_id=library_id )}">Edit this folder's permissions</a>
                    %endif
                </div>
            </div>
        </li>
    %endif
    %if subfolder:
        <ul id="subFolder" style="display: none;">
    %else:
        <ul>
    %endif
        %for folder in name_sorted( parent.active_folders ):
            ${render_folder( folder, pad, created_ldda_ids, library_id )}
        %endfor
        %for library_dataset in name_sorted( parent.active_datasets ):
            <%
                selected = created_ldda_ids and library_dataset.library_dataset_dataset_association.id in created_ldda_ids
            %>
            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_ACCESS, dataset=library_dataset.library_dataset_dataset_association.dataset ):
                <li class="datasetRow" style="padding-left: ${pad + 20}px;">${render_dataset( library_dataset, selected, library )}</li>
            %endif
        %endfor
    </ul>
</%def>

<h2>Library '${library.name}'</h2>

%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library ):
    <ul class="manage-table-actions">
        %if not deleted:
            <li>
                <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library.id, folder_id=library.root_folder.id )}"><span>Add datasets to this library</span></a>
            </li>
            <li>
                <a class="action-button" href="${h.url_for( controller='library', action='folder', new=True, id=library.root_folder.id, library_id=library.id )}">Add a folder to this library</a>
            </li>
        %endif
    </ul>
%endif

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<form name="import_from_library" action="${h.url_for( controller='library', action='datasets', library_id=library.id )}" method="post">
    <ul>
        <li class="libraryRow libraryOrFolderRow">
            <div class="rowTitle">
                <%
                    library_item_ids = {}
                    library_item_ids[ 'library' ] = library.id
                %>
                <table cellspacing="0" cellpadding="0" border="0" width="100%" class="libraryTitle">
                    <tr>
                        <th width="*">
                            <span class="expandLink" id="libraryRow"><img src="${h.url_for( '/static/images/silk/resultset_bottom.png' )}" class="expanderIcon"/><img src="${h.url_for( '/static/images/silk/book_open.png' )}" class="rowIcon"/>
                                ${library.name}
                                %if library.description:
                                    <i>- ${library.description}</i>
                                %endif
                                <a id="library-${library.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                                <div popupmenu="library-${library.id}-popup">
                                    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=library ):
                                        <a class="action-button" href="${h.url_for( controller='library', action='library', information=True, id=library.id )}">Edit this library's information</a>
                                    %else:
                                        <a class="action-button" href="${h.url_for( controller='library', action='library', information=True, id=library.id )}">View this library's information</a>
                                    %endif

                                    %if library.library_info_template_associations:
                                        <% template = library.get_library_item_info_templates( template_list=[], restrict=False )[0] %>
                                        %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=template ):
                                            <a class="action-button" href="${h.url_for( controller='library', action='info_template', library_id=library.id, id=template.id, edit_template=True )}">Edit this library's information template</a>
                                        %endif
                                    %else:
                                        %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library ):
                                            <a class="action-button" href="${h.url_for( controller='library', action='info_template', library_id=library.id, new_template=True )}">Add an information template to this library</a>
                                        %endif
                                    %endif
                                    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=library ):
                                        <a class="action-button" href="${h.url_for( controller='library', action='library', permissions=True, id=library.id )}">Edit this library's permissions</a>
                                    %endif
                                </div>
                            </span>
                        </th>
                    <th width="500">Information</th>
                    <th width="150">Uploaded By</th>
                    <th width="60">Date</th>
                    </tr>
                </table>
            </div>
        </li>
        <ul>
            ${render_folder( library.root_folder, 0, created_ldda_ids, library.id )}
        </ul>
        <br/>
    </ul>
    <select name="do_action" id="action_on_datasets_select">
        %if default_action == 'add':
            <option value="add" selected>Import selected datasets into your current history</option>
        %else:
            <option value="add">Import selected datasets into your current history</option>
        %endif
        %if default_action == 'manage_permissions':
            <option value="manage_permissions" selected>Edit selected datasets' permissions</option>
            # This condition should not contain an else clause because the user is not authorized
            # to manage dataset permissions unless the default action is 'manage_permissions'
        %endif
        %if 'bz2' in comptypes:
            <option value="tbz"
            %if default_action == 'download':
                selected
            %endif>
            >Download selected datasets as a .tar.bz2 file</option>
        %endif
        %if 'gz' in comptypes:
            <option value="tgz">Download selected datasets as a .tar.gz file</option>
        %endif
        %if 'zip' in comptypes:
            <option value="zip">Download selected datasets as a .zip file</option>
        %endif
    </select>
    <input type="submit" class="primary-button" name="action_on_datasets_button" id="action_on_datasets_button" value="Go"/>
</form>

%if len( comptypes ) > 1:
    <div>
        <p class="infomark">
            TIP: Multiple compression options are available for downloading library datasets:
        </p>
        <ul style="padding-left: 1em; list-style-type: disc;">
            %if 'bz2' in comptypes:
                <li>bzip2: Compression takes the most time but is better for slower network connections (that transfer slower than the rate of compression) since the resulting file size is smallest.</li>
            %endif
            %if 'gz' in comptypes:
                <li>gzip: Compression is faster and yields a larger file, making it more suitable for fast network connections.</li>
            %endif
            %if 'zip' in comptypes:
                <li>ZIP: Not recommended but is provided as an option for those on Windows without WinZip (since WinZip can read .bz2 and .gz files).</li>
            %endif
        </ul>
    </div>
%endif
