<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% from galaxy.web.framework.helpers import time_ago %>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( sample.request.id ) )}">Browse this request</a></li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<h3>History of sample "${sample.name}"</h3>

<div class="toolForm">
    <table class="grid">
        <thead>
            <tr>
                <th>State</th>
                <th>Description</th>
                <th>Last Updated</th>
                <th>Comments</th>
            </tr>
        </thead>
        <tbody>
            %for event in sample.events:    
                <tr>
                    <td><b>${event.state.name}</b></td>
                    <td>${event.state.desc}</td>
                    <td>${time_ago( event.update_time )}</td>
                    <td>${event.comment}</td>
                </tr>             
            %endfor
        </tbody>
    </table>
</div>
