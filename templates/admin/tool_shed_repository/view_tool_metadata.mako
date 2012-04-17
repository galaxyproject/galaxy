<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">Browse repository</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}">Manage repository</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get updates</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or Uninstall</a>
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
            %if tool:
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
            <%
                if 'requirements' in metadata:
                    requirements = metadata[ 'requirements' ]
                else:
                    requirements = None
            %>
            %if requirements:
                <%
                    requirements_str = ''
                    for requirement_dict in metadata[ 'requirements' ]:
                        requirements_str += '%s (%s), ' % ( requirement_dict[ 'name' ], requirement_dict[ 'type' ] )
                    requirements_str = requirements_str.rstrip( ', ' )
                %>
                <div class="form-row">
                    <label>Requirements:</label>
                    ${requirements_str}
                    <div style="clear: both"></div>
                </div>
            %endif
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
            %endif
        </div>
    </div>
%endif
