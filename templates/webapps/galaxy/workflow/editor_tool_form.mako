<%
from galaxy.tools.parameters import DataToolParameter, RuntimeValue
from galaxy.tools.parameters import DataCollectionToolParameter
from galaxy.util.expressions import ExpressionContext
%>

<%def name="do_inputs( inputs, values, errors, prefix, ctx=None )">
  <% ctx = ExpressionContext( values, ctx ) %>
  %for input_index, input in enumerate( inputs.itervalues() ):
    %if input.type == "repeat":
      <div class="repeat-group form-row">
          <label>${input.title_plural}:</label>
          <% repeat_values = values[input.name] %>
          %for i in range( len( repeat_values ) ):
            <%
            if input.name in errors:
                rep_errors = errors[input.name][i]
            else:
                rep_errors = dict()
            index = repeat_values[i]['__index__']
            %>
            <div class="repeat-group-item">
            <div class="form-title-row"><label>${input.title} ${i + 1}</label></div>
            ${do_inputs( input.inputs, repeat_values[ i ], rep_errors,  prefix + input.name + "_" + str(index) + "|", ctx )}
            <div class="form-row"><input type="submit" name="${prefix}${input.name}_${index}_remove" value="Remove ${input.title} ${i+1}"></div>
            </div>
          %endfor
          <div class="form-row"><input type="submit" name="${prefix}${input.name}_add" value="Add new ${input.title}"></div>
      </div>
    %elif input.type == "conditional":
      %if input.is_job_resource_conditional:
        <% continue %>
      %endif
      <% group_values = values[input.name] %>
      <% current_case = group_values['__current_case__'] %>
      <% group_prefix = prefix + input.name + "|" %>
      <% group_errors = errors.get( input.name, {} ) %>
      ${row_for_param( input.test_param, group_values[ input.test_param.name ], group_errors, group_prefix, ctx, allow_runtime=False )}
      ${do_inputs( input.cases[ current_case ].inputs, group_values, group_errors, group_prefix, ctx )}
    %else:
      %if input.name in values:
        ${row_for_param( input, values[ input.name ], errors, prefix, ctx )}
      %else:
        <% errors[ input.name ] = 'Value not stored, displaying default' %>
        ${row_for_param( input, input.get_initial_value( trans, values ), errors, prefix, ctx )}
      %endif
    %endif
  %endfor  
</%def>

<%def name="row_for_param( param, value, error_dict, prefix, ctx, allow_runtime=True )">
    %if error_dict.has_key( param.name ):
        <% cls = "form-row form-row-error" %>
    %else:
        <% cls = "form-row" %>
    %endif
    <div class="${cls}" id="row-${prefix}${param.name}">
        ## Data parameters are very special since their value / runtime state
        ## comes from connectors
        %if type( param ) is DataToolParameter:
            <label>
                ${param.get_label()}
            </label>
            <div>
                Data input '${param.name}' (${" or ".join( param.extensions )})
            </div>
        %elif type( param ) is DataCollectionToolParameter:
            <label>
                ${param.get_label()}
            </label>
            <div>
                Data collection input '${param.name}'
            </div>
        %else:
            %if isinstance( value, RuntimeValue ):    
                <label>
                    ${param.get_label()}:
                    <span class="popupmenu">
                        <button type="submit" name="make_buildtime" value="${prefix}${param.name}">Set in advance</button>
                    </span>
                </label>
                <div>
                    <i>To be set at runtime</i>
                </div>
            %else:
                <label>
                    ${param.get_label()}:
                    %if allow_runtime:
                        <span class="popupmenu">
                            <button type="submit" name="make_runtime" value="${prefix}${param.name}">Set at runtime</button>
                        </span>
                    %endif
                </label>
                <div>
                    ${param.get_html_field( trans, value, ctx ).get_html( prefix )}          
                </div>
            %endif
            %if error_dict.has_key( param.name ):
            <div style="color: red; font-weight: bold; padding-top: 1px; padding-bottom: 3px;">
                <div style="width: 300px;"><img style="vertical-align: middle;" src="${h.url_for('/static/style/error_small.png')}">&nbsp;<span style="vertical-align: middle;">${error_dict[param.name]}</span></div>
            </div>
            %endif
        %endif
        <div style="clear: both"></div>       
    </div>
</%def>

<form method="post" action="${h.url_for(controller='workflow', action='editor_form_post' )}">

    <div class="toolForm">
        <div class="toolFormTitle">Tool: ${tool.name}</div>
        %if tool.version:
            <div class="form-row"><div class='titleRow'>Version: ${tool.version}</div></div>
        %endif
        <div class="toolFormBody">
            <input type="hidden" name="tool_id" value="${tool.id}" />
            %for i, inputs in enumerate( tool.inputs_by_page ):
                %if tool.has_multiple_pages:
                    <div class='titleRow'>Page ${i+1}</div>
                %endif
                ${do_inputs( inputs, values, errors, "" )}
            %endfor
        </div>
    </div>
    

</form>
