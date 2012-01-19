<%def name="render_metadata( repository, can_reset_metadata=False )">
    <div class="toolForm">
        <div class="toolFormTitle">Repository contents</div>
        <div class="toolFormBody">
            <% metadata = repository.metadata %>
            %if metadata:
                %if 'tools' in metadata:
                    <div class="form-row">
                        <table width="100%">
                            <tr bgcolor="#D8D8D8" width="100%">
                                <td><b>Tools</b><i> - click the name to view tool related information</i></td>
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
                                        <a class="view-info" href="${h.url_for( controller='admin_toolshed', action='view_tool_metadata', repository_id=trans.security.encode_id( repository.id ), tool_id=tool_dict[ 'id' ] )}">
                                            ${tool_dict[ 'name' ]}
                                        </a>
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
                    ## metadata[ 'workflows' ] is a list of tuples where each contained tuple is
                    ## [ <relative path to the .ga file in the repository>, <exported workflow dict> ]
                    <div class="form-row">
                        <table width="100%">
                            <tr bgcolor="#D8D8D8" width="100%">
                                <td><b>Workflows</b><i> - click the name to import</i></td>
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
                            <% index = 0 %>
                            %for workflow_tup in workflow_tups:
                                <%
                                    import os.path
                                    relative_path = workflow_tup[ 0 ]
                                    full_path = os.path.abspath( relative_path )
                                    workflow_dict = workflow_tup[ 1 ]
                                    workflow_name = workflow_dict[ 'name' ]
                                    ## Initially steps were not stored in the metadata record.
                                    steps = workflow_dict.get( 'steps', [] )
                                    format_version = workflow_dict[ 'format-version' ]
                                    annotation = workflow_dict[ 'annotation' ]
                                %>
                                <tr>
                                    <td>
                                        <div class="menubutton" style="float: left;" id="workflow-${index}-popup">
                                            ${workflow_name}
                                            <div popupmenu="workflow-${index}-popup">
                                                <a class="action-button" href="${h.url_for( controller='workflow', action='import_workflow', installed_repository_file=full_path, repository_id=trans.security.encode_id( repository.id ) )}">Import to Galaxy</a>
                                            </div>
                                        </div>
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
                                <% index += 1 %>
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
            %if can_reset_metadata:
                <form name="set_metadata" action="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post">
                    <div class="form-row">
                        <div style="float: left; width: 250px; margin-right: 10px;">
                            <input type="submit" name="set_metadata_button" value="Reset metadata"/>
                        </div>
                        <div class="toolParamHelp" style="clear: both;">
                            Inspect the repository and reset the above attributes.
                        </div>
                    </div>
                </form>
            %endif
        </div>
    </div>
</%def>
