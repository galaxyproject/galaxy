<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<% from galaxy import util %>

<%def name="title()">Browse data library</%def>
<%def name="stylesheets()">
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
    <link href="${h.url_for('/static/style/library.css')}" rel="stylesheet" type="text/css" />
</%def>

<%

def name_sorted( l ):
    return sorted( l, lambda a, b: cmp( a.name.lower(), b.name.lower() ) )

class RowCounter( object ):
    def __init__( self ):
        self.count = 0
    def increment( self ):
        self.count += 1
    def __str__( self ):
        return str( self.count )
%>

<script type="text/javascript">
    $( document ).ready( function () {
        $("#library-grid").each( function() {
           // Recursively fill in children and descendents of each row
           var process_row = function( q, parents ) {
                // Find my index
                var index = $(q).parent().children().index( $(q) );
                // Find my immediate children
                var children = $(q).siblings().filter( "[parent='" + index + "']" );
                // Recursively handle them
                var descendents = children;
                children.each( function() {
                    child_descendents = process_row( $(this), parents.add( q ) );
                    descendents = descendents.add( child_descendents );
                });
                // Set up expand / hide link
                // HACK: assume descendents are invisible. The caller actually
                //       ensures this for the root node. However, if we start
                //       remembering folder states, we'll need something
                //       more sophisticated here.
                var visible = false;
                $(q).find( "span.expandLink").click( function() {
                    if ( visible ) {
                        descendents.hide();
                        descendents.removeClass( "expanded" );
                        q.removeClass( "expanded" );
                        visible = false;
                    } else {
                        children.show();
                        q.addClass( "expanded" );
                        visible = true;
                    }
                });
                // Check/uncheck boxes in subfolders.
                q.children( "td" ).children( "input[type=checkbox]" ).click( function() {
                    if ( $(this).is(":checked") ) {
                        descendents.find( "input[type=checkbox]").attr( 'checked', true );
                    } else {
                        descendents.find( "input[type=checkbox]").attr( 'checked', false );
                        // If you uncheck a lower level checkbox, uncheck the boxes above it
                        // (since deselecting a child means the parent is not fully selected any
                        // more).
                        parents.children( "td" ).children( "input[type=checkbox]" ).attr( "checked", false );
                    }
                });
                // return descendents for use by parent
                return descendents;
           }
           $(this).find( "tbody tr" ).not( "[parent]").each( function() {
                descendents = process_row( $(this), $([]) );
                descendents.hide();
           });
        });
    });
</script>

<%def name="render_dataset( library_dataset, selected, library, pad, parent, row_conter )">
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

    <tr class="datasetRow"
    %if parent is not None:
        parent="${parent}"
        style="display: none;"
    %endif
    >
        <td style="padding-left: ${pad+20}px;">
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
        <td>${ldda.message}</td>
        <td>${uploaded_by}</td>
        <td>${ldda.create_time.strftime( "%Y-%m-%d" )}</td>
    </tr>
                
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>


<%def name="render_folder( folder, folder_pad, created_ldda_ids, library_id, parent=None, row_counter=None )">
    <%
        def show_folder():
            if trans.app.security_agent.check_folder_contents( trans.user, folder ) or trans.app.security_agent.show_library_item( trans.user, folder ):
                return True
            return False
        if not show_folder:
            return ""
        root_folder = not folder.parent
        if root_folder:
            pad = folder_pad
        else:
            pad = folder_pad + 20
        if folder_pad == 0:
            subfolder = False
        else:
            subfolder = True
        created_ldda_id_list = util.listify( created_ldda_ids )
        if created_ldda_id_list:
           created_ldda_ids = [ int( ldda_id ) for ldda_id in created_ldda_id_list ]
        my_row = None
    %>
    %if not root_folder:
        <tr class="folderRow libraryOrFolderRow"
        %if parent is not None:
            parent="${parent}"
            style="display: none;"
        %endif
        >
            <td style="padding-left: ${folder_pad}px;">
                <span class="expandLink"></span>
                <input type="checkbox" class="folderCheckbox"/>
                <span class="rowIcon"></span>
                ${folder.name}
                %if folder.description:
                    <i>- ${folder.description}</i>
                %endif
                <a id="folder_img-${folder.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                <div popupmenu="folder_img-${folder.id}-popup">
                    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=folder ):
                        <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library_id, folder_id=folder.id )}">Add datasets to this folder</a>
                        <a class="action-button" href="${h.url_for( controller='library', action='folder', new=True, id=folder.id, library_id=library_id )}">Create a new sub-folder in this folder</a>
                    %endif
                    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=folder ):
                        <a class="action-button" href="${h.url_for( controller='library', action='folder', information=True, id=folder.id, library_id=library_id )}">Edit this folder's information</a>
                    %else:
                        <a class="action-button" href="${h.url_for( controller='library', action='folder', information=True, id=folder.id, library_id=library_id )}">View this folder's information</a>
                    %endif
                    %if forms and not folder.info_association:
                        %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library ):
                            <a class="action-button" href="${h.url_for( controller='library', action='info_template', library_id=library.id, add=True )}">Add an information template to this folder</a>
                        %endif
                    %endif
                    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=folder ):
                        <a class="action-button" href="${h.url_for( controller='library', action='folder', permissions=True, id=folder.id, library_id=library_id )}">Edit this folder's permissions</a>
                    %endif
                </div>
            </div>
            <td colspan="3"></td>
        </tr>
        <%
            my_row = row_counter.count
            row_counter.increment()
        %>
    %endif
    %for child_folder in name_sorted( folder.active_folders ):
        ${render_folder( child_folder, pad, created_ldda_ids, library_id, my_row, row_counter )}
    %endfor
    %for library_dataset in name_sorted( folder.active_datasets ):
        <%
            selected = created_ldda_ids and library_dataset.library_dataset_dataset_association.id in created_ldda_ids
        %>
        %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_ACCESS, dataset=library_dataset.library_dataset_dataset_association.dataset ):
            ${render_dataset( library_dataset, selected, library, pad, my_row, row_counter )}
        %endif
    %endfor
</%def>

<h2>Data Library &ldquo;${library.name}&rdquo;</h2>

<ul class="manage-table-actions">
    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library ):
            %if not deleted:
                <li>
                    <a class="action-button" href="${h.url_for( controller='library', action='library_dataset_dataset_association', library_id=library.id, folder_id=library.root_folder.id )}"><span>Add datasets to this library</span></a>
                </li>
                <li>
                    <a class="action-button" href="${h.url_for( controller='library', action='folder', new=True, id=library.root_folder.id, library_id=library.id )}">Add a folder to this library</a>
                </li>
            %endif
    %endif
    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=library ):
        <li><a class="action-button" href="${h.url_for( controller='library', action='library', information=True, id=library.id )}">Edit this library's information</a></li>
    %else:
        <li><a class="action-button" href="${h.url_for( controller='library', action='library', information=True, id=library.id )}">View this library's information</a></li>
    %endif
    %if forms and not library.info_association:
        %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library ):
            <a class="action-button" href="${h.url_for( controller='library', action='info_template', library_id=library.id, add=True )}">Add an information template to this library</a>
        %endif
    %endif
    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=library ):
        <li><a class="action-button" href="${h.url_for( controller='library', action='library', permissions=True, id=library.id )}">Edit this library's permissions</a></li>
    %endif 
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<form name="import_from_library" action="${h.url_for( controller='library', action='datasets', library_id=library.id )}" method="post">
    <%
        library_item_ids = {}
        library_item_ids[ 'library' ] = library.id
    %>
    <table cellspacing="0" cellpadding="0" border="0" width="100%" class="grid" id="library-grid">
        <thead>
            <tr class="libraryTitle">
                <th style="padding-left: 42px;">Name</th>
                <th>Information</th>
                <th>Uploaded By</th>
                <th>Date</th>
            </thead>
        </tr>
        <% row_counter = RowCounter() %>
        ${render_folder( library.root_folder, 0, created_ldda_ids, library.id, Nonw, row_counter )}
        <tfoot>
            <tr>
                <td colspan="4" style="padding-left: 42px;">
                    For selected items:
                    <select name="do_action" id="action_on_datasets_select">
                        %if default_action == 'add':
                            <option value="add" selected>Import into your current history</option>
                        %else:
                            <option value="add">Import into your current history</option>
                        %endif
                        %if default_action == 'manage_permissions':
                            <option value="manage_permissions" selected>Edit permissions</option>
                            # This condition should not contain an else clause because the user is not authorized
                            # to manage dataset permissions unless the default action is 'manage_permissions'
                        %endif
                        %if 'bz2' in comptypes:
                            <option value="tbz"
                            %if default_action == 'download':
                                selected
                            %endif>
                            >Download as a .tar.bz2 file</option>
                        %endif
                        %if 'gz' in comptypes:
                            <option value="tgz">Download  as a .tar.gz file</option>
                        %endif
                        %if 'zip' in comptypes:
                            <option value="zip">Download as a .zip file</option>
                        %endif
                    </select>
                    <input type="submit" class="primary-button" name="action_on_datasets_button" id="action_on_datasets_button" value="Go"/>
                </td>
            </tr>
        </tfoot>
    </table>
</form>

## Help about compression types

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
