<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/requests/common/common.mako" import="render_sample_datasets" />

<%
    is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
    is_complete = sample.request.is_complete
    is_submitted = sample.request.is_submitted
    can_select_datasets = is_admin and ( is_complete or is_submitted )
    can_transfer_datasets = is_admin and sample.untransferred_dataset_files
%>

<br/><br/>

<ul class="manage-table-actions">
    %if can_transfer_datasets:
        <li><a class="action-button" href="${h.url_for( controller='requests_admin', action='manage_datasets', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">Transfer datasets</a></li>
    %endif
    <li><a class="action-button" href="${h.url_for( controller='requests_common', action='view_selected_datasets', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">Refresh page</a></li>
    <li><a class="action-button" id="sample-${sample.id}-popup" class="menubutton">Dataset Actions</a></li>
    <div popupmenu="sample-${sample.id}-popup">
        %if can_select_datasets:
            <li><a class="action-button" href="${h.url_for( controller='requests_admin', action='select_datasets_to_transfer', cntrller=cntrller, request_id=trans.security.encode_id( sample.request.id ), sample_id=trans.security.encode_id( sample.id ) )}">Select more datasets</a></li>
        %endif
        <li><a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( sample.library.id ) )}">View target Data Library</a></li>
        <li><a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( sample.request.id ) )}">Browse this request</a></li>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if sample and sample.datasets:
    <% title = 'Datasets currently selected for "sample.name"' %>
    ${render_sample_datasets( cntrller, sample, sample.datasets, title )}
%endif
