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

<%def name="render_repository_items( repository_metadata_id, metadata, can_set_metadata=False, webapp='community' )">
    <% from galaxy.webapps.community.controllers.common import encode, decode %>
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
                                    <td><b>Valid tools</b><i> - click the name to preview the tool and use the pop-up menu to inspect all metadata</i></td>
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
                                %for index, tool_dict in enumerate( tool_dicts ):
                                    <tr>
                                        <td>
                                            <div style="float:left;" class="menubutton split popup" id="tool-${index}-popup">
                                                <a class="view-info" href="${h.url_for( controller='repository', action='display_tool', repository_id=trans.security.encode_id( repository.id ), tool_config=tool_dict[ 'tool_config' ], changeset_revision=changeset_revision, webapp=webapp )}">${tool_dict[ 'name' ]}</a>
                                            </div>
                                            <div popupmenu="tool-${index}-popup">
                                                <a class="action-button" href="${h.url_for( controller='repository', action='view_tool_metadata', repository_id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision, tool_id=tool_dict[ 'id' ], webapp=webapp )}">View tool metadata</a>
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
                    %if 'invalid_tools' in metadata:
                        <div class="form-row">
                            <table width="100%">
                                <tr bgcolor="#D8D8D8" width="100%">
                                    <td><b>Invalid tools</b><i> - click the tool config file name to see why the tool is invalid</i></td>
                                </tr>
                            </table>
                        </div>
                        <div style="clear: both"></div>
                        <div class="form-row">
                            <% invalid_tool_configs = metadata[ 'invalid_tools' ] %>
                            <table class="grid">
                                %for invalid_tool_config in invalid_tool_configs:
                                    <tr>
                                        <td>
                                            <a class="view-info" href="${h.url_for( controller='repository', action='load_invalid_tool', repository_id=trans.security.encode_id( repository.id ), tool_config=invalid_tool_config, changeset_revision=changeset_revision, webapp=webapp )}">
                                                ${invalid_tool_config}
                                            </a>
                                        </td>
                                    </tr>
                                %endfor
                            </table>
                        </div>
                        <div style="clear: both"></div>
                    %endif
                    %if 'workflows' in metadata:
                        ## metadata[ 'workflows' ] is a list of tuples where each contained tuple is
                        ## [ <relative path to the .ga file in the repository>, <exported workflow dict> ]
                        <div class="form-row">
                            <table width="100%">
                                <tr bgcolor="#D8D8D8" width="100%">
                                    <td><b>Workflows</b></td>
                                </tr>
                            </table>
                        </div>
                        <div style="clear: both"></div>
                        <div class="form-row">
                            <% workflow_tups = metadata[ 'workflows' ] %>
                            <table class="grid">
                                <tr>
                                    <td><b>name</b></td>
                                    <td><b>steps</b></td>
                                    <td><b>format-version</b></td>
                                    <td><b>annotation</b></td>
                                </tr>
                                %for workflow_tup in workflow_tups:
                                    <%
                                        relative_path = workflow_tup[0]
                                        workflow_dict = workflow_tup[1]
                                        workflow_name = workflow_dict[ 'name' ]
                                        ## Initially steps were not stored in the metadata record.
                                        steps = workflow_dict.get( 'steps', [] )
                                        format_version = workflow_dict[ 'format-version' ]
                                        annotation = workflow_dict[ 'annotation' ]
                                    %>
                                    <tr>
                                        <td>
                                            <a href="${h.url_for( controller='workflow', action='view_workflow', repository_metadata_id=repository_metadata_id, workflow_name=encode( workflow_name ), webapp=webapp )}">${workflow_name}</a>
                                        </td>
                                        <td>
                                            %if steps:
                                                ${len( steps )}
                                            %else:
                                                unknown
                                            %endif
                                        </td>
                                        <td>${format_version}</td>
                                        <td>${annotation}</td>
                                    </tr>
                                %endfor
                            </table>
                        </div>
                        <div style="clear: both"></div>
                    %endif
                    %if 'datatypes' in metadata:
                        <div class="form-row">
                            <table width="100%">
                                <tr bgcolor="#D8D8D8" width="100%">
                                    <td><b>Data types</b></td>
                                </tr>
                            </table>
                        </div>
                        <div style="clear: both"></div>
                        <div class="form-row">
                            <% datatypes_dicts = metadata[ 'datatypes' ] %>
                            <table class="grid">
                                <tr>
                                    <td><b>extension</b></td>
                                    <td><b>type</b></td>
                                    <td><b>mimetype</b></td>
                                    <td><b>subclass</b></td>
                                </tr>
                                %for datatypes_dict in datatypes_dicts:
                                    <%
                                        extension = datatypes_dict.get( 'extension', '&nbsp;' )
                                        dtype = datatypes_dict.get( 'dtype', '&nbsp;' )
                                        mimetype = datatypes_dict.get( 'mimetype', '&nbsp;' )
                                        subclass = datatypes_dict.get( 'subclass', '&nbsp;' )
                                    %>
                                    <tr>
                                        <td>${extension}</td>
                                        <td>${dtype}</td>
                                        <td>${mimetype}</td>
                                        <td>${subclass}</td>
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
