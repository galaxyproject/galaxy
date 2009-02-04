<%def name="do_inputs( inputs, values, errors, prefix )">
  %for input_index, input in enumerate( inputs.itervalues() ):
    %if input.type == "repeat":
      <div class="repeat-group">
          <div class="form-title-row"><b>${input.title_plural}</b></div>
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
            <div class="form-title-row"><b>${input.title} ${i + 1}</b></div>
            ${do_inputs( input.inputs, repeat_values[ i ], rep_errors,  prefix + input.name + "_" + str(index) + "|" )}
            <div class="form-row"><input type="submit" name="${prefix}${input.name}_${index}_remove" value="Remove ${input.title} ${i+1}"></div>
            </div>
          %endfor
          <div class="form-row"><input type="submit" name="${prefix}${input.name}_add" value="Add new ${input.title}"></div>
      </div>
    %elif input.type == "conditional":
      <% group_values = values[input.name] %>
      <% current_case = group_values['__current_case__'] %>
      <% group_prefix = prefix + input.name + "|" %>
      <% group_errors = errors.get( input.name, {} ) %>
      ${row_for_param( input.test_param, group_values[ input.test_param.name ], group_errors, group_prefix )}
      ${do_inputs( input.cases[ current_case ].inputs, group_values, group_errors, group_prefix )}
    %else:
      %if input.name in values:
        ${row_for_param( input, values[ input.name ], errors, prefix )}
      %else:
        <% errors[ input.name ] = 'Value not stored, displaying default' %>
        ${row_for_param( input, input.get_initial_value( trans, values ), errors, prefix )}
      %endif
    %endif
  %endfor  
</%def>

<%def name="row_for_param( param, value, error_dict, prefix )">
    %if error_dict.has_key( param.name ):
        <% cls = "form-row form-row-error" %>
    %else:
        <% cls = "form-row" %>
    %endif
    <div class="${cls}">
        <label>${param.get_label()}</label>
        <div>
            ${as_html( param, value, t, prefix )}
        </div>
        %if error_dict.has_key( param.name ):
        <div style="color: red; font-weight: bold; padding-top: 1px; padding-bottom: 3px;">
            <div style="width: 300px;"><img style="vertical-align: middle;" src="${h.url_for('/static/style/error_small.png')}">&nbsp;<span style="vertical-align: middle;">${error_dict[param.name]}</span></div>
        </div>
        %endif
        <div style="clear: both"></div>       
    </div>
</%def>
    
<div class="toolForm">
    <div class="toolFormTitle">Tool: ${tool.name}</div>
    <div class="toolFormBody">
        <form method="post" action="${h.url_for( action='editor_form_post' )}">
            <input type="hidden" name="tool_id" value="${tool.id}" />
            %for i, inputs in enumerate( tool.inputs_by_page ):
                %if tool.has_multiple_pages:
                    <div class='titleRow'>Page ${i+1}</div>
                %endif
                ${do_inputs( inputs, values, errors, "" )}
            %endfor
            <div class="form-row">
                <input type="submit" id="tool-form-save-button" value="Save"></input>
            </div>
        </form>
    </div>
</div>