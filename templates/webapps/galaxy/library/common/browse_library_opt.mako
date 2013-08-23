<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common/library_item_info.mako" import="render_library_item_info" />
<%namespace file="/library/common/common.mako" import="render_actions_on_multiple_items" />
<%namespace file="/library/common/common.mako" import="render_compression_types_help" />
<%namespace file="/library/common/common.mako" import="common_javascripts" />

<%!
    def inherit(context):
        if context.get('use_panels'):
            return '/webapps/galaxy/base_panels.mako'
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
    self.active_view="user"
    self.overlay_visible=False
    self.has_accessible_datasets = False
%>
</%def>

##
## Override methods from base.mako and base_panels.mako
##
<%def name="center_panel()">
   <div style="overflow: auto; height: 100%;">
       <div class="page-container" style="padding: 10px;">
           ${render_content()}
       </div>
   </div>
</%def>

## Render the grid's basic elements. Each of these elements can be subclassed.
<%def name="body()">
    ${render_content()}
</%def>

<%def name="title()">Browse data library</%def>
<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js("libs/jquery/jstorage")}
    ${common_javascripts()}
    ${self.grid_javascripts()}
</%def>

<%def name="grid_javascripts()">
    <script type="text/javascript">
        var init_libraries = function() {
            var storage_id = "library-expand-state-${trans.security.encode_id(library.id)}";
            
            var restore_folder_state = function() {
                var state = $.jStorage.get(storage_id);
                if (state) {
                    for (var id in state) {
                        if (state[id] === true) {
                            var row = $("#" + id),
                                index = row.parent().children().index(row);
                            row.addClass("expanded").show();
                            row.siblings().filter("tr[parent='" + index + "']").show();
                        }
                    }
                }
            };
            
            var save_folder_state = function() {
                var state = {};
                $("tr.folderRow").each( function() {
                    var folder = $(this);
                    state[folder.attr("id")] = folder.hasClass("expanded");
                });
                $.jStorage.set(storage_id, state);
            };
            
            $("#library-grid").each(function() {
                var child_of_parent_cache = {};
                // Recursively fill in children and descendents of each row
                var process_row = function(q, parents) {
                    // Find my index
                    var parent = q.parent(),
                        this_level = child_of_parent_cache[parent] || (child_of_parent_cache[parent] = parent.children());
                        
                    var index = this_level.index(q);
                    // Find my immediate children
                    var children = $(par_child_dict[index]);
                    // Recursively handle them
                    var descendents = children;
                    children.each( function() {
                        child_descendents = process_row( $(this), parents.add(q) );
                        descendents = descendents.add(child_descendents);
                    });
                    // Set up expand / hide link
                    var expand_fn = function() {
                        if ( q.hasClass("expanded") ) {
                            descendents.hide();
                            descendents.removeClass("expanded");
                            q.removeClass("expanded");
                        } else {
                            children.show();
                            q.addClass("expanded");
                        }
                        save_folder_state();
                    };
                    $("." + q.attr("id") + "-click").click(expand_fn);
                    // Check/uncheck boxes in subfolders.
                    q.children("td").children("input[type=checkbox]").click( function() {
                        if ( $(this).is(":checked") ) {
                            descendents.find("input[type=checkbox]").attr("checked", true);
                        } else {
                            descendents.find("input[type=checkbox]").attr("checked", false);
                            // If you uncheck a lower level checkbox, uncheck the boxes above it
                            // (since deselecting a child means the parent is not fully selected any more).
                            parents.children("td").children("input[type=checkbox]").attr("checked", false);
                        }
                    });
                    // return descendents for use by parent
                    return descendents;
                }
                
                // Initialize dict[parent_id] = rows_which_have_that_parent_id_as_parent_attr
                var par_child_dict = {},
                    no_parent = [];
                
                $(this).find("tbody tr").each( function() {
                    if ( $(this).attr("parent")) {
                        var parent = $(this).attr("parent");
                        if (par_child_dict[parent] !== undefined) {
                            par_child_dict[parent].push(this);
                        } else {
                            par_child_dict[parent] = [this];
                        }
                    } else {
                        no_parent.push(this);
                    }                        
                });
                
                $(no_parent).each( function() {
                    descendents = process_row( $(this), $([]) );
                    descendents.hide();
               });
            });
            
            restore_folder_state();
        };
        $(function() {
            init_libraries();
        });
        
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
</%def>

<%def name="render_dataset( cntrller, ldda, library_dataset, can_modify, can_manage, selected, library, folder, pad, parent, row_counter, tracked_datasets, show_deleted=False, simple=False )">
    <%
        ## The received ldda must always be a LibraryDatasetDatasetAssociation object.  The object id passed to methods
        ## from the drop down menu should be the ldda id to prevent id collision ( which could happen when displaying
        ## children, which are always lddas ).  We also need to make sure we're displaying the latest version of this
        ## library_dataset, so we display the attributes from the ldda.
        
        from galaxy.webapps.galaxy.controllers.library_common import branch_deleted

        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_version = ( ldda == library_dataset.library_dataset_dataset_association )
        if current_version and ldda.state not in ( 'ok', 'error', 'empty', 'deleted', 'discarded' ):
            tracked_datasets[ldda.id] = ldda.state
        # SM: This causes a query to be emitted, but it quickly goes down a
        # rabbit hole of many possible inheritable cases. It may not be 
        # possible to easily eliminate the extra query from this call.
        info_association, inherited = ldda.get_info_association( restrict=True )
        form_type = trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
    %>
    %if current_version and ( not ldda.library_dataset.deleted or show_deleted ):
        <tr class="datasetRow"
            %if parent is not None:
                parent="${parent}"
            %endif
            id="libraryItem-${ldda.id}">
            <td style="padding-left: ${pad+20}px;">
                <input style="float: left;" type="checkbox" name="ldda_ids" id="${trans.security.encode_id( ldda.id )}" value="${trans.security.encode_id( ldda.id )}"
                %if selected:
                    checked="checked"
                %endif
                />
                %if simple:
                    <label for="${trans.security.encode_id( ldda.id )}">${ util.unicodify( ldda.name )}</label>
                %else:
                    <div style="float: left; margin-left: 1px;" class="menubutton split popup" id="dataset-${ldda.id}-popup">
                        <a class="view-info" href="${h.url_for( controller='library_common', action='ldda_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">
                            %if ldda.library_dataset.deleted:
                                <div class="libraryItem-error">${util.unicodify( ldda.name )}</div>
                            %else:
                                ${util.unicodify( ldda.name )}
                            %endif     
                        </a>
                    </div>
                    %if not library.deleted:
                        <div popupmenu="dataset-${ldda.id}-popup">
                            %if not branch_deleted( folder ) and not ldda.library_dataset.deleted and can_modify:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_edit_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit information</a>
                                <a class="action-button" href="${h.url_for( controller='library_common', action='move_library_item', cntrller=cntrller, item_type='ldda', item_id=trans.security.encode_id( ldda.id ), source_library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Move this dataset</a>
                            %else:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">View information</a>
                            %endif
                            %if not branch_deleted( folder ) and not ldda.library_dataset.deleted and can_modify and not info_association:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type='ldda', form_type=form_type, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), ldda_id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Use template</a>
                            %endif
                            %if not branch_deleted( folder ) and not ldda.library_dataset.deleted and can_modify and info_association:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='edit_template', cntrller=cntrller, item_type='ldda', form_type=form_type, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), ldda_id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit template</a>
                                <a class="action-button" href="${h.url_for( controller='library_common', action='delete_template', cntrller=cntrller, item_type='ldda', form_type=form_type, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), ldda_id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Unuse template</a>
                            %endif
                            %if not branch_deleted( folder ) and not ldda.library_dataset.deleted and can_manage:
                                %if not trans.app.security_agent.dataset_is_public( ldda.dataset ):
                                    <a class="action-button" href="${h.url_for( controller='library_common', action='make_library_item_public', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_type='ldda', id=trans.security.encode_id( ldda.dataset.id ), use_panels=use_panels, show_deleted=show_deleted )}">Make public</a>
                                %endif
                                <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_permissions', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), id=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit permissions</a>
                            %endif
                            %if not branch_deleted( folder ) and not ldda.library_dataset.deleted and can_modify:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), replace_id=trans.security.encode_id( library_dataset.id ), show_deleted=show_deleted )}">Upload a new version of this dataset</a>
                            %endif
                            %if not branch_deleted( folder ) and not ldda.library_dataset.deleted and ldda.has_data:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='import_datasets_to_histories', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), ldda_ids=trans.security.encode_id( ldda.id ), use_panels=use_panels, show_deleted=show_deleted )}">Import this dataset into selected histories</a>
                                <a class="action-button" href="${h.url_for( controller='library_common', action='download_dataset_from_folder', cntrller=cntrller, id=trans.security.encode_id( ldda.id ), library_id=trans.security.encode_id( library.id ), use_panels=use_panels )}">Download this dataset</a>
                            %endif
                            %if can_modify:
                                %if not library.deleted and not branch_deleted( folder ) and not ldda.library_dataset.deleted:
                                    <a class="action-button" confirm="Click OK to delete dataset '${util.unicodify( ldda.name )}'." href="${h.url_for( controller='library_common', action='delete_library_item', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_id=trans.security.encode_id( library_dataset.id ), item_type='library_dataset', show_deleted=show_deleted )}">Delete this dataset</a>
                                %elif not library.deleted and not branch_deleted( folder ) and not ldda.library_dataset.purged and ldda.library_dataset.deleted:
                                    <a class="action-button" href="${h.url_for( controller='library_common', action='undelete_library_item', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_id=trans.security.encode_id( library_dataset.id ), item_type='library_dataset', show_deleted=show_deleted )}">Undelete this dataset</a>
                                %endif
                            %endif
                        </div>
                    %endif
                %endif
            </td>
            % if not simple:
                <td id="libraryItemInfo">${render_library_item_info( ldda )}</td>
                <td>${ldda.extension}</td>
            % endif
            <td>${ldda.create_time.strftime( "%Y-%m-%d" )}</td>
            <td>${ldda.get_size( nice_size=True )}</td>
        </tr>
        <%
            my_row = row_counter.count
            row_counter.increment()
        %>
    %endif
</%def>

<%def name="format_delta( tdelta )">
    <%
        from datetime import datetime
        return "%d.%.6d" % ( tdelta.seconds, tdelta.microseconds )
     %>
</%def>

<%def name="render_folder( cntrller, folder, folder_pad, created_ldda_ids, library, hidden_folder_ids, tracked_datasets, show_deleted=False, parent=None, row_counter=None, root_folder=False, simple=False )">
    <%
        from galaxy.webapps.galaxy.controllers.library_common import active_folders, active_folders_and_library_datasets, activatable_folders_and_library_datasets, map_library_datasets_to_lddas, branch_deleted, datasets_for_lddas 

        # SM: DELETEME
        from datetime import datetime, timedelta
        import logging
        log = logging.getLogger( __name__ )
        
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        has_accessible_library_datasets = trans.app.security_agent.has_accessible_library_datasets( trans, folder, trans.user, current_user_roles, search_downward=False )
        
        if root_folder:
            pad = folder_pad
            expander = h.url_for("/static/images/silk/resultset_bottom.png")
            folder_img = h.url_for("/static/images/silk/folder_page.png")
        else:
            pad = folder_pad + 20
            expander = h.url_for("/static/images/silk/resultset_next.png")
            folder_img = h.url_for("/static/images/silk/folder.png")
        # SM: If this is a comma-delimited list of LDDAs, then split them up
        # into a list. For anything else, turn created_ldda_ids into a single
        # item list.
        if created_ldda_ids:
            created_ldda_ids = util.listify( created_ldda_ids )
        if str( folder.id ) in hidden_folder_ids:
            return ""
        my_row = None
        if is_admin:
            can_add = can_modify = can_manage = True
        elif cntrller in [ 'library' ]:
            can_access, folder_ids = trans.app.security_agent.check_folder_contents( trans.user, current_user_roles, folder )
            if not can_access:
                can_show, folder_ids = \
                    trans.app.security_agent.show_library_item( trans.user,
                                                                current_user_roles,
                                                                folder,
                                                                [ trans.app.security_agent.permitted_actions.LIBRARY_ADD,
                                                                  trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                                  trans.app.security_agent.permitted_actions.LIBRARY_MANAGE ] )
                if not can_show:
                    return ""
            can_add = trans.app.security_agent.can_add_library_item( current_user_roles, folder )
            can_modify = trans.app.security_agent.can_modify_library_item( current_user_roles, folder )
            can_manage = trans.app.security_agent.can_manage_library_item( current_user_roles, folder )
        else:
            can_add = can_modify = can_manage = False
            
        form_type = trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
        info_association, inherited = folder.get_info_association( restrict=True )
    %>
    %if not root_folder and ( not folder.deleted or show_deleted ):
        <% encoded_id = trans.security.encode_id( folder.id ) %>
        <tr id="folder-${encoded_id}" class="folderRow libraryOrFolderRow"
            %if parent is not None:
                parent="${parent}"
                style="display: none;"
            %endif
            >
            <td style="padding-left: ${folder_pad}px;">
                <input type="checkbox" class="folderCheckbox"/>
                <span class="expandLink folder-${encoded_id}-click">
                    <div style="float: left; margin-left: 2px;" class="menubutton split popup" id="folder_img-${folder.id}-popup">
                        <a class="folder-${encoded_id}-click" href="javascript:void(0);">
                            <span class="rowIcon"></span>
                            %if folder.deleted:
                                <div class="libraryItem-error">${folder.name}</div>
                            %else:
                                ${folder.name}
                            %endif
                        </a>
                    </div>
                </span>
                %if not library.deleted:
                    <div popupmenu="folder_img-${folder.id}-popup">
                        %if not branch_deleted( folder ) and can_add:
                            <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), use_panels=use_panels, show_deleted=show_deleted )}">Add datasets</a>
                            <a class="action-button" href="${h.url_for( controller='library_common', action='create_folder', cntrller=cntrller, parent_id=trans.security.encode_id( folder.id ), library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Add sub-folder</a>
                        %endif
                        %if not branch_deleted( folder ):
                            %if has_accessible_library_datasets:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='import_datasets_to_histories', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), use_panels=use_panels, show_deleted=show_deleted )}">Select datasets for import into selected histories</a>
                            %endif
                            %if can_modify:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='folder_info', cntrller=cntrller, id=trans.security.encode_id( folder.id ), library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit information</a>
                                <a class="action-button" href="${h.url_for( controller='library_common', action='move_library_item', cntrller=cntrller, item_type='folder', item_id=trans.security.encode_id( folder.id ), source_library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Move this folder</a>
                            %else:
                                <a class="action-button" class="view-info" href="${h.url_for( controller='library_common', action='folder_info', cntrller=cntrller, id=trans.security.encode_id( folder.id ), library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">View information</a>
                            %endif
                        %endif
                        %if not branch_deleted( folder ) and can_modify and not info_association:
                            <a class="action-button" href="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type='folder', form_type=form_type, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), use_panels=use_panels, show_deleted=show_deleted )}">Use template</a>
                        %endif
                        %if not branch_deleted( folder ) and can_modify and info_association:
                            <a class="action-button" href="${h.url_for( controller='library_common', action='edit_template', cntrller=cntrller, item_type='folder', form_type=form_type, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit template</a>
                            <a class="action-button" href="${h.url_for( controller='library_common', action='delete_template', cntrller=cntrller, item_type='folder', form_type=form_type, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), use_panels=use_panels, show_deleted=show_deleted )}">Unuse template</a>
                        %endif
                        %if not branch_deleted( folder ) and can_manage:
                           %if not trans.app.security_agent.folder_is_public( folder ):
                               <a class="action-button" href="${h.url_for( controller='library_common', action='make_library_item_public', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_type='folder', id=trans.security.encode_id( folder.id ), use_panels=use_panels, show_deleted=show_deleted )}">Make public</a>
                           %endif
                            <a class="action-button" href="${h.url_for( controller='library_common', action='folder_permissions', cntrller=cntrller, id=trans.security.encode_id( folder.id ), library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit permissions</a>
                        %endif
                        %if can_modify:
                            %if not library.deleted and not folder.deleted:
                                <a class="action-button" confirm="Click OK to delete the folder '${folder.name}.'" href="${h.url_for( controller='library_common', action='delete_library_item', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_id=trans.security.encode_id( folder.id ), item_type='folder', show_deleted=show_deleted )}">Delete this folder</a>
                            %elif not library.deleted and folder.deleted and not folder.purged:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='undelete_library_item', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_id=trans.security.encode_id( folder.id ), item_type='folder', show_deleted=show_deleted )}">Undelete this folder</a>
                            %endif
                        %endif
                    </div>
                %endif
            <td>
            %if folder.description:
                ${folder.description}
            %endif
            <td colspan="3"></td>
        </tr>
        <%
            my_row = row_counter.count
            row_counter.increment()
        %>
    %endif
    <%
        # TODO: If show_deleted is set to True, then nothing is displayed. Why? This wasn't the case
        # in the past.
        if show_deleted:
            sub_folders, library_datasets = activatable_folders_and_library_datasets( trans, folder )
        else:
            sub_folders, library_datasets = active_folders_and_library_datasets( trans, folder )
        # Render all the subfolders: 
        # TODO: Check permissions first. 
        for sub_folder in sub_folders:
            render_folder( cntrller, sub_folder, pad, created_ldda_ids, library, [], tracked_datasets, show_deleted=show_deleted, parent=my_row, row_counter=row_counter, root_folder=False )

        # Map LibraryDatasets to LDDAs, then map LDDAs to Datasets.
        # Then determine which Datasets are accessible and which are not.
        # For every LibraryDataset, if there's an LDDA for it and it's 
        # accessible then display it.
        if ( len( library_datasets ) > 0 ):
            lib_dataset_ldda_map = map_library_datasets_to_lddas( trans, library_datasets )
            dataset_list = datasets_for_lddas( trans, lib_dataset_ldda_map.values() )
            #can_access_datasets = trans.app.security_agent.dataset_access_mapping( trans, current_user_roles, dataset_list )
            can_access_datasets = trans.app.security_agent.dataset_permission_map_for_access( trans, current_user_roles, dataset_list )
            can_modify_datasets = trans.app.security_agent.item_permission_map_for_modify( trans, current_user_roles, dataset_list )
            can_manage_datasets = trans.app.security_agent.item_permission_map_for_manage( trans, current_user_roles, dataset_list )
            for library_dataset in library_datasets:
                ldda = lib_dataset_ldda_map[ library_dataset.id ]
                if ldda: 
                    # SMTODO: Fix awkard modify/manage permission checks.
                    can_access = is_admin or can_access_datasets[ ldda.dataset_id ]
                    can_modify = is_admin or ( cntrller in ['library', 'requests'] and can_modify_datasets[ ldda.dataset_id ])
                    can_manage = is_admin or ( cntrller in ['library', 'requests'] and can_manage_datasets[ ldda.dataset_id ])
                    selected = created_ldda_ids and str( ldda.id ) in created_ldda_ids
                    if can_access:
                        render_dataset( cntrller, ldda, library_dataset, can_modify, can_manage, selected, library, folder, pad, my_row, row_counter, tracked_datasets, show_deleted=show_deleted )
    %>
</%def>

<%def name="render_content(simple=False)">
    <%
        from galaxy import util
        from galaxy.webapps.galaxy.controllers.library_common import branch_deleted
        from time import strftime
        import logging
        log = logging.getLogger( __name__ )
        
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        
        if is_admin:
            can_add = can_modify = can_manage = True
        elif cntrller in [ 'library', 'requests' ]:
            can_add = trans.app.security_agent.can_add_library_item( current_user_roles, library )
            can_modify = trans.app.security_agent.can_modify_library_item( current_user_roles, library )
            can_manage = trans.app.security_agent.can_manage_library_item( current_user_roles, library )
        else:
            can_add = can_modify = can_manage = False
            
        info_association, inherited = library.get_info_association()
        form_type = trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
        
        # SM: These are mostly display-specific; ignore them for now. 
        # The has_accessible_folders determines if anything can be shown - use it.
        self.has_accessible_datasets = trans.app.security_agent.has_accessible_library_datasets( trans, library.root_folder, trans.user, current_user_roles )
        root_folder_has_accessible_library_datasets = trans.app.security_agent.has_accessible_library_datasets( trans, library.root_folder, trans.user, current_user_roles, search_downward=False )
        has_accessible_folders = is_admin or trans.app.security_agent.has_accessible_folders( trans, library.root_folder, trans.user, current_user_roles )
        
        tracked_datasets = {}
        
        class RowCounter( object ):
            def __init__( self ):
                self.count = 0
            def increment( self ):
                self.count += 1
            def __str__( self ):
                return str( self.count )
    %>
    
    <h2>Data Library &ldquo;${library.name}&rdquo;</h2>
    
     <ul class="manage-table-actions">
         %if not library.deleted and ( is_admin or can_add ):
             <li><a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( library.root_folder.id ), use_panels=use_panels, show_deleted=show_deleted )}">Add datasets</a></li>
             <li><a class="action-button" href="${h.url_for( controller='library_common', action='create_folder', cntrller=cntrller, parent_id=trans.security.encode_id( library.root_folder.id ), library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Add folder</a></li>
         %endif
         %if ( ( not library.deleted ) and ( can_modify or can_manage ) ) or ( can_modify and not library.purged ) or ( library.purged ):
             <li><a class="action-button" id="library-${library.id}-popup" class="menubutton">Library Actions</a></li>
             <div popupmenu="library-${library.id}-popup">
                 %if not library.deleted:
                     %if can_modify:
                         <a class="action-button" href="${h.url_for( controller='library_common', action='library_info', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit information</a>
                         <a class="action-button" confirm="Click OK to delete the library named '${library.name}'." href="${h.url_for( controller='library_common', action='delete_library_item', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_id=trans.security.encode_id( library.id ), item_type='library' )}">Delete this data library</a>
                         %if show_deleted:
                             <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=False )}">Hide deleted items</a>
                         %else:
                             <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=True )}">Show deleted items</a>
                         %endif
                     %endif
                     %if can_modify and not library.info_association:
                         <a class="action-button" href="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type='library', form_type=form_type, library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Use template</a>
                     %endif
                     %if can_modify and info_association:
                         <a class="action-button" href="${h.url_for( controller='library_common', action='edit_template', cntrller=cntrller, item_type='library', form_type=form_type, library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit template</a>
                         <a class="action-button" href="${h.url_for( controller='library_common', action='delete_template', cntrller=cntrller, item_type='library', form_type=form_type, library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Unuse template</a>
                     %endif
                     %if can_manage:
                         %if not trans.app.security_agent.library_is_public( library, contents=True ):
                             <a class="action-button" href="${h.url_for( controller='library_common', action='make_library_item_public', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_type='library', id=trans.security.encode_id( library.id ), contents=True, use_panels=use_panels, show_deleted=show_deleted )}">Make public</a>
                         %endif
                         <a class="action-button" href="${h.url_for( controller='library_common', action='library_permissions', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit permissions</a>
                     %endif
                     %if root_folder_has_accessible_library_datasets:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='import_datasets_to_histories', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( library.root_folder.id ), use_panels=use_panels, show_deleted=show_deleted )}">Select datasets for import into selected histories</a>
                     %endif
                 %elif can_modify and not library.purged:
                     <a class="action-button" href="${h.url_for( controller='library_common', action='undelete_library_item', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_id=trans.security.encode_id( library.id ), item_type='library', use_panels=use_panels )}">Undelete this data library</a>
                 %elif library.purged:
                     <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">This data library has been purged</a>
                 %endif
             </div>
         %endif
    </ul>
    
    %if message:
        ${render_msg( message, status )}
    %endif

    %if library.synopsis not in [ '', 'None', None ]:
        <div class="libraryItemBody">
            ${library.synopsis}
        </div>
    %endif
    
    %if self.has_accessible_datasets:
        <form name="act_on_multiple_datasets" action="${h.url_for( controller='library_common', action='act_on_multiple_datasets', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}" onSubmit="javascript:return checkForm();" method="post">
    %endif
    %if has_accessible_folders:
        <table cellspacing="0" cellpadding="0" border="0" width="100%" class="grid" id="library-grid">
            <thead>
                <tr class="libraryTitle">
                    <th>
                        %if self.has_accessible_datasets:
                            <input type="checkbox" id="checkAll" name=select_all_datasets_checkbox value="true" onclick='checkAllFields(1);'/><input type="hidden" name=select_all_datasets_checkbox value="true"/>
                        %endif
                        Name
                    </th>
                    % if not simple:
                        <th>Message</th>
                        <th>Data type</th>
                    % endif
                    <th>Date uploaded</th>
                    <th>File size</th>
                </tr>
            </thead>
            <% row_counter = RowCounter() %>
            ## SM: Here is where we render the libraries based on admin/non-admin privileges:
            %if cntrller in [ 'library', 'requests' ]:
                ${self.render_folder( 'library', library.root_folder, 0, created_ldda_ids, library, hidden_folder_ids, tracked_datasets, show_deleted=show_deleted, parent=None, row_counter=row_counter, root_folder=True, simple=simple )}
                ## SM: TODO: WTF?
                %if not library.deleted and self.has_accessible_datasets and not simple:
                    ${render_actions_on_multiple_items()}
                %endif
            %elif ( trans.user_is_admin() and cntrller in [ 'library_admin', 'requests_admin' ] ):
                ${self.render_folder( 'library_admin', library.root_folder, 0, created_ldda_ids, library, [], tracked_datasets, show_deleted=show_deleted, parent=None, row_counter=row_counter, root_folder=True )}
                ## SM: TODO: WTF?
                %if not library.deleted and not show_deleted and self.has_accessible_datasets:
                    ${render_actions_on_multiple_items()}
                %endif
            %endif
        </table>
    %endif
    %if self.has_accessible_datasets:
        </form>
    %endif
     
    %if tracked_datasets:
        <script type="text/javascript">
            // Updater
            updater({${ ",".join( [ '"%s" : "%s"' % ( k, v ) for k, v in tracked_datasets.iteritems() ] ) }});
        </script>
        <!-- running: do not change this comment, used by TwillTestCase.library_wait -->
    %endif
    
    %if self.has_accessible_datasets and not simple:
        ${render_compression_types_help( comptypes )}
    %endif
    %if not has_accessible_folders:
        The data library '${library.name}' does not contain any datasets that you can access.
    %endif
</%def>
