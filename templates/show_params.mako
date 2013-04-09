<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<% from galaxy.util import nice_size %>

<style>
    .inherit {
        border: 1px solid #bbb;
        padding: 15px;
        text-align: center;
        background-color: #eee;
    }
</style>

<%def name="inputs_recursive( input_params, param_values, depth=1, upgrade_messages=None )">
    <%
        if upgrade_messages is None:
            upgrade_messages = {}
    %>
    %for input_index, input in enumerate( input_params.itervalues() ):
        %if input.name in param_values:
            %if input.type == "repeat":
                %for i in range( len(param_values[input.name]) ):
                    ${ inputs_recursive(input.inputs, param_values[input.name][i], depth=depth+1) }
                %endfor
            %elif input.type == "conditional":
                <% 
                try:
                    current_case = param_values[input.name]['__current_case__']
                    is_valid = True
                except:
                    current_case = None
                    is_valid = False
                %>
                %if is_valid:
                    <tr>
                        ${ inputs_recursive_indent( text=input.test_param.label, depth=depth )}
                        ##<!-- Get the value of the current Conditional parameter -->
                        <td>${input.cases[current_case].value | h}</td>
                        <td></td>
                    </tr>
                    ${ inputs_recursive( input.cases[current_case].inputs, param_values[input.name], depth=depth+1, upgrade_messages=upgrade_messages.get( input.name ) ) }
                %else:
                    <tr>
                        ${ inputs_recursive_indent( text=input.name, depth=depth )}
                        <td><em>The previously used value is no longer valid</em></td>
                        <td></td>
                    </tr>
                %endif
            %elif input.type == "upload_dataset":
                    <tr>
                        ${inputs_recursive_indent( text=input.group_title( param_values ), depth=depth )}
                        <td>${ len( param_values[input.name] ) } uploaded datasets</td>
                        <td></td>
                    </tr>
            %elif input.visible:
                <% 
                if  hasattr( input, "label" ) and input.label:
                    label = input.label
                else:
                    #value for label not required, fallback to input name (same as tool panel)
                    label = input.name
                %>
                <tr>
                    ${inputs_recursive_indent( text=label, depth=depth )}
                    <td>${input.value_to_display_text( param_values[input.name], trans.app ) | h}</td>
                    <td>${ upgrade_messages.get( input.name, '' ) | h }</td>
                </tr>
            %endif
        %else:
            ## Parameter does not have a stored value.
            <tr>
                <%
                    # Get parameter label.  
                    if input.type == "conditional":
                        label = input.test_param.label
                    elif input.type == "repeat":
                        label = input.label()
                    else:
                        label = input.label or input.name
                %>
                ${inputs_recursive_indent( text=label, depth=depth )}
                <td><em>not used (parameter was added after this job was run)</em></td>
                <td></td>
            </tr>
        %endif
        
    %endfor
</%def>

 ## function to add a indentation depending on the depth in a <tr>
<%def name="inputs_recursive_indent( text, depth )">
    <td style="padding-left: ${ ( depth - 1 ) * 10 }px">
        ${text | h}
    </td> 
</%def>

<table class="tabletip">
    <thead>
        <tr><th colspan="2" style="font-size: 120%;">
            % if tool:
                Tool: ${tool.name | h}
            % else:
                Unknown Tool
            % endif
        </th></tr>
    </thead>
    <tbody>
        <tr><td>Name:</td><td>${hda.name | h}</td></tr>
        <tr><td>Created:</td><td>${hda.create_time.strftime("%b %d, %Y")}</td></tr>
        ##      <tr><td>Copied from another history?</td><td>${hda.source_library_dataset}</td></tr>
        <tr><td>Filesize:</td><td>${nice_size(hda.dataset.file_size)}</td></tr>
        <tr><td>Dbkey:</td><td>${hda.dbkey | h}</td></tr>
        <tr><td>Format:</td><td>${hda.ext | h}</td></tr>
        <tr><td>Galaxy Tool Version:</td><td>${job.tool_version | h}</td></tr>
        <tr><td>Tool Version:</td><td>${hda.tool_version | h}</td></tr>
        <tr><td>Tool Standard Output:</td><td><a href="${h.url_for( controller='dataset', action='stdout')}">stdout</a></td></tr>
        <tr><td>Tool Standard Error:</td><td><a href="${h.url_for( controller='dataset', action='stderr')}">stderr</a></td></tr>
        <tr><td>Tool Exit Code:</td><td>${job.exit_code | h}</td></tr>
        <tr><td>API ID:</td><td>${trans.security.encode_id(hda.id)}</td></tr>
        %if trans.user_is_admin() or trans.app.config.expose_dataset_path:
            <tr><td>Full Path:</td><td>${hda.file_name | h}</td></tr>
        %endif
</table>
<br />

<table class="tabletip">
    <thead>
        <tr>
            <th>Input Parameter</th>
            <th>Value</th>
            <th>Note for rerun</th>
        </tr>
    </thead>
    <tbody>
        % if params_objects and tool:
            ${ inputs_recursive( tool.inputs, params_objects, depth=1, upgrade_messages=upgrade_messages ) }
        %elif params_objects is None:
            <tr><td colspan="2">Unable to load parameters.</td></tr>
        % else:
            <tr><td colspan="2">No parameters.</td></tr>
        % endif
    </tbody>
</table>
%if has_parameter_errors:
    <br />
    ${ render_msg( 'One or more of your original parameters may no longer be valid or displayed properly.', status='warning' ) }
%endif

    <h3>Inheritance Chain</h3>
    <div class="inherit" style="background-color: #fff; font-weight:bold;">${hda.name | h}</div>

    % for dep in inherit_chain:
    <div style="font-size: 36px; text-align: center;">&uarr;</div>
    <div class="inherit">${dep[0].name | h}<br/>${dep[1]}</div>
    % endfor

