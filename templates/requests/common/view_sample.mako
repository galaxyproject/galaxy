<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/common/template_common.mako" import="render_template_fields" />

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="sample-${sample.id}-popup" class="menubutton">Sample Actions</a></li>
    <div popupmenu="sample-${sample.id}-popup">
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( sample.request.id ) )}">Browse this request</a>
        %if sample.runs:
            <a class="action-button" href="${h.url_for( controller='requests_common', action='edit_template', cntrller=cntrller, item_type='sample', form_type=trans.app.model.FormDefinition.types.RUN_DETAILS_TEMPLATE, sample_id=trans.security.encode_id( sample.id ) )}">Edit template</a>
            <a class="action-button" href="${h.url_for( controller='requests_common', action='delete_template', cntrller=cntrller, item_type='sample', form_type=trans.app.model.FormDefinition.types.RUN_DETAILS_TEMPLATE, sample_id=trans.security.encode_id( sample.id ) )}">Unuse template</a>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Sample "${sample.name}"</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Name:</label>
            ${sample.name}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Description:</label>
            ${sample.desc}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Barcode:</label>
            ${sample.bar_code}
            <div style="clear: both"></div>
        </div>
        %if sample.library:
            <div class="form-row">
                <label>Library:</label>
                ${sample.library.name}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Folder:</label>
                ${sample.folder.name}
                <div style="clear: both"></div>
            </div>
        %endif
        <div class="form-row">
            <label>Request:</label>
            ${sample.request.name}
            <div style="clear: both"></div>
        </div>
    </div>
</div>

%if widgets:
    ${render_template_fields( cntrller=cntrller, item_type='sample', widgets=widgets, widget_fields_have_contents=widget_fields_have_contents, sample_id=trans.security.encode_id( sample.id ), editable=False )}
%endif
