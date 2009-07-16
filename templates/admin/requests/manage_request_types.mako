<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">request Types</%def>

<h2>
    %if deleted:
        Deleted 
    %endif
    Request Types
</h2>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='request_type', create=True )}"><span>Create a new request type</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if not request_types:
    %if deleted:
        There are no deleted request types
    %else:
        There are no request types.
    %endif
%else:
    <table class="grid">
        <thead>
            <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Request Form</th>
                <th>Sample Form</th>
            </tr>
        </thead>
        <tbody>
            %for request_type in request_types:    
                <tr>
                    <td><b><a href="${h.url_for( controller='admin', action='request_type', edit='True', id=request_type.id)}">${request_type.name}</a></b></td>
                    <td><i>${request_type.desc}</i></td>
                    <td><a href="${h.url_for( controller='forms', action='edit', form_id=request_type.request_form.id, read_only=True)}">${request_type.request_form.name}</a></td>
                    <td><a href="${h.url_for( controller='forms', action='edit', form_id=request_type.sample_form.id, read_only=True)}">${request_type.sample_form.name}</a></td> 
               </tr>          
            %endfor
        </tbody>
    </table>
%endif