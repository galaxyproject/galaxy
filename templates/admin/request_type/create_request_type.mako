<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/request_type/common.mako" import="*" />

%if not rt_info_widgets:
    <br/><br/>
    <ul class="manage-table-actions">
        <li><a class="action-button" href="${h.url_for( controller='forms', action='create_form_definition' )}">Create new form</a></li>
    </ul>
    <br/<br/>
    Creating a new request type requires two form definitions, a <b>Sequencing Request Form</b>,
    and a <b>Sequencing Sample Form</b>, which must be created first.  Click the <b>Create new form</b>
    button to create them.
%endif

%if message:
    ${render_msg( message, status )}
%endif

%if rt_info_widgets:
    <form name="create_request_type" action="${h.url_for( controller='request_type', action='create_request_type' )}" method="post">
        <div class="toolForm">
            <div class="toolFormTitle">Create a new request type</div>
            %for rt_info in rt_info_widgets:
                <div class="form-row">
                    <label>${rt_info['label']}</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        ${rt_info['widget'].get_html()}
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endfor
        </div>
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Sample states defined for this request type</div>
            <div class="form-row">
                A request_type requires at least one possible sample state so that it can be used to create a sequencing request
            </div>
            %for index, info in enumerate( rt_states_widgets ):
                ${render_state( index, info[0], info[1] )}
            %endfor
            <div class="form-row">
                <input type="submit" name="add_state_button" value="Add state"/>
            </div>
        </div>
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">External services</div>
            <div class="form-row">
                An external service can be a sequencer or any application that is web accessible.  A request type can be associated with 
                multiple external services.
            </div>
            %for index, external_service_select_field in enumerate( external_service_select_fields_list ):
                ${render_external_services( index, external_service_select_field )}
            %endfor
            <div class="form-row">
                <input type="submit" name="add_external_service_button" value="Add external service"/>
            </div>
        </div>
        <div class="form-row">
            <input type="submit" name="create_request_type_button" value="Save"/>
        </div>
    </form>
%endif
