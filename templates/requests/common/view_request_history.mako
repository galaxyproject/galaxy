<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
    is_complete = request.is_complete
    is_submitted = request.is_submitted
    is_unsubmitted = request.is_unsubmitted
    can_add_samples = is_unsubmitted
    can_edit_request = ( is_admin and not is_complete ) or is_unsubmitted
    can_reject = is_admin and is_submitted
    can_select_datasets = is_admin and ( is_complete or is_submitted )
    can_submit_request = request.samples and is_unsubmitted
%>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="request-${request.id}-popup" class="menubutton">Request Actions</a></li>
    <div popupmenu="request-${request.id}-popup">
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Browse this request</a>
        %if can_edit_request:
            <a class="action-button" href="${h.url_for( controller='requests_common', action='edit_basic_request_info', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Edit this request</a>
        %endif
        %if can_submit_request:
            <a class="action-button" confirm="More samples cannot be added to this request once it is submitted. Click OK to submit." href="${h.url_for( controller='requests_common', action='submit_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Submit this request</a>
        %endif
        %if can_reject:
            <a class="action-button" href="${h.url_for( controller='requests_admin', action='reject_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Reject this request</a>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<h3>History of sequencing request "${request.name}"</h3>

<div class="toolForm">
    <table class="grid">
        <thead>
            <tr>
                <th>State</th>
                <th>Last Update</th>
                <th>Comments</th>
            </tr>
        </thead>
        <tbody>
            %for state, updated, comments in events_list:    
                <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                    <td><b><a>${state}</a></b></td>
                    <td><a>${updated}</a></td>
                    <td><a>${comments}</a></td>
                </tr>             
            %endfor
        </tbody>
    </table>
</div>
