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

<%def name="do_inputs( inputs, values, errors, prefix, step )">
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
            <div class="form-title-row"><b>${input.title} ${i + 1}</b></div>
            ${do_inputs( input.inputs, repeat_values[ i ], rep_errors,  prefix + input.name + "_" + str(i) + "|", step )}
            <div class="form-row"><input type="submit" name="${prefix}${input.name}_${i}_remove" value="Remove ${input.title} ${i+1}" /></div>
            </div>
          %endfor
          <div class="form-row"><input type="submit" name="${prefix}${input.name}_add" value="Add new ${input.title}" /></div>
      </div>
    %elif input.type == "conditional":
      <% group_values = values[input.name] %>
      <% current_case = group_values['__current_case__'] %>
      <% prefix = prefix + input.name + "|" %>
      <% group_errors = errors.get( input.name, {} ) %>
      ${row_for_param( input.test_param, group_values[ input.test_param.name ], group_errors, prefix, step )}
      ${do_inputs( input.cases[ current_case ].inputs, group_values, group_errors, prefix + input.name + "|", step )}
    %else:
      ${row_for_param( input, values[ input.name ], errors, prefix, step )}
    %endif
  %endfor  
</%def>

<%def name="row_for_param( param, value, error_dict, prefix, step )">
    %if error_dict.has_key( param.name ):
        <% cls = "form-row form-row-error" %>
    %else:
        <% cls = "form-row" %>
    %endif
    <div class="${cls}">
        <label>${param.get_label()}</label>
        <div>
            %if isinstance( param, DataToolParameter ):
                %if step.input_connections[ prefix + param.name ] is None:
                    ${param.get_html_field( t, dict(), dict() ).get_html( prefix )}
                %else:
                    <% id, name = step.input_connections[ prefix + param.name ] %>
                    Output dataset '${name}' from step ${int(id)+1}
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
    %for step in steps:
        <% tool = app.toolbox.tools_by_id[step.tool_id] %>
        <div class="toolForm">
            <div class="toolFormTitle">${int(step.id) + 1}: ${tool.name}</div>
            <div class="toolFormBody">
                ${do_inputs( tool.inputs, step.state.inputs, dict(), "", step )}
            </div>
        </div>
        
    %endfor
</body>