<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">request Types</%def>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<h2>
    Request Types
</h2>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='request_type', create=True )}"><span>Create a new request type</span></a>
    </li>
</ul>

<div class="grid-header">
    ##<span class="title">Filter:</span>
    %for i, filter in enumerate( ['Active', 'Deleted', 'All'] ):
        %if i > 0:    
            <span>|</span>
        %endif
        %if show_filter == filter:
            <span class="filter"><a href="${h.url_for( controller='admin', action='manage_request_types', show_filter=filter )}"><b>${filter}</b></a></span>
        %else:
            <span class="filter"><a href="${h.url_for( controller='admin', action='manage_request_types', show_filter=filter )}">${filter}</a></span>
        %endif
    %endfor
</div>
%if not request_types:
    There are no request types.
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
                    <td>
                        <a href="${h.url_for( controller='admin', action='request_type', edit='True', id=request_type.id)}">${request_type.name}</a>
                        <a id="request_type-${request_type.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        %if request_type.deleted:
                            <div popupmenu="request_type-${request_type.id}-popup">
                                <a class="action-button" href="${h.url_for( action='undelete_request_type', request_type_id=request_type.id )}">Undelete</a>
                            </div>
                        %else:
                            <div popupmenu="request_type-${request_type.id}-popup">
                                <a class="action-button" confirm="Click OK to delete the request type ${request_type.name}." href="${h.url_for( action='delete_request_type', request_type_id=request_type.id )}">Delete</a>
                            </div>
                        %endif
                    </td>
                    <td><i>${request_type.desc}</i></td>
                    <td><a href="${h.url_for( controller='forms', action='edit', form_id=request_type.request_form.id, read_only=True)}">${request_type.request_form.name}</a></td>
                    <td><a href="${h.url_for( controller='forms', action='edit', form_id=request_type.sample_form.id, read_only=True)}">${request_type.sample_form.name}</a></td> 
               </tr>          
            %endfor
        </tbody>
    </table>
%endif