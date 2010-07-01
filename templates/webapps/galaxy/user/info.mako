<%inherit file="/base.mako"/>
<%namespace file="/user/info.mako" import="render_user_info" />
<%namespace file="/message.mako" import="render_msg" />

<script type="text/javascript">
$( function() {
    $( "select[refresh_on_change='true']").change( function() {
        var refresh = false;
        var refresh_on_change_values = $( this )[0].attributes.getNamedItem( 'refresh_on_change_values' )
        if ( refresh_on_change_values ) {
            refresh_on_change_values = refresh_on_change_values.value.split( ',' );
            var last_selected_value = $( this )[0].attributes.getNamedItem( 'last_selected_value' );
            for( i= 0; i < refresh_on_change_values.length; i++ ) {
                if ( $( this )[0].value == refresh_on_change_values[i] || ( last_selected_value && last_selected_value.value == refresh_on_change_values[i] ) ){
                    refresh = true;
                    break;
                }
            }
        }
        else {
            refresh = true;
        }
        if ( refresh ){
            $( "#user_info" ).submit();
        }
    });
});
</script>

%if message:
    ${render_msg( message, status )}
%endif

${render_user_info()}

%if user.values or user_info_forms:
    <p></p>
    <div class="toolForm">
        <form name="user_info" id="user_info" action="${h.url_for( controller='user', action='edit_info', user_id=user.id, admin_view=admin_view )}" method="post" >
            <div class="toolFormTitle">User information</div>
            %if user_info_select:
                <div class="form-row">
                    <label>User type:</label>
                    ${user_info_select.get_html()}
                </div>
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
            %if not user_info_select:
                <input type="hidden" name="user_info_select" value="${user_info_form.id}"/>
            %endif  
        
            <div class="form-row">
                <input type="submit" name="edit_user_info_button" value="Save"/>
            </div>
        </form>
    </div>
    <p></p>
%endif

<p/>

<div class="toolForm">
    <form name="user_addresses" id="user_addresses" action="${h.url_for( controller='user', action='new_address', user_id=user.id, admin_view=admin_view )}" method="post" >
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
                            <span class="filter"><a href="${h.url_for( controller='user', action='show_info', show_filter=filter, user_id=user.id, admin_view=admin_view )}"><b>${filter}</b></a></span>
                        %else:
                            <span class="filter"><a href="${h.url_for( controller='user', action='show_info', show_filter=filter, user_id=user.id, admin_view=admin_view )}">${filter}</a></span>
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
                                                    <a class="action-button"  href="${h.url_for( controller='user', action='edit_address', admin_view=admin_view, address_id=address.id, user_id=user.id  )}"><span>Edit</span></a>
                                                    <a class="action-button"  href="${h.url_for( controller='user', action='delete_address', admin_view=admin_view, address_id=address.id, user_id=user.id)}"><span>Delete</span></a>
                                                %else:
                                                    <a class="action-button"  href="${h.url_for( controller='user', action='undelete_address', admin_view=admin_view, address_id=address.id, user_id=user.id)}"><span>Undelete</span></a>
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

<p/>

%if trans.app.config.enable_api:
    <div class="toolForm">
        <form name="user_api_keys" id="user_api_keys" action="${h.url_for( controller='user', action='new_api_key', user_id=user.id, admin_view=admin_view )}" method="post" >
            <div class="toolFormTitle">Web API Key</div>
            <div class="toolFormBody">
                <div class="form-row">
                    <label>Current API key:</label>
                    %if user.api_keys:
                        ${user.api_keys[0].key}
                    %else:
                        none set
                    %endif
                </div>
                <div class="form-row">
                    <input type="submit" name="new_api_key_button" value="Generate a new key now"/>
                    %if user.api_keys:
                        (invalidates old key)
                    %endif
                    <div class="toolParamHelp" style="clear: both;">
                        An API key will allow you to access Galaxy via its web
                        API (documentation forthcoming).  Please note that
                        <strong>this key acts as an alternate means to access
                        your account, and should be treated with the same care
                        as your login password</strong>.
                    </div>
                </div>
            </div>
        </form>
    </div>
%endif
