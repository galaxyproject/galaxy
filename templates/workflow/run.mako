<%inherit file="/base.mako"/>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "jquery.autocomplete", "jquery.tipsy" )}
    <script type="text/javascript">
        $( function() {
            function show_tool_body(title){
                title.parent().show().css('border-bottom-width', '1px');
                title.next().show('fast');
                if ('${hide_fixed_params}'.toLowerCase() == 'true') {
                    // show previously hidden parameters
                    title.next().children(".form-row").show();
                }
            }
            function hide_tool_body(title){
                title.parent().css('border-bottom-width', '0px');
                title.next().hide('fast');
            }
            function toggle_tool_body(title) {
                if (title.next().is(':visible')){
                    hide_tool_body(title);
                }else{
                    show_tool_body(title);
                }
            }
            function toggle_multiinput(select) {
                var placeholder;
                if (select.attr('multiple')) {
                    $('.multiinput').removeClass('disabled');
                    if (select.val()) {
                        select.val(select.val()[0]);
                    } else {
                        select.val($('option:last', select).val());
                    }
                    select.removeAttr('multiple').removeAttr('size');
                    placeholder = 'type to filter';
                } else {
                    $('.multiinput').addClass('disabled');
                    $('.multiinput', select.closest('.form-row')).removeClass('disabled');
                    select.attr('multiple', 'multiple').attr('size', 8);
                    placeholder = 'type to filter, [enter] to select all';
                }
                $('input.multiinput-filter', select.parent()).attr(
                    'placeholder', placeholder);
            }
            $( "select[refresh_on_change='true']").change( function() {
                $( "#tool_form" ).submit();
            });
            $("div.toolFormTitle").click(function(){
                toggle_tool_body($(this));
            });
            if ('${hide_fixed_params}'.toLowerCase() == 'true') {
                // hide parameters that are not runtime inputs
                $("div.form-row:not(:has(select, textarea, input[type!=hidden], .wfpspan))").hide();
                $("div.toolForm:not(:has(select, textarea, input[type!=hidden], .wfpspan))").hide();
            }
            else {
                // Collapse non-interactive run-workflow panels by default.
                $("div.toolFormBody:not(:has(select, textarea, input[type!=hidden], .wfpspan))").hide().parent().css('border-bottom-width', '0px');
            }
            $("#show_all_tool_body").click(function(){
                $("div.toolFormTitle").each(function(){
                    show_tool_body($(this));
                });
            });
            $("#hide_all_tool_body").click(function(){
                $("div.toolFormTitle").each(function(){
                    hide_tool_body($(this));
                });
            });
            $("#new_history_cbx").click(function(){
                $("#new_history_input").toggle(this.checked);
            });
            $('span.multiinput_wrap select[name*="|input"]').removeAttr('multiple').each(function(i, s) {
                var select = $(s);
                var new_width = Math.max(200, select.width()) + 20;
                // Find the label for this element.
                select.closest('.form-row').children('label').append(
                    $('<span class="icon-button multiinput"></span>').click(function() {
                        if ($(this).hasClass('disabled')) return;
                        toggle_multiinput(select);
                        select.focus();
                    }).attr('original-title',
                            'Enable/disable selection of multiple input ' +
                            'files. Each selected file will have an ' +
                            'instance of the workflow.').tipsy({gravity:'s'})
                );
                var filter = $('<input type="text" class="multiinput-filter" ' +
                               'placeholder="type to filter">');
                var filter_timeout = false;
                var original_rows = select.find('option');
                var previous_filter = '';
                // Todo: might have to choose keypress, depending on browser
                filter.keydown(function(e) {
                    var filter_select = function() {
                        var f = $.trim(filter.val());
                        var filtered_rows = original_rows;
                        if (f.length >= 1) {
                            filtered_rows = original_rows.filter(function() {
                                return new RegExp(f, 'ig').test($(this).text());
                            });
                        }
                        select.html('');
                        select.html(filtered_rows);
                    };
                    if (e.which == 13) { // 13 = enter key
                        e.preventDefault();
                        multi = select.attr('multiple');
                        if (typeof multi !== 'undefined' && multi !== false) {
                            if (!select.find('option:not(:selected)').length) {
                                select.find('option').removeAttr('selected');
                            } else {
                                select.find('option').attr('selected', 'selected');
                            }
                        }
                        return;
                    }
                    if (filter.val() != previous_filter) {
                        if (filter_timeout) clearTimeout(filter_timeout);
                        timeout = setTimeout(filter_select, 300);
                        previous_filter = filter.val();
                    }
                }).width(new_width).css('display', 'block');
                select.after(filter);
                select.width(new_width);
            });
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
    <style type="text/css">
    #new_history_p{
        line-height:2.5em;
        margin:0em 0em .5em 0em;
    }
    #new_history_cbx{
        margin-right:.5em;
    }
    #new_history_input{
        display:none;
        line-height:1em;
    }
    #ec_button_container{
        float:right;
    }
    div.toolForm{
        margin-top: 10px;
        margin-bottom: 10px;
    }
    div.toolFormTitle{
        cursor:pointer;
    }
    .title_ul_text{
        text-decoration:underline;
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
import re
import colorsys
import random

used_accumulator = []

wf_parms = {}
for step in steps:
    for v in [ActionBox.get_short_str(pja) for pja in step.post_job_actions] + step.state.inputs.values():
        if isinstance(v, basestring):
            for rematch in re.findall('\$\{.+?\}', v):
                if rematch[2:-1] not in wf_parms:
                    wf_parms[rematch[2:-1]] = ""
if wf_parms:
    hue_offset = 1.0 / len(wf_parms)
    hue = 0.0
    for k in wf_parms.iterkeys():
        wf_parms[k] = "#%X%X%X" % tuple([int(x * 255) for x in colorsys.hsv_to_rgb(hue, .1, .9)])
        hue += hue_offset
%>

<%def name="do_inputs( inputs, values, errors, prefix, step, other_values = None, already_used = None )">
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
            ${do_inputs( input.inputs, repeat_values[ i ], rep_errors,  prefix + input.name + "_" + str(index) + "|", step, other_values, already_used )}
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
      ${row_for_param( input.test_param, group_values[ input.test_param.name ], other_values, group_errors, prefix, step, already_used )}
      ${do_inputs( input.cases[ current_case ].inputs, group_values, group_errors, new_prefix, step, other_values, already_used )}
    %else:
      ${row_for_param( input, values[ input.name ], other_values, errors, prefix, step, already_used )}
    %endif
  %endfor
</%def>

<%def name="row_for_param( param, value, other_values, error_dict, prefix, step, already_used )">
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
                        value = other_values[ param.name ] = param.get_initial_value_from_history_prevent_repeats( t, other_values, already_used )
                        if not enable_unique_defaults:
                            del already_used[:]
                    %>
                    %if step.type == 'data_input':
                    ##Input Dataset Step, wrap for multiinput.
                        <span class='multiinput_wrap'>
                        ${param.get_html_field( t, value, other_values ).get_html( str(step.id) + "|" + prefix )}
                        </span>
                    %else:
                        ${param.get_html_field( t, value, other_values ).get_html( str(step.id) + "|" + prefix )}
                    %endif

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
                <%
                    value = other_values[ param.name ] = param.get_initial_value_from_history_prevent_repeats( t, other_values, already_used )
                    if not enable_unique_defaults:
                        del already_used[:]
                %>
                ${param.get_html_field( t, value, other_values ).get_html( str(step.id) + "|" + prefix )}
                <input type="hidden" name="${step.id}|__runtime__${prefix}${param.name}" value="true" />
            %else:
                <%
                p_text = param.value_to_display_text( value, app )
                replacements = []
                if isinstance(p_text, basestring):
                    for rematch in re.findall('\$\{.+?\}', p_text):
                        replacements.append('wf_parm__%s' % rematch[2:-1])
                        p_text = p_text.replace(rematch, '<span style="background-color:%s" class="wfpspan wf_parm__%s">%s</span>' % (wf_parms[rematch[2:-1]], rematch[2:-1], rematch[2:-1]))
                %>
                %if replacements:
                    <span style="display:none" class="parm_wrap ${' '.join(replacements)}">
                    ${param.get_html_field( t, value, other_values ).get_html( str(step.id) + "|" + prefix )}
                    </span>
                    <span class="p_text_wrapper">${p_text}</span>
                    <input type="hidden" name="${step.id}|__runtime__${prefix}${param.name}" value="true" />
                %else:
                    ${param.value_to_display_text( value, app )}
                %endif
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

<div id='ec_button_container'>
    <span class="action-button" id="show_all_tool_body">Expand All</span>
    <span class="action-button" id="hide_all_tool_body">Collapse</span>
</div>

<h2>Running workflow "${h.to_unicode( workflow.name )}"</h2>

%if has_upgrade_messages:
<div class="warningmessage">
    Problems were encountered when loading this workflow, likely due to tool
    version changes. Missing parameter values have been replaced with default.
    Please review the parameter values below.
</div>
%endif

%if workflow.annotation:
    <div class="workflow-annotation">${workflow.annotation}</div>
    <hr/>
%endif

<form id="tool_form" name="tool_form" method="POST">
## <input type="hidden" name="workflow_name" value="${h.to_unicode( workflow.name ) | h}" />


%if wf_parms:
<div class="metadataForm">
    <div class="metadataFormTitle">Workflow Parameters</div>
    <div class="metadataFormBody">
    %for parm in wf_parms:
        <div class='form-row'><label style='width:100px;'>${parm}<input style="border:2px solid ${wf_parms[parm]};border-left-width:8px;" type="text" class='wf_parm_input ptag_${parm}' name="wf_parm|${parm}" value=""/></label></div>
    %endfor
    </div>
</div>
    <script type="text/javascript">
    // Set the change hooks for workflow parameters.
    $(document).ready(function () {
        $('.wf_parm_input').bind('change keypress keyup', function(event){
            // DBTODO This is probably not reliable.  Ensure we have the right class.
            var new_text = $(this).val();
            if (new_text === ''){
                var tag_id = $(this).attr("class").split(' ')[1].substring(5);
                // Set text properly.
                $('.wfpspan.wf_parm__'+tag_id).text(tag_id);
            }else{
                var tag_id = $(this).attr("class").split(' ')[1].substring(5);
                // Set text properly.
                $('.wfpspan.wf_parm__'+tag_id).text(new_text);
                // Now set the hidden input to the generated text.
                $('.wfpspan.wf_parm__'+tag_id).not('.pja_wfp').each(function(){
                    var new_text = $(this).parent().text();
                    $(this).parent().siblings().children().val(new_text);
                });
            }
        });
    });
    </script>
%endif
%for i, step in enumerate( steps ):
    %if step.type == 'tool' or step.type is None:
      <%
        tool = trans.app.toolbox.get_tool( step.tool_id )
      %>
      <input type="hidden" name="${step.id}|tool_state" value="${step.state.encode( tool, app )}">
      <div class="toolForm">
          <div class="toolFormTitle">
              <span class='title_ul_text'>Step ${int(step.order_index)+1}: ${tool.name}</span>
              % if step.annotations:
                <div class="step-annotation">${h.to_unicode( step.annotations[0].annotation )}</div>
              % endif
          </div>
          <div class="toolFormBody">
                ${do_inputs( tool.inputs, step.state.inputs, errors.get( step.id, dict() ), "", step, None, used_accumulator )}
                % if step.post_job_actions:
                    <hr/>
                    <div class='form-row'>
                    % if len(step.post_job_actions) > 1:
                        <label>Actions:</label>
                    % else:
                        <label>Action:</label>
                    % endif
                    <%
                    pja_ss_all = []
                    for pja_ss in [ActionBox.get_short_str(pja) for pja in step.post_job_actions]:
                        for rematch in re.findall('\$\{.+?\}', pja_ss):
                            pja_ss = pja_ss.replace(rematch, '<span style="background-color:%s" class="wfpspan wf_parm__%s pja_wfp">%s</span>' % (wf_parms[rematch[2:-1]], rematch[2:-1], rematch[2:-1]))
                        pja_ss_all.append(pja_ss)
                    %>
                    ${'<br/>'.join(pja_ss_all)}
                    </div>
                % endif
              </div>
          </div>
        %else:
        <% module = step.module %>
          <input type="hidden" name="${step.id}|tool_state" value="${module.encode_runtime_state( t, step.state )}">
          <div class="toolForm">
              <div class="toolFormTitle">
                  <span class='title_ul_text'>Step ${int(step.order_index)+1}: ${module.name}</span>
                  % if step.annotations:
                    <div class="step-annotation">${step.annotations[0].annotation}</div>
                  % endif
          </div>
          <div class="toolFormBody">
              <%
              # Filter possible inputs to data types that are valid for subsequent steps
              type_filter = []
              for oc in step.output_connections:
                  for ic in oc.input_step.module.get_data_inputs():
                      if 'extensions' in ic and ic['name'] == oc.input_name:
                          type_filter += ic['extensions']
              if not type_filter:
                  type_filter = ['data']
              %>
              ${do_inputs( module.get_runtime_inputs(type_filter), step.state.inputs, errors.get( step.id, dict() ), "", step, None, used_accumulator )}
          </div>
      </div>
    %endif
%endfor
%if missing_tools:
    <div class='errormessage'>
    <strong>This workflow utilizes tools which are unavailable, and cannot be run.  Enable the tools listed below, or <a href="${h.url_for( action='editor', id=trans.security.encode_id(workflow.id) )}" target="_parent">edit the workflow</a> to correct these errors.</strong><br/>
    <ul>
    %for i, tool in enumerate( missing_tools ):
        <li>${tool}</li>
    %endfor
    </ul>
%else:
    %if history_id is None:
<p id='new_history_p'>
    <input type="checkbox" name='new_history' value="true" id='new_history_cbx'/><label for='new_history_cbx'>Send results to a new history </label>
    <span id="new_history_input">named: <input type='text' name='new_history_name' value='${h.to_unicode( workflow.name )}'/></span>
</p>
    %endif
<input type="submit" name="run_workflow" value="Run workflow" />
</form>
%endif
