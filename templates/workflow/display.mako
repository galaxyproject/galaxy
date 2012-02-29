<%inherit file="/display_base.mako"/>
<%namespace file="/display_common.mako" import="render_message" />

<%!
    from galaxy.tools.parameters import DataToolParameter, RuntimeValue
    from galaxy.web import form_builder
%>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "workflow" )}
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
                    <i>select at runtime</i>
                %endif
            %else:
                ${param.value_to_display_text( value, app )}
            %endif
        </div>
        %if hasattr( step, 'upgrade_messages' ) and step.upgrade_messages and param.name in step.upgrade_messages:
            ${render_message( step.upgrade_messages[param.name], "info" )}
        %endif
    </div>
</%def>

<%def name="render_item_links( workflow )">
    %if workflow.importable:
    <a
        href="${h.url_for( controller='/workflow', action='imp', id=trans.security.encode_id(workflow.id) )}"
        class="icon-button import"
        ## Needed to overwide initial width so that link is floated left appropriately.
        style="width: 100%"
        title="Import workflow">Import workflow</a>
    %endif
</%def>

<%def name="render_item( workflow, steps )">
    <%
        # HACK: Rendering workflow steps requires that trans have a history; however, if it's  user's first visit to Galaxy is here, he won't have a history
        # and an error will occur. To prevent this error, make sure user has a history. 
        trans.get_history( create=True ) 
    %>
    <table class="annotated-item">
        <tr><th>Step</th><th class="annotation">Annotation</th></tr>
        %for i, step in enumerate( steps ):
            <tr><td>
            %if step.type == 'tool' or step.type is None:
              <% 
                tool = trans.app.toolbox.get_tool( step.tool_id )
              %>
              <div class="toolForm">
                  <div class="toolFormTitle">Step ${int(step.order_index)+1}: ${tool.name}</div>
                  <div class="toolFormBody">
                    ${do_inputs( tool.inputs, step.state.inputs, "", step )}
                  </div>
              </div>
            %else:
            ## TODO: always input dataset?
            <% module = step.module %>
              <div class="toolForm">
                  <div class="toolFormTitle">Step ${int(step.order_index)+1}: ${module.name}</div>
                  <div class="toolFormBody">
                    ${do_inputs( module.get_runtime_inputs(), step.state.inputs, "", step )}
                  </div>
              </div>
            %endif
            </td>
            <td class="annotation">
                %if hasattr( step, "annotation") and step.annotation is not None:
                    ${step.annotation}
                %endif                
            </td>
            </tr>
        %endfor
    </table>
</%def>
