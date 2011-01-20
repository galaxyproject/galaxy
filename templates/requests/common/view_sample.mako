<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/common/template_common.mako" import="render_template_fields" />

<%def name="render_external_service_actions( external_service )">
%if external_service:
    <p>
        <div class="toolForm">
            <div class="toolFormTitle">Available External Service Actions for ${sample.name} at ${external_service.name}</div>
            <div class="toolFormBody">
                    <div class="toolMenu">
                        %for item in external_service.actions:
                            ${ render_external_service_action_group( item ) }
                        %endfor
                    </div>
            </div>
        </div>
    </p>
%endif
</%def>

<%def name="render_external_service_action_group( external_service_group )">
    %if external_service_group.has_action():
        %if external_service_group.label:
            <div class="form-row">
                <div class="toolSectionList">
                    <div class="toolSectionTitle">
                        <span>${external_service_group.label}</span>
                    </div>
                    <div class="toolSectionBody">
                        <div class="toolSectionBg">
        %endif
                        %for item in external_service_group:
                            %if isinstance( item, list ):
                                ${ render_external_service_action_group( item ) }
                            %else:
                                ${ render_external_service_action( item ) }
                            %endif
                        %endfor
        %if external_service_group.label:
                        </div>
                    </div>
                </div>
            </div>
        %endif
    %endif
</%def>

<%def name="render_external_service_action( external_service_action )">
    <%
        if hasattr( external_service_action.action, 'target' ):
            target = external_service_action.action.target
        else:
            target = 'galaxy_main'
    %>
    <div class="toolTitle">
        <a href="${external_service_action.get_action_access_link( trans )}" target="${target}">${external_service_action.label}</a>
    </div>
</%def>

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
%if external_services:
    %for external_service in external_services:
        ${ render_external_service_actions( external_service ) }
    %endfor
%endif
