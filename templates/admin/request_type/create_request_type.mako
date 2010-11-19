<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/requests/common.mako" import="*" />

%if message:
    ${render_msg( message, status )}
%endif


%if not rt_info_widgets:
    <br/><br/>
    <ul class="manage-table-actions">
        <li><a class="action-button" href="${h.url_for( controller='forms', action='create_form' )}">Create new form</a></li>
    </ul>
    <br/<br/>
    Creating a new sequencer configuration requires two form definitions, a <b>Sequencing Request Form</b>,
    and a <b>Sequencing Sample Form</b>, which must be created first.  Click the <b>Create new form</b>
    button to create them.
%else:
    <form name="create_request_type" action="${h.url_for( controller='sequencer', action='create_request_type')}" method="post" >
        <div class="toolForm">
            <div class="toolFormTitle">Create a new sequencer configuration</div>
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
            <div class="toolFormTitle">Sample states defined for this sequencer configuration</div>
            %for index, info in enumerate( rt_states_widgets ):
                ${render_state( index, info[0], info[1] )}
            %endfor
            <div class="form-row">
                <input type="submit" name="add_state_button" value="Add state"/>
            </div>
        </div>
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Sequencer login information</div>
            <div class="form-row">
                This information is needed only if you will transfer datasets from the sequencer to a target Galaxy data library
            </div>
            <div class="form-row">
                <label>Hostname or IP Address:</label>
                <input type="text" name="host" value="" size="40"/>
            </div>
            <div class="form-row">
                <label>Username:</label>
                <input type="text" name="username" value="" size="40"/>
            </div>
            <div class="form-row">
                <label>Password:</label>
                <input type="password" name="password" value="" size="40"/>
            </div>
            <div class="form-row">
                <label>Data directory:</label>
                <input type="text" name="data_dir" value="" size="40"/>
            </div>
            <div class="form-row">
                <label>Prepend the experiment name and sample name to the dataset name?</label>
                ${rename_dataset_select_field.get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    Galaxy datasets are renamed by prepending the experiment name and sample name to the dataset name, ensuring
                    dataset names remain unique in Galaxy even when multiple datasets have the same name on the sequencer.
                </div>
            </div>
        </div>
        <div class="form-row">
            <input type="submit" name="create_request_type_button" value="Save"/>
        </div>
    </form>
%endif
