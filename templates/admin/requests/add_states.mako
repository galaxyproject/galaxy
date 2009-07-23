<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create ${num_states} states for the '${sample_type_name}' request type</div>
    <form name="new_form_fields" action="${h.url_for( controller='admin', action='request_type', save_new=True, create=False, edit=False, name=sample_type_name, description=desc, num_states=num_states, request_form_id=request_form_id, sample_form_id=sample_form_id)}" method="post" >
        <div class="toolFormBody">
            %for element_count in range( num_states ):
                <div class="form-row">
                    <label>${1+element_count}) State name:</label>
                    <input type="text" name="new_element_name_${element_count}" value="" size="40"/>
                    <label>State help text (optional):</label>
                    <input type="text" name="new_element_description_${element_count}" value="" size="40"/>
                </div>
                <div style="clear: both"></div>
            %endfor
        </div>
        <div class="form-row">
            <input type="submit" name="save_new_sample_type" value="Save"/>
        </div>
    </form>
</div>