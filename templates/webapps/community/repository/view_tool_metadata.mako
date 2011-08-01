<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    from urllib import quote_plus
    is_admin = trans.user_is_admin()
    is_new = repository.is_new
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_upload = can_push
    can_browse_contents = not is_new
    can_rate = repository.user != trans.user
    can_manage = is_admin or repository.user == trans.user
    can_view_change_log = not is_new
    if can_push:
        browse_label = 'Browse or delete repository files'
    else:
        browse_label = 'Browse repository files'
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<br/><br/>
<ul class="manage-table-actions">
    %if is_new:
        <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
    %else:
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            %if can_manage:
                <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ) )}">Manage repository</a>
            %else:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ) )}">View repository</a>
            %endif
            %if can_upload:
                <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
            %endif
            %if can_view_change_log:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">View change log</a>
            %endif
            %if can_browse_contents:
                <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">${browse_label}</a>
            %endif
            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='gz' )}">Download as a .tar.gz file</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='bz2' )}">Download as a .tar.bz2 file</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='zip' )}">Download as a zip file</a>
        </div>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${repository.name}</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Clone this repository:</label>
            ${render_clone_str( repository )}
        </div>
    </div>
</div>
%if metadata:
## "{"tools": 
## [{"description": "data on any column using simple expressions", 
##   "id": "Filter1", 
##   "name": "Filter", 
##   "requirements": [], 
##   "tests": [{
##               "inputs": [["input", "1.bed", {"children": [], "value": "1.bed"}], ["cond", "c1=='chr22'", {"children": [], "value": "c1=='chr22'"}]], "name": "Test-1", 
##               "outputs": [["out_file1", "filter1_test1.bed", {"compare": "diff", "delta": 10000, "extra_files": [], "lines_diff": 0, "sort": false}]], 
##               "required_files": [["1.bed", {"children": [], "value": "1.bed"}]]}, {"inputs": [["input", "7.bed", {"children": [], "value": "7.bed"}], ["cond", "c1=='chr1' and c3-c2>=2000 and c6=='+'", {"children": [], "value": "c1=='chr1' and c3-c2>=2000 and c6=='+'"}]], "name": "Test-2", "outputs": [["out_file1", "filter1_test2.bed", {"compare": "diff", "delta": 10000, "extra_files": [], "lines_diff": 0, "sort": false}]], "required_files": [["7.bed", {"children": [], "value": "7.bed"}]]}], "tool_config": "database/community_files/000/repo_1/filtering.xml", "version": "1.0.1", "version_string_cmd": null}], "workflows": [{"a_galaxy_workflow": "true", "annotation": "", "format-version": "0.1", "name": "Workflow constructed from history 'Unnamed history'", "steps": {"0": {"annotation": "", "id": 0, "input_connections": {}, "inputs": [{"description": "", "name": "Input Dataset"}], "name": "Input dataset", "outputs": [], "position": {"left": 10, "top": 10}, "tool_errors": null, "tool_id": null, "tool_state": "{\\"name\\": \\"Input Dataset\\"}", "tool_version": null, "type": "data_input", "user_outputs": []}, "1": {"annotation": "", "id": 1, "input_connections": {"input": {"id": 0, "output_name": "output"}}, "inputs": [], "name": "Filter", "outputs": [{"name": "out_file1", "type": "input"}], "position": {"left": 230, "top": 10}, "post_job_actions": {}, "tool_errors": null, "tool_id": "Filter1", "tool_state": "{\\"__page__\\": 0, \\"cond\\": \\"\\\\\\"c1=='chr1'\\\\\\"\\", \\"chromInfo\\": \\"\\\\\\"/Users/gvk/workspaces_2008/central_051111/tool-data/shared/ucsc/chrom/?.len\\\\\\"\\", \\"input\\": \\"null\\"}", "tool_version": null, "type": "tool", "user_outputs": []}, "2": {"annotation": "", "id": 2, "input_connections": {"input1": {"id": 0, "output_name": "output"}, "input2": {"id": 1, "output_name": "out_file1"}}, "inputs": [], "name": "Subtract Whole Dataset", "outputs": [{"name": "output", "type": "input"}], "position": {"left": 450, "top": 10}, "post_job_actions": {}, "tool_errors": null, "tool_id": "subtract_query1", "tool_state": "{\\"input2\\": \\"null\\", \\"__page__\\": 0, \\"end_col\\": \\"{\\\\\\"__class__\\\\\\": \\\\\\"UnvalidatedValue\\\\\\", \\\\\\"value\\\\\\": \\\\\\"None\\\\\\"}\\", \\"begin_col\\": \\"{\\\\\\"__class__\\\\\\": \\\\\\"UnvalidatedValue\\\\\\", \\\\\\"value\\\\\\": \\\\\\"None\\\\\\"}\\", \\"input1\\": \\"null\\", \\"chromInfo\\": \\"\\\\\\"/Users/gvk/workspaces_2008/central_051111/tool-data/shared/ucsc/chrom/?.len\\\\\\"\\"}", "tool_version": null, "type": "tool", "user_outputs": []}}}]}"
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">${metadata[ 'name' ]} tool metadata</div>
        <div class="toolFormBody">
            <div class="form-row">
                <label>Name:</label>
                <a href="${h.url_for( controller='repository', action='display_tool', repository_id=trans.security.encode_id( repository.id ), tool_config=metadata[ 'tool_config' ] )}">${metadata[ 'name' ]}</a>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                ${metadata[ 'description' ]}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Id:</label>
                ${metadata[ 'id' ]}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Version:</label>
                ${metadata[ 'version' ]}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Version command string:</label>
                ${metadata[ 'version_string_cmd' ]}
                <div style="clear: both"></div>
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
                                        ${required_file[0]}<br/>
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
