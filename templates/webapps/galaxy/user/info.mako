<%inherit file="/base.mako"/>
<%namespace file="/user/info.mako" import="render_user_info" />
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

${render_user_info()}

%if user.values or user_info_forms:
    <p></p>
    <div class="toolForm">
        <form name="user_info" id="user_info" action="${h.url_for( controller='user', action='edit_info', cntrller=cntrller, user_id=trans.security.encode_id( user.id ) )}" method="post" >
            <div class="toolFormTitle">User information</div>
            %if user_type_fd_id_select_field and len( user_type_fd_id_select_field.options ) > 1:
                <div class="form-row">
                    <label>User type:</label>
                    ${user_type_fd_id_select_field.get_html()}
                </div>
            %else:
                <input type="hidden" name="user_type_fd_id" value="${trans.security.encode_id( user_type_form_definition.id )}"/>
            %endif
            %for field in widgets:
                <div class="form-row">
                    <label>${field['label']}:</label>
                    ${field['widget'].get_html()}
                    <div class="toolParamHelp" style="clear: both;">
                        ${field['helptext']}
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endfor
            <div class="form-row">
                <input type="submit" name="edit_user_info_button" value="Save"/>
            </div>
        </form>
    </div>
    <p></p>
%endif

<p/>

<div class="toolForm">
    <form name="user_addresses" id="user_addresses" action="${h.url_for( controller='user', action='new_address', cntrller=cntrller, user_id=trans.security.encode_id( user.id ) )}" method="post" >
        <div class="toolFormTitle">User Addresses</div>
        <div class="toolFormBody">
            %if user.addresses:
                <div class="form-row">
                <div class="grid-header">
                    %for i, filter in enumerate( ['Active', 'Deleted', 'All'] ):
                        %if i > 0:    
                            <span>|</span>
                        %endif
                        %if show_filter == filter:
                            <span class="filter"><a href="${h.url_for( controller='user', action='manage_user_info', cntrller=cntrller, show_filter=filter, user_id=trans.security.encode_id( user.id ) )}"><b>${filter}</b></a></span>
                        %else:
                            <span class="filter"><a href="${h.url_for( controller='user', action='manage_user_info', cntrller=cntrller, show_filter=filter, user_id=trans.security.encode_id( user.id ) )}">${filter}</a></span>
                        %endif
                    %endfor
                </div>
                </div>
                <table class="grid">
                    <tbody>
                        %for index, address in enumerate(addresses):    
                            <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                                <td>
                                    <div class="form-row">   
                                        <label>${address.desc}:</label>
                                        ${address.get_html()}
                                    </div>
                                    <div class="form-row">
                                        <ul class="manage-table-actions">
                                            <li>
                                                %if not address.deleted:
                                                    <a class="action-button"  href="${h.url_for( controller='user', action='edit_address', cntrller=cntrller, address_id=trans.security.encode_id( address.id ), user_id=trans.security.encode_id( user.id ) )}">Edit</a>
                                                    <a class="action-button"  href="${h.url_for( controller='user', action='delete_address', cntrller=cntrller, address_id=trans.security.encode_id( address.id ), user_id=trans.security.encode_id( user.id ) )}">Delete</a>
                                                %else:
                                                    <a class="action-button"  href="${h.url_for( controller='user', action='undelete_address', cntrller=cntrller, address_id=trans.security.encode_id( address.id ), user_id=trans.security.encode_id( user.id ) )}">Undelete</a>
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
            <div class="form-row">
                <input type="submit" value="Add a new address">
            </div>
        </div>
    </form>
</div>
