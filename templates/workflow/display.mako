<%inherit file="/display_base.mako"/>

<%! from galaxy.tools.parameters import DataToolParameter, RuntimeValue %>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "workflow" )}
    <style type="text/css">
        div.toolForm{
            margin-top: 10px;
            margin-bottom: 10px;
        }
    </style>
</%def>

<%def name="do_inputs( inputs, values, prefix, step, other_values=None )">
  %for input_index, input in enumerate( inputs.itervalues() ):
    %if input.type == "repeat":
      <div class="repeat-group">
          <div class="form-title-row"><b>${input.title_plural}</b></div>
          <% repeat_values = values[input.name] %>
          %for i in range( len( repeat_values ) ):
            <div class="repeat-group-item">
            <% index = repeat_values[i]['__index__'] %>
            <div class="form-title-row"><b>${input.title} ${i + 1}</b></div>
            ${do_inputs( input.inputs, repeat_values[ i ], prefix + input.name + "_" + str(index) + "|", step, other_values )}
            
            </div> 
          %endfor
      </div>
    %elif input.type == "conditional":
      <% group_values = values[input.name] %>
      <% current_case = group_values['__current_case__'] %>
      <% new_prefix = prefix + input.name + "|" %>
      ${row_for_param( input.test_param, group_values[ input.test_param.name ], other_values, prefix, step )}
      ${do_inputs( input.cases[ current_case ].inputs, group_values, new_prefix, step, other_values )}
    %else:
      ${row_for_param( input, values[ input.name ], other_values, prefix, step )}
    %endif
  %endfor  
</%def>

<%def name="row_for_param( param, value, other_values, prefix, step )">
    <% cls = "form-row" %>
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
                        other_values = {}
                        value = other_values[ param.name ] = param.get_initial_value( t, other_values )
                    %>
                    <% print param.__class__ %>
                    ${param.get_html_field( t, value, other_values ).get_html( str(step.id) + "|" + prefix )}
                %endif
            %else:
                ${param.value_to_display_text( value, app )}
            %endif
        </div>      
    </div>
</%def>


<%def name="render_item_links( workflow )">
    %if workflow.user != trans.get_user():
        <a href="${h.url_for( controller='/workflow', action='imp', id=trans.security.encode_id(workflow.id) )}">import and start using workflow</a>
    %else:
        your workflow
    %endif
</%def>

<%def name="render_item( workflow, steps )">
     <h2>${workflow.name}</h2>
        %for i, step in enumerate( steps ):    
            %if step.type == 'tool' or step.type is None:
              <% tool = app.toolbox.tools_by_id[step.tool_id] %>
              <div class="toolForm">
                  <div class="toolFormTitle">Step ${int(step.order_index)+1}: ${tool.name}</div>
                  <div class="toolFormBody">
                    ${do_inputs( tool.inputs, step.state.inputs, "", step )}
                  </div>
              </div>
            %else:
            <% module = step.module %>
              <div class="toolForm">
                  <div class="toolFormTitle">Step ${int(step.order_index)+1}: ${module.name}</div>
                  <div class="toolFormBody">
                    ##Need to do more work to print only dataset label and not combo box as well.
                    ##${do_inputs( module.get_runtime_inputs(), step.state.inputs, "", step )}
                  </div>
              </div>
            %endif
        %endfor
</%def>