<%def name="common_javascripts(repository)">
    <script type="text/javascript">
        $(function(){
            $("#tree").ajaxComplete(function(event, XMLHttpRequest, ajaxOptions) {
                _log("debug", "ajaxComplete: %o", this); // dom element listening
            });
            // --- Initialize sample trees
            $("#tree").dynatree({
                title: "${repository.name}",
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
                initAjax: {url: "${h.url_for( controller='repository', action='open_folder' )}",
                           dataType: "json", 
                           data: { repository_id: "${trans.security.encode_id( repository.id )}", key: "${repository.repo_path}" },
                },
                onLazyRead: function(dtnode){
                    dtnode.appendAjax({
                        url: "${h.url_for( controller='repository', action='open_folder' )}", 
                        dataType: "json",
                        data: { repository_id: "${trans.security.encode_id( repository.id )}", key: dtnode.data.key },
                    });
                },
                onSelect: function(select, dtnode) {
                    // Display list of selected nodes
                    var selNodes = dtnode.tree.getSelectedNodes();
                    // convert to title/key array
                    var selKeys = $.map(selNodes, function(node) {
                        return node.data.key;
                    });
                    if (document.forms["select_files_to_delete"]) {
                        // The following is used only ~/templates/webapps/community/repository/browse_repository.mako.
                        document.select_files_to_delete.selected_files_to_delete.value = selKeys.join(",");
                    }
                    // The following is used only in ~/templates/webapps/community/repository/upload.mako.
                    if (document.forms["upload_form"]) {
                        document.upload_form.upload_point.value = selKeys.slice(-1);
                    }
                },
                onActivate: function(dtnode) {
                    var cell = $("#file_contents");
                    var selected_value;
                     if (dtnode.data.key == 'root') {
                        selected_value = "${repository.repo_path}/";
                    } else {
                        selected_value = dtnode.data.key;
                    };
                    if (selected_value.charAt(selected_value.length-1) != '/') {
                        // Make ajax call
                        $.ajax( {
                            type: "POST",
                            url: "${h.url_for( controller='repository', action='get_file_contents' )}",
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

<%def name="render_clone_str( repository )">
    <%
        from galaxy.webapps.community.controllers.common import generate_clone_url
        clone_str = generate_clone_url( trans, trans.security.encode_id( repository.id ) )
    %>
    hg clone <a href="${clone_str}">${clone_str}</a>
</%def>

<%def name="render_repository_tools_and_workflows( metadata, can_set_metadata=False, display_for_install=False )">
    %if metadata or can_set_metadata:
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Preview tools and inspect metadata by tool version</div>
            <div class="toolFormBody">
                %if metadata:
                    %if 'tools' in metadata:
                        <div class="form-row">
                            <table width="100%">
                                <tr bgcolor="#D8D8D8" width="100%">
                                    <td><b>Tools</b><i> - click the name to preview the tool and use the pop-up menu to inspect all metadata</i></td>
                                </tr>
                            </table>
                        </div>
                        <div class="form-row">
                            <% tool_dicts = metadata[ 'tools' ] %>
                            <table class="grid">
                                <tr>
                                    <td><b>name</b></td>
                                    <td><b>description</b></td>
                                    <td><b>version</b></td>
                                    <td><b>requirements</b></td>
                                </tr>
                                %for tool_dict in tool_dicts:
                                    <tr>
                                        <td>
                                            <div style="float: left; margin-left: 1px;" class="menubutton split popup" id="tool-${tool_dict[ 'id' ].replace( ' ', '_' )}-popup">
                                                <a class="view-info" href="${h.url_for( controller='repository', action='display_tool', repository_id=trans.security.encode_id( repository.id ), tool_config=tool_dict[ 'tool_config' ], changeset_revision=changeset_revision, display_for_install=display_for_install )}">
                                                    ${tool_dict[ 'name' ]}
                                                </a>
                                            </div>
                                            <div popupmenu="tool-${tool_dict[ 'id' ].replace( ' ', '_' )}-popup">
                                                <a class="action-button" href="${h.url_for( controller='repository', action='view_tool_metadata', repository_id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision, tool_id=tool_dict[ 'id' ], display_for_install=display_for_install )}">View tool metadata</a>
                                            </div>
                                        </td>
                                        <td>${tool_dict[ 'description' ]}</td>
                                        <td>${tool_dict[ 'version' ]}</td>
                                        <td>
                                            <%
                                                if 'requirements' in tool_dict:
                                                    requirements = tool_dict[ 'requirements' ]
                                                else:
                                                    requirements = None
                                            %>
                                            %if requirements:
                                                <%
                                                    requirements_str = ''
                                                    for requirement_dict in tool_dict[ 'requirements' ]:
                                                        requirements_str += '%s (%s), ' % ( requirement_dict[ 'name' ], requirement_dict[ 'type' ] )
                                                    requirements_str = requirements_str.rstrip( ', ' )
                                                %>
                                                ${requirements_str}
                                            %else:
                                                none
                                            %endif
                                        </td>
                                    </tr>
                                %endfor
                            </table>
                        </div>
                        <div style="clear: both"></div>
                    %endif
                    %if 'workflows' in metadata:
                        <div class="form-row">
                            <table width="100%">
                                <tr bgcolor="#D8D8D8" width="100%">
                                    <td><b>Workflows</b></td>
                                </tr>
                            </table>
                        </div>
                        <div style="clear: both"></div>
                        <div class="form-row">
                            <% workflow_dicts = metadata[ 'workflows' ] %>
                            <table class="grid">
                                <tr>
                                    <td><b>name</b></td>
                                    <td><b>format-version</b></td>
                                    <td><b>annotation</b></td>
                                </tr>
                                %for workflow_dict in workflow_dicts:
                                    <tr>
                                        <td>${workflow_dict[ 'name' ]}</td>
                                        <td>${workflow_dict[ 'format-version' ]}</td>
                                        <td>${workflow_dict[ 'annotation' ]}</td>
                                    </tr>
                                %endfor
                            </table>
                        </div>
                        <div style="clear: both"></div>
                    %endif
                %endif
                %if can_set_metadata:
                    <form name="set_metadata" action="${h.url_for( controller='repository', action='set_metadata', id=trans.security.encode_id( repository.id ), ctx_str=changeset_revision )}" method="post">
                        <div class="form-row">
                            <div style="float: left; width: 250px; margin-right: 10px;">
                                <input type="submit" name="set_metadata_button" value="Reset metadata"/>
                            </div>
                            <div class="toolParamHelp" style="clear: both;">
                                Inspect the repository and reset the above attributes for the repository tip.
                            </div>
                        </div>
                    </form>
                %endif
            </div>
        </div>
    %endif
</%def>
