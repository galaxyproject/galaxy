<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/requests/common/common.mako" import="render_sample_datasets" />
<%namespace file="/requests/common/common.mako" import="common_javascripts" />

<%def name="javascripts()">
   ${parent.javascripts()}
   ${common_javascripts()}
</%def>

<%
    is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
    is_complete = sample.request.is_complete
    is_submitted = sample.request.is_submitted
    can_transfer_datasets = is_admin and sample.untransferred_dataset_files and sample.library and sample.folder
%>

<br/><br/>

<ul class="manage-table-actions">
    %if can_transfer_datasets:
        <li><a class="action-button" href="${h.url_for( controller='requests_admin', action='manage_datasets', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">Manage selected datasets</a></li>
    %endif
    <li><a class="action-button" id="sample-${sample.id}-popup" class="menubutton">Dataset Actions</a></li>
    <div popupmenu="sample-${sample.id}-popup">
        <li><a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( sample.library.id ) )}">View target Data Library</a></li>
        <li><a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( sample.request.id ) )}">Browse this request</a></li>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if sample and sample_datasets:
    ## The list of sample_datasets may not be the same as sample.datasets because it may be
    ## filtered by a transfer_status value.  The value of title changes based on this filter.
    ${render_sample_datasets( cntrller, sample, sample_datasets, title )}
%else:
    %if transfer_status:
        No datasets with status "${transfer_status}" belong to this sample
    %else:
        No datasets have been selected for this sample.
    %endif
%endif
