<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%def name="render_state( element_count, state_name, state_desc )">
    <div class="repeat-group-item">
        <div class="form-row">
            <label>${1+element_count}. State name:</label>
            <input type="text" name="state_name_${element_count}" value="${state_name}" size="40"/>
            <input type="submit" name="remove_state_button" value="Remove state ${1+element_count}"/>
            </div>
            <div class="form-row">
            <label>Description:</label>
            <input type="text" name="state_desc_${element_count}" value="${state_desc}" size="40"/>
            <div class="toolParamHelp" style="clear: both;">
                optional
            </div>
            
        </div>
        <div style="clear: both"></div>
   </div>
</%def>

<div class="toolForm">
    <div class="toolFormTitle">Create a new request type</div>
    %if not rt_info_widgets:
        Create a request & sample form definition first to create a new request type.
    %else:
        <form name="create_request_type" action="${h.url_for( controller='requests_admin', action='create_request_type')}" method="post" >
            %for rt_info in rt_info_widgets:
                <div class="form-row">
                    <label>${rt_info['label']}</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        ${rt_info['widget'].get_html()}
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endfor
            <div class="toolFormTitle">Possible sample states</div>
            %if len(rt_states_widgets):
                %for index, info in enumerate(rt_states_widgets):
                    ${render_state( index, info[0], info[1] )}
                %endfor
            %endif
            <div class="form-row">
                <input type="submit" name="add_state_button" value="Add state"/>
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="new" value="submitted" size="40"/>
                </div>
              <div style="clear: both"></div>
            </div>
            <div class="form-row">
            <input type="submit" name="save_request_type" value="Save"/>
            </div>
        </form>

    %endif
</div>