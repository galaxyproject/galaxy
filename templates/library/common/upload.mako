<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common/common.mako" import="render_upload_form" />

<% import os, os.path %>

<%
    if replace_dataset not in [ None, 'None' ]:
        replace_id = trans.security.encode_id( replace_dataset.id )
    else:
        replace_id = 'None'
%>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js("jquery.autocomplete", "autocomplete_tagging" )}
    
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
                $( "#upload_library_dataset" ).submit();
            }
        });
    });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
</%def>

<b>Upload files to a data library</b>
<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=library_id, show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

${render_upload_form( cntrller, upload_option, action, library_id, folder_id, replace_dataset, file_formats, dbkeys, space_to_tab, link_data_only, widgets, roles_select_list, history, show_deleted )}
