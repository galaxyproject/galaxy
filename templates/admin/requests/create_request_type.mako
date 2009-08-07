<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create a new request type</div>
    %if not forms:
        Create a form definition first to create a new request type.
    %else:
        <div class="toolFormBody">
            <form name="create_request_type" action="${h.url_for( controller='admin', action='request_type', add_states=True, create=False, edit=False  )}" method="post" >
                <div class="form-row">
                    <label>Name:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="name" value="New Request Type" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Description:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="description" value="" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>
                        Request Form definition:
                    </label>
                    <select name="request_form_id">
                        %for form in forms:
                            <option value="${form.id}">${form.name}</option>
                        %endfor
                    </select>
                </div>
                <div class="form-row">
                    <label>
                        Sample Form definition:
                    </label>
                    <select name="sample_form_id">
                        %for form in forms:
                            <option value="${form.id}">${form.name}</option>
                        %endfor
                    </select>
                </div>
                <div class="form-row">
                    <label>Number of sample states:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" size="3" name="num_states" value="1"/> 
                    </div>
                </div>           
                <div class="form-row">
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="hidden" name="new" value="submitted" size="40"/>
                    </div>
                  <div style="clear: both"></div>
                </div>
                <div class="form-row">
                <input type="submit" name="create_request_type_button" value="Define states"/>
                </div>
            </form>
        </div>
    %endif
</div>