<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/external_service/common.mako" import="*" />

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="external_service-${external_service.id}-popup" class="menubutton">External service actions</a></li>
    <div popupmenu="external_service-${external_service.id}-popup">
        %if not external_service.deleted:
            <li><a class="action-button" href="${h.url_for( controller='external_service', action='edit_external_service', id=trans.security.encode_id( external_service.id ) )}">Edit external service</a></li>
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

${render_external_service( external_service )}
