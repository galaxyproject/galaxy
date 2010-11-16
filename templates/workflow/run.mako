<%inherit file="/base.mako"/>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "jquery.autocomplete" )}
    <script type="text/javascript">        
        $( function() {
            $( "select[refresh_on_change='true']").change( function() {
                $( "#tool_form" ).submit();
            });
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
    <style type="text/css">
    div.toolForm{
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .step-annotation {
        margin-top: 0.25em;
        font-weight: normal;
        font-size: 97%;
    }
    .workflow-annotation {
        margin-bottom: 1em;
    }
    </style>
</%def>

<%
from galaxy.tools.parameters import DataToolParameter, RuntimeValue
from galaxy.jobs.actions.post import ActionBox
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
      <% new_prefix = prefix + input.name + "|" %>
      <% group_errors = errors.get( input.name, {} ) %>
      ${row_for_param( input.test_param, group_values[ input.test_param.name ], other_values, group_errors, prefix, step )}
      ${do_inputs( input.cases[ current_case ].inputs, group_values, group_errors, new_prefix, step, other_values )}
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
                    ## FIXME: Initialize in the controller
                    <%
                    if value is None:
                        value = other_values[ param.name ] = param.get_initial_value( t, other_values )
                    %>
                    ${param.get_html_field( t, value, other_values ).get_html( str(step.id) + "|" + prefix )}
                    <input type="hidden" name="${step.id}|__force_update__${prefix}${param.name}" value="true" />
                %endif
            %elif isinstance( value, RuntimeValue ) or ( str(step.id) + '|__runtime__' + prefix + param.name ) in incoming:
                ## On the first load we may see a RuntimeValue, so we write
                ## an input field using the initial value for the param.
                ## Subsequents posts will no longer have the runtime value
                ## (since an actualy value will be posted) so we add a hidden
                ## field so we know to continue drawing form for this param.
                ## FIXME: This logic shouldn't be in the template. The
                ## controller should go through the inputs on the first
                ## load, fill in initial values where needed, and mark
                ## all that are runtime modifiable in some way.
                <% value = other_values[ param.name ] = param.get_initial_value( t, other_values ) %>
                ${param.get_html_field( t, value, other_values ).get_html( str(step.id) + "|" + prefix )}
                <input type="hidden" name="${step.id}|__runtime__${prefix}${param.name}" value="true" />
            %else:
                ${param.value_to_display_text( value, app )}
            %endif
        </div>
        %if step.upgrade_messages and param.name in step.upgrade_messages:
        <div class="warningmark">${step.upgrade_messages[param.name]}</div>
        %endif
        %if error_dict.has_key( param.name ):
        <div style="color: red; font-weight: bold; padding-top: 1px; padding-bottom: 3px;">
            <div style="width: 300px;"><img style="vertical-align: middle;" src="${h.url_for('/static/style/error_small.png')}">&nbsp;<span style="vertical-align: middle;">${error_dict[param.name]}</span></div>
        </div>
        %endif
        <div style="clear: both"></div>       
    </div>
</%def>

<h2>Running workflow "${h.to_unicode( workflow.name )}"</h2>

%if has_upgrade_messages:
<div class="warningmessage">
    Problems were encountered when loading this workflow, likely due to tool
    version changes. Missing parameter values have been replaced with default.
    Please review the parameter values below.
</div>
%endif

%if workflow.annotation:
    <div class="workflow-annotation">Annotation: ${workflow.annotation}</div>
    <hr/>
%endif

<form id="tool_form" name="tool_form" method="POST">
## <input type="hidden" name="workflow_name" value="${h.to_unicode( workflow.name ) | h}" />
%for i, step in enumerate( steps ):    
    %if step.type == 'tool' or step.type is None:
      <% tool = app.toolbox.tools_by_id[step.tool_id] %>
      <input type="hidden" name="${step.id}|tool_state" value="${step.state.encode( tool, app )}">
      <div class="toolForm">
          <div class="toolFormTitle">
              Step ${int(step.order_index)+1}: ${tool.name}
              % if step.annotations:
      			<div class="step-annotation">Annotation: ${h.to_unicode( step.annotations[0].annotation )}</div>
      		  % endif
          </div>
          <div class="toolFormBody">
              ${do_inputs( tool.inputs, step.state.inputs, errors.get( step.id, dict() ), "", step )}
			% if step.post_job_actions:
				<hr/>
				<div class='form-row'>
				% if len(step.post_job_actions) > 1:
					<label>Actions:</label>
				% else:
					<label>Action:</label>
				% endif
				${'<br/>'.join([ActionBox.get_short_str(pja) for pja in step.post_job_actions])}
				</div>
			% endif
          </div>
      </div>
    %else:
    <% module = step.module %>
      <input type="hidden" name="${step.id}|tool_state" value="${module.encode_runtime_state( t, step.state )}">
      <div class="toolForm">
          <div class="toolFormTitle">
              Step ${int(step.order_index)+1}: ${module.name}
              % if step.annotations:
  				<div class="step-annotation">Annotation: ${step.annotations[0].annotation}</div>
              % endif
  			
          </div>
          <div class="toolFormBody">
              ${do_inputs( module.get_runtime_inputs(), step.state.inputs, errors.get( step.id, dict() ), "", step )}
          </div>
      </div>
    %endif
%endfor
<input type="submit" name="run_workflow" value="Run workflow" />
</form>