<%inherit file="/base_panels.mako"/>
<%namespace file="/display_common.mako" import="get_history_link" />
<%namespace file="../tagging_common.mako" import="render_individual_tagging_element, render_community_tagging_element" />

<%! from galaxy.tools.parameters import DataToolParameter %>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "galaxy.base", "jquery", "json2", "jquery.autocomplete", "autocomplete_tagging" )}

    <script type="text/javascript">
    //
    // Handle click on community tag.
    //
    function community_tag_click(tag_name, tag_value) 
    {
        var href = '${h.url_for( controller='/workflow', action='list_public')}';
        href = href + "?f-tags=" + tag_name;
        if (tag_value != null && tag_value != "")
            href = href + ":" + tag_value;
        self.location = href;
    }
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "workflow", "autocomplete_tagging" )}
    <style type="text/css">
        .page-body
        {
            padding: 10px;
            float: left;
            width: 65%;
        }
        .page-meta
        {
            float: right;
            width: 27%;
            padding: 0.5em;
            margin: 0.25em;
            vertical-align: text-top;
            border: 2px solid #DDDDDD;
            border-top: 4px solid #DDDDDD;
        }
        div.toolForm{
            margin-top: 10px;
            margin-bottom: 10px;
        }
    </style>
    <noscript>
        <style>
            .historyItemBody {
                display: block;
            }
        </style>
    </noscript>
</%def>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
%>
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
                        value = other_values[ param.name ] = param.get_initial_value( t, other_values )
                    %>
                    ${param.get_html_field( t, value, other_values ).get_html( str(step.id) + "|" + prefix )}
                %endif
            %else:
                ${param.value_to_display_text( value, app )}
            %endif
        </div>      
    </div>
</%def>

<%def name="center_panel()">
    ## Get URL to other workflows owned by user that owns this workflow.
    <%
        ##TODO: is there a better way to create this URL? Can't use 'f-username' as a key b/c it's not a valid identifier.
        href_to_user_workflows = h.url_for( action='list_public', xxx=workflow.user.username )
        href_to_user_workflows = href_to_user_workflows.replace( 'xxx', 'f-username' )
    %>
    
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            <a href="${h.url_for ( action='list_public' )}">Public Workflows</a> | 
            <a href="${href_to_user_workflows}">${workflow.user.username}</a> | ${workflow.name}
        </div>
    </div>
    
    <div class="unified-panel-body">
        <div style="overflow: auto; height: 100%;">
            <div class="page-body">
                ## Render top links.
                <div id="top-links" style="padding: 0px 0px 5px 0px">
                    %if workflow.user != trans.get_user():
                        <a href="${h.url_for( action='imp', id=trans.security.encode_id(workflow.id) )}">import and start using workflow</a>
                    %endif
                </div>
            
                ## Render Workflow.
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
                          </div>
                      </div>
                    %endif
                %endfor
            </div>
        
            <div class="page-meta">
                ## Workflows.
                <div><strong>Related Workflows</strong></div>
                <p>
                    <a href="${h.url_for ( action='list_public' )}">All public workflows</a><br>
                    <a href="${href_to_user_workflows}">Workflows owned by ${workflow.user.username}</a>
            
                ## Tags.
                <div><strong>Tags</strong></div>
                <p>
                ## Community tags.
                <div>
                    Community:
                    ${render_community_tagging_element( tagged_item=workflow, tag_click_fn='community_tag_click', use_toggle_link=False )}
                    %if len ( workflow.tags ) == 0:
                        none
                    %endif
                </div>
                ## Individual tags.
                <p>
                <div>
                    Yours:
                    ${render_individual_tagging_element( user=trans.get_user(), tagged_item=workflow, elt_context='view.mako', use_toggle_link=False )}
                </div>
            </div>
        </div>
    </div>
</%def>
