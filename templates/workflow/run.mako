<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<head>
<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<style type="text/css">
div.toolForm{
    margin-top: 10px;
    margin-bottom: 10px;
}
</style>
</head>

<%
from galaxy.tools.parameters import DataToolParameter
%>

<%def name="do_inputs( inputs, values, errors, prefix, step, other_values = None )">
  %if other_values is None:
      <% other_values = values %>
  %endif
  %for input_index, input in enumerate( inputs.itervalues() ):
    %if input.type == "repeat":
      <div class="repeat-group">
          <div class="form-title-row"><b>${input.title_plural}</b></div>
          <% repeat_values = values[input.name] %>
          %for i in range( len( repeat_values ) ):
            %if input.name in errors:
                <% rep_errors = errors[input.name][i] %>
            %else:
                <% rep_errors = dict() %>
            %endif
            <div class="repeat-group-item">
            <% index = repeat_values[i]['__index__'] %>
            <div class="form-title-row"><b>${input.title} ${i + 1}</b></div>
            ${do_inputs( input.inputs, repeat_values[ i ], rep_errors,  prefix + input.name + "_" + str(index) + "|", step, other_values )}
            ## <div class="form-row"><input type="submit" name="${step.id}|${prefix}${input.name}_${i}_remove" value="Remove ${input.title} ${i+1}" /></div>
            </div> 
          %endfor
          ## <div class="form-row"><input type="submit" name="${step.id}|${prefix}${input.name}_add" value="Add new ${input.title}" /></div>
      </div>
    %elif input.type == "conditional":
      <% group_values = values[input.name] %>
      <% current_case = group_values['__current_case__'] %>
      <% prefix = prefix + input.name + "|" %>
      <% group_errors = errors.get( input.name, {} ) %>
      ${row_for_param( input.test_param, group_values[ input.test_param.name ], other_values, group_errors, prefix, step )}
      ${do_inputs( input.cases[ current_case ].inputs, group_values, group_errors, prefix + input.name + "|", step, other_values )}
    %else:
      ${row_for_param( input, values[ input.name ], other_values, errors, prefix, step )}
    %endif
  %endfor  
</%def>

<%def name="row_for_param( param, value, other_values, error_dict, prefix, step )">
    ## -- ${param.name} -- ${step.state.inputs} --
    %if error_dict.has_key( param.name ):
        <% cls = "form-row form-row-error" %>
    %else:
        <% cls = "form-row" %>
    %endif
    <div class="${cls}">
        <label>${param.get_label()}</label>
        <div>
            %if isinstance( param, DataToolParameter ):
                %if ( prefix + param.name ) in step.input_connections_by_name:
                    <%
                        conn = step.input_connections_by_name[ prefix + param.name ]
                    %>
                    Output dataset '${conn.output_name}' from step ${int(conn.output_step.order_index)+1}
                %else:
                    ${param.get_html_field( t, dict(), other_values ).get_html( str(step.id) + "|" + prefix )}
                    <input type="hidden" name="${step.id}|__force_update__${prefix}${param.name}" value="true" />
                %endif
            %else:
                ${param.value_to_display_text( value, app )}
            %endif
        </div>
        %if error_dict.has_key( param.name ):
        <div style="color: red; font-weight: bold; padding-top: 1px; padding-bottom: 3px;">
            <div style="width: 300px;"><img style="vertical-align: middle;" src="${h.url_for('/static/style/error_small.png')}">&nbsp;<span style="vertical-align: middle;">${error_dict[param.name]}</span></div>
        </div>
        %endif
        <div style="clear: both"></div>       
    </div>
</%def>

<body>
    <h2>Running workflow "${workflow.name}"</h2>
    <form method="POST">
    ## <input type="hidden" name="workflow_name" value="${workflow.name | h}" />
    %for i, step in enumerate( steps ):
        %if step.type == 'tool' or step.type is None:
          <% tool = app.toolbox.tools_by_id[step.tool_id] %>
          <input type="hidden" name="${step.id}|tool_state" value="${step.state.encode( tool, app )}">
          <div class="toolForm">
              <div class="toolFormTitle">Step ${int(step.order_index)+1}: ${tool.name}</div>
              <div class="toolFormBody">
                  ${do_inputs( tool.inputs, step.state.inputs, errors.get( step.id, dict() ), "", step )}
              </div>
          </div>
        %else:
        <% module = step.module %>
          <input type="hidden" name="${step.id}|tool_state" value="${module.encode_runtime_state( t, step.state )}">
          <div class="toolForm">
              <div class="toolFormTitle">Step ${int(step.order_index)+1}: ${module.name}</div>
              <div class="toolFormBody">
                  ${do_inputs( module.get_runtime_inputs(), step.state.inputs, errors.get( step.id, dict() ), "", step )}
              </div>
          </div>
        %endif
    %endfor
    <input type="submit" value="Run workflow" />
    </form>
</body>