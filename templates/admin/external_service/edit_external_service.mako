<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="external_service-${external_service.id}-popup" class="menubutton">External service actions</a></li>
    <div popupmenu="external_service-${external_service.id}-popup">
        %if not external_service.deleted:
            <li><a class="action-button" href="${h.url_for( controller='external_service', action='view_external_service', id=trans.security.encode_id( external_service.id ) )}">Browse external service</a></li>
            <li><a class="action-button" href="${h.url_for( controller='external_service', action='edit_external_service_form_definition', id=trans.security.encode_id( external_service.id ) )}">Edit form definition</a></li>
            <li><a class="action-button" href="${h.url_for( controller='external_service', action='delete_external_service', id=trans.security.encode_id( external_service.id ) )}">Delete external service</a></li>
        %endif
        %if external_service.deleted:
            <li><a class="action-button" href="${h.url_for( controller='external_service', action='undelete_external_service', id=trans.security.encode_id( external_service.id ) )}">Undelete external service</a></li>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<form name="edit_external_service" action="${h.url_for( controller='external_service', action='edit_external_service', id=trans.security.encode_id( external_service.id ) )}" method="post" >
    <div class="toolForm">
        <div class="toolFormTitle">Edit external service</div>
        %for i, field in enumerate( widgets ):
            <div class="form-row">
                <label>${field['label']}:</label>
                ${field['widget'].get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    ${field['helptext']}
                </div>
                <div style="clear: both"></div>
            </div>
        %endfor  
    </div>
    <div class="form-row">
        <input type="submit" name="edit_external_service_button" value="Save"/>
    </div>
</form>
