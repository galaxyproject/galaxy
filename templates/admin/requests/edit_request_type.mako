<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if message:
    ${render_msg( message, status )}
%endif

<% num_states=len(states_list) %>

<div class="toolForm">
    <div class="toolFormTitle">Edit the request type</div>
    <div class="toolFormBody">
        <form name="library" action="${h.url_for( controller='admin', action='request_type', save_changes=True, create=False, id=request_type.id, num_states=num_states )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="${request_type.name}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="description" value="${request_type.desc}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>
                    Request Form definition: 
                </label>
                <select name="form_id">
                    %for form in forms:
                        %if form.id == request_type.request_form_id:
                            <option value="${form.id}" selected>${form.name}</option>
                        %else:
                            <option value="${form.id}">${form.name}</option>
                        %endif
                    %endfor
                </select>
            </div>       
            <div class="form-row">
                <label>
                    Sample Form definition: 
                </label>
                <select name="form_id">
                    %for form in forms:
                        %if form.id == request_type.sample_form_id:
                            <option value="${form.id}" selected>${form.name}</option>
                        %else:
                            <option value="${form.id}">${form.name}</option>
                        %endif
                    %endfor
                </select>
            </div>    
            <div class="toolFormBody">
                %for element_count, state in enumerate(states_list):
                    <div class="form-row">
                        <label>${1+element_count}) State name:</label>
                        <input type="text" name="new_element_name_${element_count}" value="${state.name}" size="40"/>
                        <label>State help text (optional):</label>
                        <input type="text" name="new_element_description_${element_count}" value="${state.desc}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                %endfor
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="new" value="submitted" size="40"/>
                </div>
              <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="edit_request_type_button" value="Save"/>
            </div>
        </form>
    </div>
</div>