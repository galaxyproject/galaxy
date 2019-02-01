<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />

<%def name="browse_files(title_text, directory_path)">
    <script type="text/javascript">
        config.addInitialization(function() {
            console.log("common.mako, browse_files");

            // --- Initialize sample trees
            $("#tree").dynatree({
                title: "${title_text|h}",
                minExpandLevel: 1,
                persist: false,
                checkbox: true,
                selectMode: 3,
                onPostInit: function(isReloading, isError) {
                    // Re-fire onActivate, so the text is updated
                    this.reactivate();
                },
                fx: { height: "toggle", duration: 200 },
                // initAjax is hard to fake, so we pass the children as object array:
                initAjax: {url: "${h.url_for( controller='admin_toolshed', action='open_folder' )}",
                           dataType: "json",
                           data: { folder_path: "${directory_path|h}",
                                   repository_id: "${trans.security.encode_id( repository.id )}" },
                },
                onLazyRead: function(dtnode){
                    dtnode.appendAjax({
                        url: "${h.url_for( controller='admin_toolshed', action='open_folder' )}",
                        dataType: "json",
                        data: { folder_path: dtnode.data.key,
                                repository_id: "${trans.security.encode_id( repository.id )}" },
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
                        selected_value = "${directory_path|h}/";
                    } else {
                        selected_value = dtnode.data.key;
                    };
                    if (selected_value.charAt(selected_value.length-1) != '/') {
                        // Make ajax call
                        $.ajax( {
                            type: "POST",
                            url: "${h.url_for( controller='admin_toolshed', action='get_file_contents' )}",
                            dataType: "json",
                            data: { file_path: selected_value, repository_id: "${trans.security.encode_id( repository.id )}" },
                            success : function( data ) {
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

<%def name="render_dependencies_section( install_resolver_dependencies_check_box, repository_dependencies_check_box, install_tool_dependencies_check_box, containers_dict, revision_label=None, export=False, requirements_status=None )">
    <style type="text/css">
        #dependency_table{ table-layout:fixed;
                           width:100%;
                           overflow-wrap:normal;
                           overflow:hidden;
                           border:0px;
                           word-break:keep-all;
                           word-wrap:break-word;
                           line-break:strict; }
    </style>
    <script type="text/javascript">
         config.addInitialization(function() {
             console.log("common.mako, render_dependencies_section");

             $(".detail-section").hide();
             var hidden = true;
             $(".toggle-detail-section").click(function(e){
                 e.preventDefault();
                 hidden = !hidden;
                 if (hidden === true){
                     $(".toggle-detail-section").text('Display Details');
                 } else{
                     $(".toggle-detail-section").text('Hide Details');
                 }
                 $(".detail-section").toggle();
             })
         });
     </script>
    <%
        from markupsafe import escape
        class RowCounter( object ):
            def __init__( self ):
                self.count = 0
            def increment( self ):
                self.count += 1
            def __str__( self ):
                return str( self.count )

        repository_dependencies_root_folder = containers_dict.get( 'repository_dependencies', None )
        missing_repository_dependencies_root_folder = containers_dict.get( 'missing_repository_dependencies', None )
        tool_dependencies_root_folder = containers_dict.get( 'tool_dependencies', None )
        missing_tool_dependencies_root_folder = containers_dict.get( 'missing_tool_dependencies', None )
        env_settings_heaader_row_displayed = False
        package_header_row_displayed = False
        if revision_label:
            revision_label_str = ' revision <b>%s</b> of ' % escape( str( revision_label ) )
        else:
            revision_label_str = ' '
    %>
    <div class="form-row">
        <p>
            By default Galaxy will install all needed dependencies for${revision_label_str}the repository. See the
            <a target="_blank" href="https://docs.galaxyproject.org/en/master/admin/dependency_resolvers.html">
                dependency resolver documentation
            </a>.
        </p>
        <p>
            You can control how dependencies are installed (this is an advanced option, if in doubt, use the default)
            <button class="toggle-detail-section">
                Display Details
            </button>
        </p>
        <p>
        </p>
     </div>
   %if export:
    <div class="form-row">
        <div class="toolParamHelp" style="clear: both;">
            <p>
                The following additional repositories are required by${revision_label_str}the <b>${repository.name|h}</b> repository and they can be exported as well.
            </p>
        </div>
    </div>
    %endif
    <div style="clear: both"></div>
    <div class="detail-section">
    %if repository_dependencies_root_folder or missing_repository_dependencies_root_folder:
        %if repository_dependencies_check_box:
            <div class="form-row">
                %if export:
                    <label>Export repository dependencies?</label>
                %else:
                    <label>Handle repository dependencies?</label>
                %endif
                ${render_checkbox(repository_dependencies_check_box)}
                <div class="toolParamHelp" style="clear: both;">
                    %if export:
                        Select to export the following additional repositories that are required by this repository.
                    %else:
                        Select to automatically install these additional Tool Shed repositories required by this repository.
                    %endif
                </div>
            </div>
            <div style="clear: both"></div>
        %endif
        %if repository_dependencies_root_folder:
            <div class="form-row">
                <p/>
                <% row_counter = RowCounter() %>
                <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table">
                    ${render_folder( repository_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                </table>
                <div style="clear: both"></div>
            </div>
        %endif
        %if missing_repository_dependencies_root_folder:
            <div class="form-row">
                <p/>
                <% row_counter = RowCounter() %>
                <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table">
                    ${render_folder( missing_repository_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                </table>
                <div style="clear: both"></div>
            </div>
        %endif
    %endif
    %if tool_dependencies_root_folder or missing_tool_dependencies_root_folder:
        %if install_tool_dependencies_check_box is not None:
            <div class="form-row">
                <label>When available, install Tool Shed managed tool dependencies?</label>
                <% disabled = trans.app.config.tool_dependency_dir is None %>
                ${render_checkbox(install_tool_dependencies_check_box, disabled=disabled)}
                <div class="toolParamHelp" style="clear: both;">
                    %if disabled:
                        Set the tool_dependency_dir configuration value in your Galaxy config to automatically handle tool dependencies.
                    %else:
                        Select to automatically handle tool dependencies via Tool Shed.
                    %endif
                </div>
            <div style="clear: both"></div>
        %endif
        %if tool_dependencies_root_folder:
            <div class="form-row">
                <p/>
                <% row_counter = RowCounter() %>
                <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="dependency_table">
                    ${render_folder( tool_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                </table>
                <div style="clear: both"></div>
            </div>
        %endif
        %if missing_tool_dependencies_root_folder:
            <div class="form-row">
                <p/>
                <% row_counter = RowCounter() %>
                <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="dependency_table">
                    ${render_folder( missing_tool_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                </table>
                <div style="clear: both"></div>
            </div>
        %endif
    </div>
    %endif
    <div style="clear: both"></div>
    %if requirements_status and install_resolver_dependencies_check_box:
    <div class="form-row">
        <label>When available, install <a href="https://docs.galaxyproject.org/en/master/admin/conda_faq.html" target="_blank">Conda</a> managed tool dependencies?</label>
        ${render_checkbox(install_resolver_dependencies_check_box)}
        <div class="toolParamHelp" style="clear: both;">
            Select to automatically install tool dependencies via Conda.
        </div>
    </div>
    %endif
    </div>
</%def>

<%def name="render_readme_section( containers_dict )">
    <%
        class RowCounter( object ):
            def __init__( self ):
                self.count = 0
            def increment( self ):
                self.count += 1
            def __str__( self ):
                return str( self.count )

        readme_files_root_folder = containers_dict.get( 'readme_files', None )
    %>
    %if readme_files_root_folder:
        <p/>
        <div class="form-row">
            <% row_counter = RowCounter() %>
            <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table">
                ${render_folder( readme_files_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
            </table>
        </div>
    %endif
</%def>

<%def name="dependency_status_updater()">
    <script type="text/javascript">
        config.addInitialization(function() {
            console.log("common.mako, dependency_status_updater");

            // Tool dependency status updater - used to update the installation status on the Tool Dependencies Grid.
            // Looks for changes in tool dependency installation status using an async request. Keeps calling itself
            // (via setTimeout) until dependency installation status is neither 'Installing' nor 'Building'.
            window.tool_dependency_status_updater = function( dependency_status_list ) {
                // See if there are any items left to track
                var empty = true;
                for ( var item in dependency_status_list ) {
                    //alert( "item" + item.toSource() );
                    //alert( "dependency_status_list[item] " + dependency_status_list[item].toSource() );
                    //alert( "dependency_status_list[item]['status']" + dependency_status_list[item]['status'] );
                    if ( dependency_status_list[item]['status'] != 'Installed' ) {
                        empty = false;
                        break;
                    }
                }
                if ( ! empty ) {
                    setTimeout( function() { 
                        tool_dependency_status_updater_callback( dependency_status_list )
                    }, 3000 );
                }
            };

            var tool_dependency_status_updater_callback = function( dependency_status_list ) {
                var ids = [];
                var status_list = [];
                $.each( dependency_status_list, function( index, dependency_status ) {
                    ids.push( dependency_status[ 'id' ] );
                    status_list.push( dependency_status[ 'status' ] );
                });
                // Make ajax call
                $.ajax( {
                    type: "POST",
                    url: "${h.url_for( controller='admin_toolshed', action='tool_dependency_status_updates' )}",
                    dataType: "json",
                    data: { ids: ids.join( "," ), status_list: status_list.join( "," ) },
                    success : function( data ) {
                        $.each( data, function( index, val ) {
                            // Replace HTML
                            var cell1 = $( "#ToolDependencyStatus-" + val[ 'id' ] );
                            cell1.html( val[ 'html_status' ] );
                            dependency_status_list[ index ] = val;
                        });
                        tool_dependency_status_updater( dependency_status_list );
                    },
                });
            };

        });
    </script>
</%def>

<%def name="repository_installation_status_updater()">
    <script type="text/javascript">
        config.addInitialization(function() {
            console.log("common.mako, repository_installation_status_updater");
            
            // Tool shed repository status updater - used to update the installation status on the Repository Installation Grid.
            // Looks for changes in repository installation status using an async request. Keeps calling itself (via setTimeout) until
            // repository installation status is not one of: 'New', 'Cloning', 'Setting tool versions', 'Installing tool dependencies',
            // 'Loading proprietary datatypes'.
            window.tool_shed_repository_status_updater = function( repository_status_list ) {
                // See if there are any items left to track
                //alert( "repository_status_list start " + repository_status_list.toSource() );
                var empty = true;
                for ( var item in repository_status_list ) {
                    //alert( "item" + item.toSource() );
                    //alert( "repository_status_list[item] " + repository_status_list[item].toSource() );
                    //alert( "repository_status_list[item]['status']" + repository_status_list[item]['status'] );
                    if (repository_status_list[item]['status'] != 'Installed'){
                        empty = false;
                        break;
                    }
                }
                if ( ! empty ) {
                    setTimeout( function() { 
                        tool_shed_repository_status_updater_callback( repository_status_list )
                    }, 3000 );
                }
            };

            var tool_shed_repository_status_updater_callback = function( repository_status_list ) {
                //alert( repository_status_list );
                //alert( repository_status_list.toSource() );
                var ids = [];
                var status_list = [];
                $.each( repository_status_list, function( index, repository_status ) {
                    //alert('repository_status '+ repository_status.toSource() );
                    //alert('id '+ repository_status['id'] );
                    //alert( 'status'+ repository_status['status'] );
                    ids.push( repository_status[ 'id' ] );
                    status_list.push( repository_status[ 'status' ] );
                });
                // Make ajax call
                $.ajax( {
                    type: "POST",
                    url: "${h.url_for( controller='admin_toolshed', action='repository_installation_status_updates' )}",
                    dataType: "json",
                    data: { ids: ids.join( "," ), status_list: status_list.join( "," ) },
                    success : function( data ) {
                        $.each( data, function( index, val ) {
                            // Replace HTML
                            var cell1 = $( "#RepositoryStatus-" + val[ 'id' ] );
                            cell1.html( val[ 'html_status' ] );
                            repository_status_list[ index ] = val;
                        });
                        tool_shed_repository_status_updater( repository_status_list );
                    },
                });
            };
        })
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
            config.addInitialization(function() {
                console.log("common.mako, tool_dependency_installation_updater");
                // Tool dependency installation status updater
                tool_dependency_status_updater( [${ ",".join( [ '{"id" : "%s", "status" : "%s"}' % ( trans.security.encode_id( td.id ), td.status ) for td in query ] ) } ] );
            });
        </script>
    %endif
</%def>

<%def name="repository_installation_updater()">
    <%
        can_update = False
        if query.count():
            for tool_shed_repository in query:
                if tool_shed_repository.status not in [ trans.install_model.ToolShedRepository.installation_status.INSTALLED,
                                                        trans.install_model.ToolShedRepository.installation_status.ERROR,
                                                        trans.install_model.ToolShedRepository.installation_status.DEACTIVATED,
                                                        trans.install_model.ToolShedRepository.installation_status.UNINSTALLED ]:
                    can_update = True
                    break
    %>
    %if can_update:
        <script type="text/javascript">
            config.addInitialization(function() {
                console.log("common.mako, repository_installation_updater");
                // Tool shed repository installation status updater
                tool_shed_repository_status_updater( [${ ",".join( [ '{"id" : "%s", "status" : "%s"}' % ( trans.security.encode_id( tsr.id ), tsr.status ) for tsr in query ] ) } ] );
            });
        </script>
    %endif
</%def>
