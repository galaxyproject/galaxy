<%inherit file="/base.mako"/>
<%namespace file="common.mako" import="render_dataset" />
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Import from Library</%def>
<%def name="stylesheets()">
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
    <link href="${h.url_for('/static/style/library.css')}" rel="stylesheet" type="text/css" />
</%def>

<%
def name_sorted( l ):
    return sorted( l, lambda a, b: cmp( a.name.lower(), b.name.lower() ) )
%>

<script type="text/javascript">
    //var q = jQuery.noConflict();
    $( document ).ready( function () {
        // Check/uncheck boxes in subfolders.
        $("input.folderCheckbox").click( function() {
            if ( $(this).is(":checked") ) {
                //$(this).parent().children().find("input[@type=checkbox]").each( function() { this.checked = true; });
                $(this).parent().next("ul").find("input[@type=checkbox]").each( function() { this.checked = true; });
            } else {
                //$(this).parent().children().find("input[@type=checkbox]").each( function() { this.checked = false; });
                $(this).parent().next("ul").find("input[@type=checkbox]").each( function() { this.checked = false; });
            }
        });
        // If you uncheck a lower level checkbox, uncheck the boxes above it
        // (since deselecting a child means the parent is not fully selected any
        // more).
        $("input[@type=checkbox]").click( function() {
            if ( ! $(this).is(":checked") ) {
                //var folder_rows = $(this).parents("ul").next("li.folderRow");
                //var folder_rows = $(this).parents("ul").children("li.folderRow");
                var folder_rows = $(this).parents("ul").prev("li.folderRow");
                //$(folder_rows).children("input[@type=checkbox]").not(this).each( function() {
                $(folder_rows).find("input[@type=checkbox]").each( function() {
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
        $( "img[@rollover]" ).each( function() {
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

<%def name="render_folder( parent, parent_pad )">
    <%
        def show_folder():
            if trans.app.security_agent.check_folder_contents( trans.user, parent ) or trans.app.security_agent.show_library_item( trans.user, parent ):
                return True
        if not show_folder:
            return ""
        pad = parent_pad + 20
        if parent_pad == 0:
            expander = "/static/images/silk/resultset_bottom.png"
            folder = "/static/images/silk/folder_page.png"
            subfolder = False
        else:
            expander = "/static/images/silk/resultset_next.png"
            folder = "/static/images/silk/folder.png"
            subfolder = True
    %>
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
                %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=parent ):
                    <a class="action-button" href="${h.url_for( controller='library', action='folder', folder_id=parent.id )}">Manage folder</a>
                %endif
            </div>
        </div>
    </li>
    %if subfolder:
        <ul id="subFolder" style="display: none;">
    %else:
        <ul>
    %endif
    %for folder in name_sorted( parent.active_folders ):
        ${render_folder( folder, pad )}
    %endfor
    %for dataset in name_sorted( parent.active_datasets ):
        %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_ACCESS, dataset=dataset.dataset ):
            <li class="datasetRow" style="padding-left: ${pad + 20}px;">${render_dataset( dataset )}</li>
        %endif
    %endfor
    </ul>
</%def>

<h2>Libraries</h2>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if not libraries:
    No libraries contain datasets that you are allowed to access
%else:
    <% can_access = False %>
    <form name="import_from_library" action="${h.url_for( controller='library', action='import_datasets' )}" method="post">
        <ul>
            %for library in libraries:
                %if trans.app.security_agent.check_folder_contents( trans.user, library ) or trans.app.security_agent.show_library_item( trans.user, library ):
                    <% can_access = True %>
                    <li class="libraryRow libraryOrFolderRow">
                        <div class="rowTitle">
                            <table cellspacing="0" cellpadding="0" border="0" width="100%" class="libraryTitle">
                                <tr>
                                    <th width="*">
                                        <span class="expandLink" id="libraryRow"><img src="${h.url_for( '/static/images/silk/resultset_bottom.png' )}" class="expanderIcon"/><img src="${h.url_for( '/static/images/silk/book_open.png' )}" class="rowIcon"/>
                                            ${library.name}
                                            %if library.description:
                                                <i>- ${library.description}</i>
                                            %endif
                                            %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=library ) or \
                                                trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library ) or \
                                                trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=library ):
                                                <a id="library-${library.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                                            %endif
                                        </span>
                                    </th>
                                    <th width="100">Format</th>
                                    <th width="50">Db</th>
                                    <th width="200">Info</th>
                                </tr>
                            </table>
                        </div>
                        <div popupmenu="library-${library.id}-popup">
                            <a class="action-button" href="${h.url_for( controller='library', action='edit_library', id=library.id )}">Manage Library</a>
			            </div>
                    </li>
                    <ul>
                        ${render_folder( library.root_folder, 0 )}
                    </ul>
                    <br/>
                %endif
            %endfor
        </ul>
        %if can_access:
            <select name="do_action" id="action_on_datasets_select">
                %if default_action == 'add':
                    <option value="add" selected>Add selected datasets to history</option>
                %else:
                    <option value="add">Add selected datasets to history</option>
                %endif
                %if default_action == 'download':
                    <option value="zip" selected>Download selected datasets as a .zip file</option>
                %else:
                    <option value="zip">Download selected datasets as a .zip file</option>
                %endif
                <option value="tgz">Download selected datasets as a .tar.gz file</option>
                <option value="tbz">Download selected datasets as a .tar.bz2 file</option>
            </select>
            <input type="submit" class="primary-button" name="action_on_datasets_button" id="action_on_datasets_button" value="Go"/>
        %else:
            No libraries contain datasets that you are allowed to access
        %endif
    </form>
%endif
