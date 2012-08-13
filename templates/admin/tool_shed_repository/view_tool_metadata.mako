<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">Browse repository files</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}">Manage repository</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get updates</a>
        %if repository.tool_dependencies:
            <% tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in repository.tool_dependencies ] %>
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', tool_dependency_ids=tool_dependency_ids )}">Manage tool dependencies</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or uninstall repository</a>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if metadata:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">${metadata[ 'name' ]} tool metadata</div>
        <div class="toolFormBody">
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%"><td><b>Miscellaneous</td></tr>
                </table>
            </div>
            <div class="form-row">
                <label>Name:</label>
                ${metadata[ 'name' ]}
                <div style="clear: both"></div>
            </div>
            %if 'description' in metadata:
                <div class="form-row">
                    <label>Description:</label>
                    ${metadata[ 'description' ]}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'id' in metadata:
                <div class="form-row">
                    <label>Id:</label>
                    ${metadata[ 'id' ]}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'guid' in metadata:
                <div class="form-row">
                    <label>Guid:</label>
                    ${metadata[ 'guid' ]}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'version' in metadata:
                <div class="form-row">
                    <label>Version:</label>
                    ${metadata[ 'version' ]}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'version_string_cmd' in metadata:
                <div class="form-row">
                    <label>Version command string:</label>
                    ${metadata[ 'version_string_cmd' ]}
                    <div style="clear: both"></div>
                </div>
            %endif
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%"><td><b>Version lineage of this tool (guids ordered most recent to oldest)</td></tr>
                </table>
            </div>
            <div class="form-row">
                %if tool_lineage:
                    <table class="grid">
                        %for guid in tool_lineage:
                            <tr>
                                <td>
                                    %if guid == metadata[ 'guid' ]:
                                        ${guid} <b>(this tool)</b>
                                    %else:
                                        ${guid}
                                    %endif
                                </td>
                            </tr>
                        %endfor
                    </table>
                %else:
                    No tool versions are defined for this tool so it is critical that you <b>Set tool versions</b> from the <b>Manage repository</b> page.
                %endif
            </div>
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%"><td><b>Requirements (dependencies defined in the &lt;requirements&gt; tag set)</td></tr>
                </table>
            </div>
            <%
                if 'requirements' in metadata:
                    requirements = metadata[ 'requirements' ]
                else:
                    requirements = None
            %>
            %if requirements:
                <div class="form-row">
                    <label>Requirements:</label>
                    <table class="grid">
                        <tr>
                            <td><b>name</b></td>
                            <td><b>version</b></td>
                            <td><b>type</b></td>
                        </tr>
                        %for requirement_dict in requirements:
                            <%
                                requirement_name = requirement_dict[ 'name' ] or 'not provided'
                                requirement_version = requirement_dict[ 'version' ] or 'not provided'
                                requirement_type = requirement_dict[ 'type' ] or 'not provided'
                            %>
                            <tr>
                                <td>${requirement_name}</td>
                                <td>${requirement_version}</td>
                                <td>${requirement_type}</td>
                            </tr>
                        %endfor
                    </table>
                    <div style="clear: both"></div>
                </div>
            %else:
                <div class="form-row">
                    No requirements defined
                </div>
            %endif
            %if tool:
                <div class="form-row">
                    <table width="100%">
                        <tr bgcolor="#D8D8D8" width="100%"><td><b>Additional information about this tool</td></tr>
                    </table>
                </div>
                <div class="form-row">
                    <label>Command:</label>
                    <pre>${tool.command}</pre>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Interpreter:</label>
                    ${tool.interpreter}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Is multi-byte:</label>
                    ${tool.is_multi_byte}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Forces a history refresh:</label>
                    ${tool.force_history_refresh}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Parallelism:</label>
                    ${tool.parallelism}
                    <div style="clear: both"></div>
                </div>
            %endif
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%"><td><b>Functional tests</td></tr>
                </table>
            </div>
            <%
                if 'tests' in metadata:
                    tests = metadata[ 'tests' ]
                else:
                    tests = None
            %>
            %if tests:
                <div class="form-row">
                    <label>Functional tests:</label></td>
                    <table class="grid">
                        <tr>
                            <td><b>name</b></td>
                            <td><b>inputs</b></td>
                            <td><b>outputs</b></td>
                            <td><b>required files</b></td>
                        </tr>
                        %for test_dict in tests:
                            <%
                                inputs = test_dict[ 'inputs' ]
                                outputs = test_dict[ 'outputs' ]
                                required_files = test_dict[ 'required_files' ]
                            %>
                            <tr>
                                <td>${test_dict[ 'name' ]}</td>
                                <td>
                                    %for input in inputs:
                                        <b>${input[0]}:</b> ${input[1]}<br/>
                                    %endfor
                                </td>
                                <td>
                                    %for output in outputs:
                                        <b>${output[0]}:</b> ${output[1]}<br/>
                                    %endfor
                                </td>
                                <td>
                                    %for required_file in required_files:
                                        ${required_file}<br/>
                                    %endfor
                                </td>
                            </tr>
                        %endfor
                    </table>
                </div>
            %else:
                <div class="form-row">
                    No functional tests defined
                </div>
            %endif
        </div>
    </div>
%endif
