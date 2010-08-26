<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common/common.mako" import="render_template_fields" />

<%def name="javascripts()">
    ${parent.javascripts()}
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
                $( "#edit_info" ).submit();
            }
        });
    });
    </script>
</%def>

<%
    from cgi import escape
    if trans.user_is_admin() and cntrller == 'library_admin':
        can_add = can_modify = can_manage = True
    elif cntrller in [ 'library', 'requests' ]:
        can_add = trans.app.security_agent.can_add_library_item( current_user_roles, library )
        can_modify = trans.app.security_agent.can_modify_library_item( current_user_roles, library )
        can_manage = trans.app.security_agent.can_manage_library_item( current_user_roles, library )
    else:
        can_add = can_modify = can_manage = False
    library_name = escape( str( library.name ), quote=True )
    library_description = escape( str( library.description ), quote=True )
    library_synopsis = escape( str( library.synopsis ), quote=True )
%>

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">
        <a href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}"><b>${library.name[:50]}</b></a>
        %if can_add or can_modify or can_manage:
            <a id="library-${library.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            <div popupmenu="library-${library.id}-popup">
                %if not library.deleted:
                    %if can_add and not library.info_association:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type='library', library_id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Add template</a>
                    %endif
                    %if can_manage:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='library_permissions', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">Edit permissions</a>
                    %endif
                    %if can_modify:
                        <a class="action-button" confirm="Click OK to delete the library named '${library.name}'." href="${h.url_for( controller='library_common', action='delete_library_item', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_id=trans.security.encode_id( library.id ), item_type='library' )}">Delete this data library</a>
                    %endif
                %elif can_modify and not library.purged:
                    <a class="action-button" href="${h.url_for( controller='library_common', action='undelete_library_item', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), item_id=trans.security.encode_id( library.id ), item_type='library' )}">Undelete this data library</a>
                %elif library.purged:
                    <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), use_panels=use_panels, show_deleted=show_deleted )}">This data library has been purged</a>
                %endif
            </div>
        %endif
    </div>
    <div class="toolFormBody">
        %if not library.deleted and can_modify:
            <form name="library" action="${h.url_for( controller='library_common', action='library_info', id=trans.security.encode_id( library.id ), cntrller=cntrller, use_panels=use_panels, show_deleted=show_deleted )}" method="post" >
                <div class="form-row">
                    <label>Name:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="name" value="${library_name}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Description:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="description" value="${library_description}" size="40"/>
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        Displayed when browsing all libraries
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Synopsis:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="synopsis" value="${library_synopsis}" size="40"/>
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        Displayed when browsing this library
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <input type="submit" name="library_info_button" value="Save"/>
                </div>
            </form>
        %else:
            <div class="form-row">
                <label>Name:</label>
                ${library_name}
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Description:</label>
                ${library_description}
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Synopsis:</label>
                ${library_synopsis}
            </div>
            <div style="clear: both"></div>
        %endif
    </div>
</div>

%if widgets:
    ${render_template_fields( cntrller=cntrller, item_type='library', library_id=trans.security.encode_id( library.id ), widgets=widgets, widget_fields_have_contents=widget_fields_have_contents, info_association=info_association, inherited=inherited, editable=not( library.deleted ) )}
%endif
