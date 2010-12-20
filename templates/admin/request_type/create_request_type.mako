<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/requests/common.mako" import="*" />

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
            %for index, info in enumerate( rt_states_widgets ):
                ${render_state( index, info[0], info[1] )}
            %endfor
            <div class="form-row">
                <input type="submit" name="add_state_button" value="Add state"/>
            </div>
        </div>
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Sequencer information</div>
            <div class="form-row">
                This information is needed only if you will transfer datasets from the sequencer to a target Galaxy data library
            </div>
            <div class="form-row">
                <label>Sequencer:</label>
                ${sequencer_select_field.get_html()}
            </div>
        <div class="form-row">
            <input type="submit" name="create_request_type_button" value="Save"/>
        </div>
    </form>
%endif
