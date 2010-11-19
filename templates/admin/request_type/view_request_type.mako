<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="request_type-${request_type.id}-popup" class="menubutton">Configuration Actions</a></li>
    <div popupmenu="request_type-${request_type.id}-popup">
        %if not request_type.deleted:
            <li><a class="action-button" href="${h.url_for( controller='sequencer', action='edit_request_type', id=trans.security.encode_id( request_type.id ) )}">Edit configuration</a></li>
            <li><a class="action-button" href="${h.url_for( controller='sequencer', action='request_type_permissions', id=trans.security.encode_id( request_type.id ) )}">Edit permissions</a></li>
            <li><a class="action-button" href="${h.url_for( controller='sequencer', action='delete_request_type', id=trans.security.encode_id( request_type.id ) )}">Delete configuration</a></li>
        %endif
        %if request_type.deleted:
            <li><a class="action-button" href="${h.url_for( controller='sequencer', action='undelete_request_type', id=trans.security.encode_id( request_type.id ) )}">Undelete configuration</a></li>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">"${request_type.name}" sequencer configuration</div>
    <div class="form-row">
        <label>Name:</label>
        ${request_type.name}
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Description:</label>
        ${request_type.desc}
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Sequencing request form definition:</label>
        ## TODO: RC, fix this link
        <a href="${h.url_for( controller='forms', action='manage', operation='view', id=trans.security.encode_id( request_type.request_form_id ) )}">${request_type.request_form.name}</a>
    </div>       
    <div class="form-row">
        <label>Sample form definition:</label>
        ## TODO: RC, fix this link
        <a href="${h.url_for( controller='forms', action='manage', operation='view', id=trans.security.encode_id( request_type.sample_form_id ) )}">${request_type.sample_form.name}</a>
    </div>
</div>
<p/>
<div class="toolForm">
    <div class="toolFormTitle">Sample states defined for this sequencer configuration</div>
    %for state in request_type.states:
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
    <div class="form-row">
        This information is needed only if you will transfer datasets from the sequencer to a target Galaxy data library
    </div>
    <% 
        host = request_type.datatx_info[ 'host' ]
        if not host:
            sequencer_login_info = False
        else:
            sequencer_login_info = True
            username = request_type.datatx_info[ 'username' ]
            password = request_type.datatx_info[ 'password' ]
            data_dir = request_type.datatx_info[ 'data_dir' ]
            rename_dataset = request_type.datatx_info[ 'rename_dataset' ]
    %>
    <div style="clear: both"></div>
    %if sequencer_login_info:
        <div class="form-row">
            <label>Hostname or IP Address:</label>
            ${host}"
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Username:</label>
            ${username}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Password:</label>
            ${password}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Data directory:</label>
            ${data_dir}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Prepend the experiment name and sample name to the dataset name?</label>
            ${rename_dataset}
            <div class="toolParamHelp" style="clear: both;">
                Galaxy datasets are renamed by prepending the experiment name and sample name to the dataset name, ensuring
                dataset names remain unique in Galaxy even when multiple datasets have the same name on the sequencer.
            </div>
        </div>
        <div style="clear: both"></div>
    %else:
        <div class="form-row">
            Sequencer login information is not set, click the <b>Edit configuration</b> button to set it.
        </div>
    %endif
</div>
