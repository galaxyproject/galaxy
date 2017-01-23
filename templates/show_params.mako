<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<% from galaxy.util import listify, nice_size, unicodify %>

<style>
    .inherit {
        border: 1px solid #bbb;
        padding: 15px;
        text-align: center;
        background-color: #eee;
    }

    table.info_data_table {
        table-layout: fixed;
        word-break: break-word;
    }
    table.info_data_table td:nth-child(1) {
        width: 25%;
    }

    .code {
        white-space: pre-wrap;
        background: #1d1f21;
        color: white;
        padding: 1em;
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
            %elif input.type == "section":
                <tr>
                    ##<!-- Get the value of the current Section parameter -->
                    ${inputs_recursive_indent( text=input.name, depth=depth )}
                    <td></td>
                </tr>
                ${ inputs_recursive( input.inputs, param_values[input.name], depth=depth+1, upgrade_messages=upgrade_messages.get( input.name ) ) }
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
            ## files used for inputs
            %elif input.type == "data":
                    <tr>
                        ${inputs_recursive_indent( text=input.label, depth=depth )}
                        <td>
                        %for i, element in enumerate(listify(param_values[input.name])):
                            %if i > 0:
                            ,
                            %endif
                            %if element.history_content_type == "dataset":
                                <%
                                    hda = element
                                    encoded_id = trans.security.encode_id( hda.id )
                                    show_params_url = h.url_for( controller='dataset', action='show_params', dataset_id=encoded_id )
                                %>
                                <a class="input-dataset-show-params" data-hda-id="${encoded_id}"
                                       href="${show_params_url}">${hda.hid}: ${hda.name | h}</a>

                            %else:
                                ${element.hid}: ${element.name | h}
                            %endif
                        %endfor
                        </td>
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

<h2>
% if tool:
    ${tool.name | h}
% else:
    Unknown Tool
% endif
</h2>

<h3>Dataset Information</h3>
<table class="tabletip" id="dataset-details">
    <tbody>
        <%
        encoded_hda_id = trans.security.encode_id( hda.id )
        encoded_history_id = trans.security.encode_id( hda.history_id )
        %>
        <tr><td>Number:</td><td>${hda.hid | h}</td></tr>
        <tr><td>Name:</td><td>${hda.name | h}</td></tr>
        <tr><td>Created:</td><td>${unicodify(hda.create_time.strftime(trans.app.config.pretty_datetime_format))}</td></tr>
        ##      <tr><td>Copied from another history?</td><td>${hda.source_library_dataset}</td></tr>
        <tr><td>Filesize:</td><td>${nice_size(hda.dataset.file_size)}</td></tr>
        <tr><td>Dbkey:</td><td>${hda.dbkey | h}</td></tr>
        <tr><td>Format:</td><td>${hda.ext | h}</td></tr>
    </tbody>
</table>

<h3>Job Information</h3>
<table class="tabletip">
    <tbody>
        %if job:
            <tr><td>Galaxy Tool ID:</td><td>${ job.tool_id | h }</td></tr>
            <tr><td>Galaxy Tool Version:</td><td>${ job.tool_version | h }</td></tr>
        %endif
        <tr><td>Tool Version:</td><td>${hda.tool_version | h}</td></tr>
        <tr><td>Tool Standard Output:</td><td><a href="${h.url_for( controller='dataset', action='stdout', dataset_id=encoded_hda_id )}">stdout</a></td></tr>
        <tr><td>Tool Standard Error:</td><td><a href="${h.url_for( controller='dataset', action='stderr', dataset_id=encoded_hda_id )}">stderr</a></td></tr>
        %if job:
            <tr><td>Tool Exit Code:</td><td>${ job.exit_code | h }</td></tr>
        %endif
        <tr><td>History Content API ID:</td><td>${encoded_hda_id}</td></tr>
        %if job:
            <tr><td>Job API ID:</td><td>${trans.security.encode_id( job.id )}</td></tr>
        %endif
        <tr><td>History API ID:</td><td>${encoded_history_id}</td></tr>
        %if hda.dataset.uuid:
        <tr><td>UUID:</td><td>${hda.dataset.uuid}</td></tr>
        %endif
        %if trans.user_is_admin() or trans.app.config.expose_dataset_path:
            <tr><td>Full Path:</td><td>${hda.file_name | h}</td></tr>
        %endif
    </tbody>
</table>

<h3>Tool Parameters</h3>
<table class="tabletip" id="tool-parameters">
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
            <tr><td colspan="3">Unable to load parameters.</td></tr>
        % else:
            <tr><td colspan="3">No parameters.</td></tr>
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
    <div style="font-size: 36px; text-align: center; position: relative; top: 3px">&uarr;</div>
    <div class="inherit">
        '${dep[0].name | h}' in ${dep[1]}<br/>
    </div>
% endfor



%if job and job.command_line and (trans.user_is_admin() or trans.app.config.expose_dataset_path):
<h3>Command Line</h3>
<pre class="code">
${ job.command_line | h }</pre>
%endif

%if job and (trans.user_is_admin() or trans.app.config.expose_potentially_sensitive_job_metrics):
<h3>Job Metrics</h3>
<% job_metrics = trans.app.job_metrics %>
<% plugins = set([metric.plugin for metric in job.metrics]) %>
    %for plugin in sorted(plugins):
    %if trans.user_is_admin() or plugin != 'env':
    <h4>${ plugin | h }</h4>
    <table class="tabletip info_data_table">
        <tbody>
        <%
            plugin_metrics = filter(lambda x: x.plugin == plugin, job.metrics)
            plugin_metric_displays = [job_metrics.format( metric.plugin, metric.metric_name, metric.metric_value ) for metric in plugin_metrics]
            plugin_metric_displays = sorted(plugin_metric_displays, key=lambda pair: pair[0])  # Sort on displayed title
        %>
            %for metric_title, metric_value in plugin_metric_displays:
                <tr><td>${ metric_title | h }</td><td>${ metric_value | h }</td></tr>
            %endfor
        </tbody>
    </table>
    %endif
    %endfor
%endif

%if job and job.dependencies:
<h3>Job Dependencies</h3>
    <table class="tabletip">
        <thead>
        <tr>
            <th>Dependency</th>
            <th>Dependency Type</th>
            <th>Version</th>
        </tr>
        </thead>
        <tbody>

            %for dependency in job.dependencies:
                <tr><td>${ dependency['name'] | h }</td>
                    <td>${ dependency['dependency_type'] | h }</td>
                    <td>${ dependency['version'] | h }</td>
                </tr>
            %endfor

        </tbody>
    </table>
%endif



<script type="text/javascript">
$(function(){
    $( '.input-dataset-show-params' ).on( 'click', function( ev ){
        ## some acrobatics to get the Galaxy object that has a history from the contained frame
        if( window.parent.Galaxy && window.parent.Galaxy.currHistoryPanel ){
            window.parent.Galaxy.currHistoryPanel.scrollToId( 'dataset-' + $( this ).data( 'hda-id' ) );
        }
    })
});
</script>
