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

<%def name="render_tool_dependency_section( install_tool_dependencies_check_box, repo_info_dicts )">
    <% import os %>
    <div class="form-row">
        <div class="toolParamHelp" style="clear: both;">
            <p>
                These tool dependencies can be automatically handled with the installed repository, providing significant benefits, and 
                Galaxy includes various features to manage them.
            </p>
        </div>
    </div>
    <div class="form-row">
        <label>Handle tool dependencies?</label>
        <% disabled = trans.app.config.tool_dependency_dir is None %>
        ${install_tool_dependencies_check_box.get_html( disabled=disabled )}
        <div class="toolParamHelp" style="clear: both;">
            %if disabled:
                Set the tool_dependency_dir configuration value in your universe_wsgi.ini to automatically handle tool dependencies.
            %else:
                Un-check to skip automatic handling of these tool dependencies.
            %endif
        </div>
    </div>
    <div style="clear: both"></div>
    <div class="form-row">
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
        <table class="grid" id="dependency_table">
            <tr><td colspan="4" bgcolor="#D8D8D8"><b>Tool dependencies</b></td></tr>
            <%
                env_settings_heaader_row_displayed = False
                package_header_row_displayed = False
            %>
            %for repo_info_dict in repo_info_dicts:
                %for repository_name, repo_info_tuple in repo_info_dict.items():
                    <% description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, tool_dependencies = repo_info_tuple %>
                    %if tool_dependencies:
                        <%
                            # See if tool dependencies are packages, environment settings or both.
                            contains_packages = False
                            for k in tool_dependencies.keys():
                                if k != 'set_environment':
                                    contains_packages = True
                                    break
                            contains_env_settings = 'set_environment' in tool_dependencies.keys()
                        %>
                        %if contains_packages:
                            %if not package_header_row_displayed:
                                <%
                                    info_str = "Each of these packages may require their own build requirements (e.g., CMake, g++, etc).  "
                                    info_str += "Galaxy will not attempt to install these build requirements, so tool dependency installation "
                                    info_str += "may partially fail if any are missing from your environment, but the repository and all of it's "
                                    info_str += "contents will be installed.  You can install the missing build requirements and have Galaxy attempt "
                                    info_str += "to install the packages again if tool dependency installation fails in any way."
                                %>
                                </tr><td bgcolor="#FFFFCC" colspan="4">${info_str}</td></tr>
                                <tr>
                                    <th>Name</th>
                                    <th>Version</th>
                                    <th>Type</th>
                                    <th>Install directory</th>
                                </tr>
                                <% package_header_row_displayed = True %>
                            %endif
                            %for dependency_key, requirements_dict in tool_dependencies.items():
                                %if dependency_key not in [ 'set_environment' ]:
                                    <%
                                        name = requirements_dict[ 'name' ]
                                        version = requirements_dict[ 'version' ]
                                        type = requirements_dict[ 'type' ]
                                        install_dir = os.path.join( trans.app.config.tool_dependency_dir,
                                                                    name,
                                                                    version,
                                                                    repository_owner,
                                                                    repository_name,
                                                                    changeset_revision )
                                        tool_dependency_readme_text = requirements_dict.get( 'readme', None )
                                    %>
                                    %if not os.path.exists( install_dir ):
                                        <tr>
                                            <td>${name}</td>
                                            <td>${version}</td>
                                            <td>${type}</td>
                                            <td>${install_dir}</td>
                                        </tr>
                                        %if tool_dependency_readme_text:
                                            <tr><td colspan="4" bgcolor="#FFFFCC">${name} ${version} requirements and installation information</td></tr>
                                            <tr><td colspan="4"><pre>${tool_dependency_readme_text}</pre></td></tr>
                                        %endif
                                    %endif
                                %endif
                            %endfor
                        %endif
                        %if contains_env_settings:
                            <% environment_settings = tool_dependencies[ 'set_environment' ] %>
                            %if not env_settings_heaader_row_displayed:
                                <%
                                    info_str = "Each of these environment settings will be defined in a file named env.sh in the installation directory."
                                %>
                                </tr><td bgcolor="#FFFFCC" colspan="4">${info_str}</td></tr>
                                <tr>
                                    <th>Name</th>
                                    <th>Type</th>
                                    <th colspan="2">Install directory for environment shell file</th>
                                </tr>
                                <% env_settings_heaader_row_displayed = True %>
                            %endif
                            %for environment_setting_dict in environment_settings:
                                <%
                                    name = environment_setting_dict[ 'name' ]
                                    type = environment_setting_dict[ 'type' ]
                                    install_dir = os.path.join( trans.app.config.tool_dependency_dir,
                                                                'environment_settings',
                                                                name,
                                                                repository_owner,
                                                                repository_name,
                                                                changeset_revision )
                                %>
                                %if not os.path.exists( install_dir ):
                                    <tr>
                                        <td>${name}</td>
                                        <td>${type}</td>
                                        <td colspan="2">${install_dir}</td>
                                    </tr>
                                %endif
                            %endfor
                        %endif
                    %endif
                %endfor
            %endfor
        </table>
        <div style="clear: both"></div>
    </div>
</%def>

<%def name="dependency_status_updater()">
    <script type="text/javascript">
        // Tool dependency status updater - used to update the installation status on the Tool Dependencies Grid. 
        // Looks for changes in tool dependency installation status using an async request. Keeps calling itself 
        // (via setTimeout) until dependency installation status is neither 'Installing' nor 'Building'.
        var tool_dependency_status_updater = function( dependency_status_list ) {
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
                setTimeout( function() { tool_dependency_status_updater_callback( dependency_status_list ) }, 3000 );
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
                error: function() {
                    alert( "tool_dependency_status_updater_callback failed..." );
                }
            });
        };
    </script>
</%def>

<%def name="repository_installation_status_updater()">
    <script type="text/javascript">
        // Tool shed repository status updater - used to update the installation status on the Repository Installation Grid. 
        // Looks for changes in repository installation status using an async request. Keeps calling itself (via setTimeout) until
        // repository installation status is not one of: 'New', 'Cloning', 'Setting tool versions', 'Installing tool dependencies',
        // 'Loading proprietary datatypes'.
        var tool_shed_repository_status_updater = function( repository_status_list ) {
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
                setTimeout( function() { tool_shed_repository_status_updater_callback( repository_status_list ) }, 3000 );
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
                error: function() {
                    alert( "tool_shed_repository_status_updater_callback failed..." );
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
            tool_dependency_status_updater( [${ ",".join( [ '{"id" : "%s", "status" : "%s"}' % ( trans.security.encode_id( td.id ), td.status ) for td in query ] ) } ] );
        </script>
    %endif
</%def>

<%def name="repository_installation_updater()">
    <%
        can_update = False
        if query.count():
            for tool_shed_repository in query:
                if tool_shed_repository.status not in [ trans.model.ToolShedRepository.installation_status.INSTALLED,
                                                        trans.model.ToolShedRepository.installation_status.ERROR,
                                                        trans.model.ToolShedRepository.installation_status.DEACTIVATED,
                                                        trans.model.ToolShedRepository.installation_status.UNINSTALLED ]:
                    can_update = True
                    break
    %>
    %if can_update:
        <script type="text/javascript">
            // Tool shed repository installation status updater
            tool_shed_repository_status_updater( [${ ",".join( [ '{"id" : "%s", "status" : "%s"}' % ( trans.security.encode_id( tsr.id ), tsr.status ) for tsr in query ] ) } ] );
        </script>
    %endif
</%def>
