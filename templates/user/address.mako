<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<h2>Manage Addresses</h2>
<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller='user', action='new_address')}">
        <span>Add a new address</span></a>
        <a class="action-button"  href="${h.url_for( controller='user', action='index')}">
        <span>User preferences</span></a>
    </li>
</ul>
%if not trans.user.addresses:
    There are no addresses
%else:
<div class="grid-header">
    ##<span class="title">Filter:</span>
    %for i, filter in enumerate( ['Active', 'Deleted', 'All'] ):
        %if i > 0:    
            <span>|</span>
        %endif
        %if show_filter == filter:
            <span class="filter"><a href="${h.url_for( controller='user', action='manage_addresses', show_filter=filter )}"><b>${filter}</b></a></span>
        %else:
            <span class="filter"><a href="${h.url_for( controller='user', action='manage_addresses', show_filter=filter )}">${filter}</a></span>
        %endif
    %endfor
</div>


%if not addresses:
    <label>There are no addresses</label>
%else:
    <div class="toolForm">
        <div class="toolFormBody">
            <% trans.user.refresh() %>
                <table class="grid">
                    <tbody>
                        %for index, address in enumerate(addresses):    
                            <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                                <td>
                                    <div class="form-row">   
                                        <label>${address.desc}</label>
                                        ${address.get_html()}
                                    </div>
                                    <div class="form-row">
                                        <ul class="manage-table-actions">
                                           <li>
                                                %if not address.deleted:
                                                    <a class="action-button"  href="${h.url_for( controller='user', action='edit_address', address_id=address.id, 
                                                                                                 short_desc=address.desc,
                                                                                                 name=address.name, institution=address.institution, 
                                                                                                 address1=address.address, city=address.city, 
                                                                                                 state=address.state, postal_code=address.postal_code, 
                                                                                                 country=address.country, phone=address.phone)}">
                                                                                                 <span>Edit</span></a>
                                                    <a class="action-button"  href="${h.url_for( controller='user', action='delete_address', address_id=address.id)}">
                                                    <span>Delete</span></a>
                                                %else:
                                                    <a class="action-button"  href="${h.url_for( controller='user', action='undelete_address', address_id=address.id)}">
                                                    <span>Undelete</span></a>
                                                %endif
                                                
                                          </li>
                                        </ul>
                                    </div>
                                </td>
                             </tr>             
                        %endfor
                    </tbody>
                </table>
            %endif
        </div>
    </div>
%endif