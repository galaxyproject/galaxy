<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% from galaxy.web.base.controller import tool_shed_encode, tool_shed_decode %>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        <a class="action-button" href="${h.url_for( controller='admin', action='manage_tool_shed_repository', id=trans.security.encode_id( repository.id ) )}">Manage repository</a>
        <a class="action-button" href="${h.url_for( controller='admin', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get updates</a>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Installed tool shed repository '${repository.name}'</div>
    <div class="toolFormBody">

        %if tool_dicts:
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%">
                        <td><b>Tools</b></td>
                    </tr>
                </table>
            </div>
            <div class="form-row">
                <table class="grid">
                    <tr>
                        <td><b>name</b></td>
                        <td><b>description</b></td>
                        <td><b>version</b></td>
                        <td><b>requirements</b></td>
                    </tr>
                    %for tool_dict in tool_dicts:
                        <tr>
                            <td>${tool_dict[ 'name' ]}</div>
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
        %if workflow_dicts:
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%">
                        <td><b>Workflows</b></td>
                    </tr>
                </table>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <table class="grid">
                    <tr>
                        <td><b>name</b></td>
                        <td><b>steps</b></td>
                        <td><b>format-version</b></td>
                        <td><b>annotation</b></td>
                    </tr>
                    <% index = 0 %>
                    %for wf_dict in workflow_dicts:
                        <%
                            full_path = wf_dict[ 'full_path' ]
                            workflow_dict = wf_dict[ 'workflow_dict' ]
                            workflow_name = workflow_dict[ 'name' ]
                            if 'steps' in workflow_dict:
                                ## Initially steps were not stored in the metadata record.
                                steps = workflow_dict[ 'steps' ]
                            else:
                                steps = []
                            format_version = workflow_dict[ 'format-version' ]
                            annotation = workflow_dict[ 'annotation' ]
                        %>
                        <tr>
                            <td>
                                <div class="menubutton" style="float: left;" id="workflow-${index}-popup">
                                    ${workflow_name}
                                    <div popupmenu="workflow-${index}-popup">
                                        <a class="action-button" href="${h.url_for( controller='workflow', action='import_workflow', local_file=full_path, repository_id=trans.security.encode_id( repository.id ) )}">Import to Galaxy</a>
                                    </div>
                                </div>
                            </td>
                            <td>
                                %if 'steps' in workflow_dict:
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
    </div>
</div>
