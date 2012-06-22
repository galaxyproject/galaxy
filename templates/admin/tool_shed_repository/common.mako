<%def name="browse_files(title_text, directory_path)">
    <script type="text/javascript">
        $(function(){
            $("#tree").ajaxComplete(function(event, XMLHttpRequest, ajaxOptions) {
                _log("debug", "ajaxComplete: %o", this); // dom element listening
            });
            // --- Initialize sample trees
            $("#tree").dynatree({
                title: "${title_text}",
                rootVisible: true,
                minExpandLevel: 0, // 1: root node is not collapsible
                persist: false,
                checkbox: true,
                selectMode: 3,
                onPostInit: function(isReloading, isError) {
                    //alert("reloading: "+isReloading+", error:"+isError);
                    logMsg("onPostInit(%o, %o) - %o", isReloading, isError, this);
                    // Re-fire onActivate, so the text is updated
                    this.reactivate();
                }, 
                fx: { height: "toggle", duration: 200 },
                // initAjax is hard to fake, so we pass the children as object array:
                initAjax: {url: "${h.url_for( controller='admin_toolshed', action='open_folder' )}",
                           dataType: "json", 
                           data: { folder_path: "${directory_path}" },
                },
                onLazyRead: function(dtnode){
                    dtnode.appendAjax({
                        url: "${h.url_for( controller='admin_toolshed', action='open_folder' )}", 
                        dataType: "json",
                        data: { folder_path: dtnode.data.key },
                    });
                },
                onSelect: function(select, dtnode) {
                    // Display list of selected nodes
                    var selNodes = dtnode.tree.getSelectedNodes();
                    // convert to title/key array
                    var selKeys = $.map(selNodes, function(node) {
                        return node.data.key;
                    });
                },
                onActivate: function(dtnode) {
                    var cell = $("#file_contents");
                    var selected_value;
                     if (dtnode.data.key == 'root') {
                        selected_value = "${directory_path}/";
                    } else {
                        selected_value = dtnode.data.key;
                    };
                    if (selected_value.charAt(selected_value.length-1) != '/') {
                        // Make ajax call
                        $.ajax( {
                            type: "POST",
                            url: "${h.url_for( controller='admin_toolshed', action='get_file_contents' )}",
                            dataType: "json",
                            data: { file_path: selected_value },
                            success : function ( data ) {
                                cell.html( '<label>'+data+'</label>' )
                            }
                        });
                    } else {
                        cell.html( '' );
                    };
                },
            });
        });
    </script>
</%def>

<%def name="dependency_status_updater()">
    <script type="text/javascript">

        // Tool dependency status updater - used to update the installation status on the Tool Dependencies grid. 
        // Looks for changes in tool dependency installation status using an async request. Keeps calling itself 
        // (via setTimeout) until dependency installation status is neither 'Installing' nor 'Building'.
        var tool_dependency_status_updater = function ( dependency_status_list ) {
            // See if there are any items left to track
            var empty = true;
            for ( i in dependency_status_list ) {
                empty = false;
                break;
            }
            if ( ! empty ) {
                setTimeout( function() { tool_dependency_status_updater_callback( dependency_status_list ) }, 3000 );
            }
        };
        var tool_dependency_status_updater_callback = function ( dependency_status_list ) {
            var ids = []
            var status_list = []
            $.each( dependency_status_list, function ( id, dependency_status ) {
                ids.push( id );
                status_list.push( dependency_status );
            });
            // Make ajax call
            $.ajax( {
                type: "POST",
                url: "${h.url_for( controller='admin_toolshed', action='tool_dependency_status_updates' )}",
                dataType: "json",
                data: { ids: ids.join( "," ), status_list: status_list.join( "," ) },
                success : function ( data ) {
                    $.each( data, function( id, val ) {
                        // Replace HTML
                        var cell1 = $("#ToolDependencyStatus-" + id);
                        cell1.html( val.html_status );
                        dependency_status_list[ id ] = val.status;
                    });
                    tool_dependency_status_updater( dependency_status_list ); 
                },
                error: function() {
                    tool_dependency_status_updater( dependency_status_list ); 
                }
            });
        };
    </script>
</%def>

<%def name="tool_dependency_installation_updater()">
    <% 
        can_update = False
        if query.count():
            # Get the first tool dependency to get to the tool shed repository.
            tool_dependency = query[0]
            tool_shed_repository = tool_dependency.tool_shed_repository
            can_update = tool_shed_repository.tool_dependencies_being_installed or tool_shed_repository.missing_tool_dependencies
    %>
    %if can_update:
        <script type="text/javascript">
            // Tool dependency installation status updater
            tool_dependency_status_updater( {${ ",".join( [ '"%s" : "%s"' % ( trans.security.encode_id( td.id ), td.status ) for td in query ] ) }});
        </script>
    %endif
</%def>

<%def name="repository_installation_status_updater()">
    <script type="text/javascript">

        // Tool shed repository status updater - used to update the installation status on the repository_installation.mako template. 
        // Looks for changes in repository installation status using an async request. Keeps calling itself (via setTimeout) until
        // repository installation status is neither 'cloning', 'cloned' nor 'installing tool dependencies'.
        var tool_shed_repository_status_updater = function ( repository_status_list ) {
            // See if there are any items left to track
            var empty = true;
            for ( i in repository_status_list ) {
                empty = false;
                break;
            }
            if ( ! empty ) {
                setTimeout( function() { tool_shed_repository_status_updater_callback( repository_status_list ) }, 3000 );
            }
        };
        var tool_shed_repository_status_updater_callback = function ( repository_status_list ) {
            var ids = []
            var status_list = []
            $.each( repository_status_list, function ( id, repository_status ) {
                ids.push( id );
                status_list.push( repository_status );
            });
            // Make ajax call
            $.ajax( {
                type: "POST",
                url: "${h.url_for( controller='admin_toolshed', action='repository_installation_status_updates' )}",
                dataType: "json",
                data: { id: ids[0], status_list: status_list.join( "," ) },
                success : function ( data ) {
                    $.each( data, function( id, val ) {
                        // Replace HTML
                        var cell1 = $("#RepositoryStatus-" + id);
                        cell1.html( val.html_status );
                        repository_status_list[ id ] = val.status;
                    });
                    tool_shed_repository_status_updater( repository_status_list ); 
                },
                error: function() {
                    tool_shed_repository_status_updater( repository_status_list ); 
                }
            });
        };
    </script>
</%def>

<%def name="repository_installation_updater()">
    <%
        can_update = True
        if tool_shed_repository:
            can_update = tool_shed_repository.status not in [ trans.model.ToolShedRepository.installation_status.INSTALLED,
                                                              trans.model.ToolShedRepository.installation_status.ERROR,
                                                              trans.model.ToolShedRepository.installation_status.UNINSTALLED ]
    %>
    %if can_update:
        <script type="text/javascript">
            // Tool shed repository installation status updater
            repository_installation_status_updater( {${ ",".join( [ '"%s" : "%s"' % ( trans.security.encode_id( repository.id ), repository.status ) for repository in query ] ) }});
        </script>
    %endif
</%def>

