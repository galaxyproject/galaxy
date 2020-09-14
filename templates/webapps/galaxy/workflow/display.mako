<%inherit file="/display_base.mako"/>
<%namespace file="/display_common.mako" import="render_message" />

<%!
    import markupsafe
    from galaxy.tools.parameters.basic import DataCollectionToolParameter, DataToolParameter, RuntimeValue
    from galaxy.web import form_builder
%>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="do_inputs( inputs, values, prefix, step, other_values=None )">
  %for input_index, input in enumerate( inputs.values() ):
    %if input.type == "repeat":
      <div>
          <div class="form-row"><b>${input.title_plural}</b></div>
          <% repeat_values = values[input.name] %>
          %for i in range( len( repeat_values ) ):
            <div class="ui-portlet-section ml-2">
                <% index = repeat_values[i]['__index__'] %>
                <div class="form-row"><b>${input.title} ${i + 1}</b></div>
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
    %elif input.type == "section":
      <% new_prefix = prefix + input.name + "|" %>
      <% group_values = values[input.name] %>
      <div class="form-row"><b>${input.title}:</b></div>
      <div>
        <div class="ui-portlet-section ml-2">
          ${do_inputs( input.inputs, group_values, new_prefix, step, other_values )}
        </div>
      </div>
    %else:
      ${row_for_param( input, values[ input.name ], other_values, prefix, step )}
    %endif
  %endfor
</%def>

<%def name="row_for_param( param, value, other_values, prefix, step )">
    <% cls = "form-row" %>
    <div class="${cls}">
        <label>${param.get_label() | h}</label>
        <div>
            %if isinstance( param, DataToolParameter ) or isinstance( param, DataCollectionToolParameter ):
                %if ( prefix + param.name ) in step.input_connections_by_name:
                    <%
                        conns = step.input_connections_by_name[ prefix + param.name ]
                        if not isinstance(conns, list):
                            conns = [conns]
                        vals = ["Output dataset '%s' from step %d" % (conn.output_name, int(conn.output_step.order_index)+1) for conn in conns]
                    %>
                    ${",".join(vals)}
                %else:
                    <i>select at runtime</i>
                %endif
            %else:
                ${markupsafe.escape( param.value_to_display_text( value ) or 'Unavailable.' )}
            %endif
        </div>
        %if hasattr( step, 'upgrade_messages' ) and step.upgrade_messages and param.name in step.upgrade_messages:
            ${render_message( step.upgrade_messages[param.name], "info" )}
        %endif
    </div>
</%def>

<%def name="render_item_links( workflow )">
   ## Check owner, show edit or view
    %if user_is_owner:
      <a
          href="${h.url_for( controller='/workflows', action='run', id=trans.security.encode_id(workflow.id) )}"
          class="btn btn-secondary fa fa-play float-right"
          title="Run workflow"></a>
      <a
          href="${h.url_for( controller='/workflow', action='editor', id=trans.security.encode_id(workflow.id) )}"
          class="btn btn-secondary fa fa-edit float-right mr-2"
          title="Edit workflow"></a>
    %elif workflow.importable:
      <a
          href="${h.url_for( controller='/workflow', action='imp', id=trans.security.encode_id(workflow.id) )}"
          class="btn btn-secondary fa fa-plus float-right"
          title="Import workflow"></a>
      <a
          href="${h.url_for( controller='/workflow', action='export_to_file', id=trans.security.encode_id(workflow.id) )}"
          class="btn btn-secondary fa fa-download float-right mr-2"
          title="Save workflow"></a>
    %endif
</%def>

<%def name="render_item( workflow, steps, outer_workflow=True )">
    <%
        # HACK: Rendering workflow steps requires that trans have a history; however, if its user's first visit to Galaxy is here, he won't have a history
        # and an error will occur. To prevent this error, make sure user has a history. 
        trans.get_history( most_recent=True, create=True )
    %>
    %if outer_workflow:
    <table class="annotated-item">
        <tr><th>Step</th><th class="annotation">Annotation</th></tr>
    %endif
        %for i, step in enumerate( steps ):
            <tr><td>
            %if step.type == 'tool' or step.type is None:
              <% 
                tool = trans.app.toolbox.get_tool( step.tool_id )
              %>
              <div class="card mt-3 mr-3">
                %if tool:
                  <div class="card-header">Step ${int(step.order_index)+1}: ${tool.name | h}</div>
                  <div class="card-body">
                    ${do_inputs( tool.inputs, step.state.inputs, "", step )}
                  </div>
                %else:
                  <div class="card-header">Step ${int(step.order_index)+1}: Unknown Tool with id '${step.tool_id | h}'</div>
                %endif
              </div>
            %elif step.type == 'subworkflow':
              <div class="card mt-3 mr-3">
                  <div class="card-header">Step ${int(step.order_index)+1}: ${step.label or (step.subworkflow.name if step.subworkflow else "Missing workflow") | h}</div>
                  <% errors = step.module.get_errors() %>
                  %if errors:
                    <div class="card-body">
                      <b>Error in Subworkflow:</b>
                      <ul>
                        %for error in errors:
                          <li>${error}</li>
                        %endfor
                      </ul>
                    </div>
                  %else:
                    <div class="card-body">
                      <table>${render_item( step.subworkflow, step.subworkflow.steps, outer_workflow=False )}</table>
                    </div>
                  %endif
              </div>
            %else:
            ## TODO: always input dataset?
            <% module = step.module %>
              <div class="card mt-3 mr-3">
                  <div class="card-header">Step ${int(step.order_index)+1}: ${module.name | h}</div>
                  <div class="card-body">
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
    %if outer_workflow:
    </table>
    %endif
</%def>
