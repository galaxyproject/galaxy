<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    states_list = request_type.states
    can_edit_permissions = not request_type.deleted
    can_delete = not request_type.deleted
    can_undelete = request_type.deleted
%>

<br/><br/>
<ul class="manage-table-actions">
    %if can_edit_permissions:
        <li><a class="action-button" href="${h.url_for( controller='requests_admin', action='request_type_permissions', id=trans.security.encode_id( request_type.id ) )}">Edit permissions</a></li>
    %endif
    %if can_delete:
        <li><a class="action-button" href="${h.url_for( controller='requests_admin', action='delete_request_type', id=trans.security.encode_id( request_type.id ) )}">Delete</a></li>
    %endif
    %if can_undelete:
        <li><a class="action-button" href="${h.url_for( controller='requests_common', action='undelete_request_type', id=trans.security.encode_id( request_type.id ) )}">Undelete</a></li>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">"${request_type.name}" sequencer configuration</div>
    <div class="form-row">
        <label>Name</label>
        ${request_type.name}
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Description</label>
        ${request_type.desc}
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Request form definition</label>
        ${request_type.request_form.name}
    </div>       
    <div class="form-row">
        <label>Sample form definition</label>
        ${request_type.sample_form.name}
    </div>
</div>
<p/>
<div class="toolForm">
    <div class="toolFormTitle">Sample states defined for this sequencer configuration</div>
    %for state in states_list:
        <div class="form-row">
            <label>${state.name}</label>
            ${state.desc}
        </div>
        <div style="clear: both"></div>
    %endfor
</div>
<p/>
<div class="toolForm">
    <div class="toolFormTitle">Sequencer login information</div>
    <form name="view_request_type" action="${h.url_for( controller='requests_admin', action='create_request_type', rt_id=trans.security.encode_id( request_type.id ))}" method="post" >
        <div class="form-row">
            This information is needed only if you will transfer datasets from the sequencer to a target Galaxy data library
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Hostname or IP Address:</label>
            <input type="text" name="host" value="${request_type.datatx_info['host']}" size="40"/>
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Username:</label>
            <input type="text" name="username" value="${request_type.datatx_info['username']}" size="40"/>
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Password:</label>
            <input type="password" name="password" value="${request_type.datatx_info['password']}" size="40"/>
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Data directory:</label>
            <input type="text" name="data_dir" value="${request_type.datatx_info.get('data_dir', '')}" size="40"/>
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Prepend the experiment name and sample name to the dataset name?</label>
            ${rename_dataset_select_field.get_html()}
            <div class="toolParamHelp" style="clear: both;">
                Galaxy datasets are renamed by prepending the experiment name and sample name to the dataset name, ensuring<br/>
                dataset names remain unique in Galaxy even when multiple datasets have the same name on the sequencer.
            </div>
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <input type="submit" name="save_changes" value="Save changes"/>
        </div>
        <div style="clear: both"></div>
    </form>
</div>
