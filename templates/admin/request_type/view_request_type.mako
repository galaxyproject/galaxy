<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/common/template_common.mako" import="render_template_fields" />

<% form_type = trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE %>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="request_type-${request_type.id}-popup" class="menubutton">Request type actions</a></li>
    <div popupmenu="request_type-${request_type.id}-popup">
        %if not request_type.deleted:
            <li><a class="action-button" href="${h.url_for( controller='request_type', action='view_editable_request_type', id=trans.security.encode_id( request_type.id ) )}">Edit request type</a></li>
            <li><a class="action-button" href="${h.url_for( controller='request_type', action='request_type_permissions', id=trans.security.encode_id( request_type.id ) )}">Edit permissions</a></li>
            <li><a class="action-button" href="${h.url_for( controller='request_type', action='delete_request_type', id=trans.security.encode_id( request_type.id ) )}">Delete request type</a></li>
            %if not request_type.run_details:
                <a class="action-button" href="${h.url_for( controller='request_type', action='add_template', cntrller='requests_admin', item_type='request_type', form_type=form_type, request_type_id=trans.security.encode_id( request_type.id ) )}">Use run details template</a>
            %elif request_type.run_details:
                <a class="action-button" href="${h.url_for( controller='request_type', action='edit_template', cntrller='requests_admin', item_type='request_type', form_type=form_type, request_type_id=trans.security.encode_id( request_type.id ) )}">Edit run details template</a>
                <a class="action-button" href="${h.url_for( controller='request_type', action='delete_template', cntrller='requests_admin', item_type='request_type', form_type=form_type, request_type_id=trans.security.encode_id( request_type.id ) )}">Unuse run details template</a>
            %endif
        %endif
        %if request_type.deleted:
            <li><a class="action-button" href="${h.url_for( controller='request_type', action='undelete_request_type', id=trans.security.encode_id( request_type.id ) )}">Undelete request type</a></li>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">"${request_type.name}" request type</div>
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
        <a href="${h.url_for( controller='request_type', action='view_form_definition', id=trans.security.encode_id( request_type.request_form_id ) )}">${request_type.request_form.name}</a>
    </div>       
    <div class="form-row">
        <label>Sample form definition:</label>
        <a href="${h.url_for( controller='request_type', action='view_form_definition', id=trans.security.encode_id( request_type.sample_form_id ) )}">${request_type.sample_form.name}</a>
    </div>
</div>
<p/>
<div class="toolForm">
    <div class="toolFormTitle">Sample states defined for this request type</div>
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
    <div class="toolFormTitle">External services</div>
    %if request_type.external_services:
        %for index, external_service in enumerate( request_type.external_services ):
            <div class="form-row">
                <label><a href="${h.url_for( controller='external_service', action='view_external_service', id=trans.security.encode_id( external_service.id ) )}">${external_service.name}</a></label> 
                ${external_service.get_external_service_type( trans ).name}
            </div>
        %endfor
    %else:
        <div class="form-row">
            External service login information is not set.  Select the <b>Edit request type</b> option in the <b>Request type actions</b> menu.
        </div>
    %endif
</div>

%if widgets:
    ${render_template_fields( cntrller='requests_admin', item_type='request_type', widgets=widgets, widget_fields_have_contents=widget_fields_have_contents, request_type_id=trans.security.encode_id( request_type.id ), editable=False )}
%endif
