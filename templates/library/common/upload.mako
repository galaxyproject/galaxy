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
   ${h.js("jquery.autocomplete", "autocomplete_tagging" )}
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

<b>Create new data library datasets</b>
%if replace_dataset in [ None, 'None' ]:
    ## Don't allow multiple datasets to be uploaded when replacing a dataset with a new version
    <a id="upload-librarydataset--popup" class="popup-arrow" style="display: none;">&#9660;</a>
    <div popupmenu="upload-librarydataset--popup">
        <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller,library_id=library_id, folder_id=folder_id, replace_id=replace_id, upload_option='upload_file', show_deleted=show_deleted )}">Upload files</a>
        %if ( trans.user_is_admin() and cntrller == 'library_admin' ):
            %if trans.app.config.library_import_dir and os.path.exists( trans.app.config.library_import_dir ):
                <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=library_id, folder_id=folder_id, replace_id=replace_id, upload_option='upload_directory', show_deleted=show_deleted )}">Upload directory of files</a>
            %endif
            %if trans.app.config.allow_library_path_paste:
                <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=library_id, folder_id=folder_id, replace_id=replace_id, upload_option='upload_paths', show_deleted=show_deleted )}">Upload files from filesystem paths</a>
            %endif
        %elif cntrller == 'library':
            %if trans.app.config.user_library_import_dir and os.path.exists( os.path.join( trans.app.config.user_library_import_dir, trans.user.email ) ):
                <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=library_id, folder_id=folder_id, replace_id=replace_id, upload_option='upload_directory', show_deleted=show_deleted )}">Upload directory of files</a>
            %endif
        %endif
        <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=library_id, folder_id=folder_id, replace_id=replace_id, upload_option='import_from_history', show_deleted=show_deleted )}">Import datasets from your current history</a>
    </div>
%endif
<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=library_id, show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

${render_upload_form( cntrller, upload_option, action, library_id, folder_id, replace_dataset, file_formats, dbkeys, widgets, roles, history, show_deleted )}
