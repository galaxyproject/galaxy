<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/library_dataset_common.mako" import="render_upload_form" />

<% import os, os.path %>

<%
    if replace_dataset not in [ None, 'None' ]:
        replace_id = replace_dataset.id
    else:
        replace_id = 'None'
%>

<b>Create new data library datasets</b>
<a id="upload-librarydataset--popup" class="popup-arrow" style="display: none;">&#9660;</a>
<div popupmenu="upload-librarydataset--popup">
    <a class="action-button" href="${h.url_for( controller='library', action='upload_library_dataset', library_id=library_id, folder_id=folder_id, replace_id=replace_id, upload_option='upload_file' )}">Upload files</a>
    %if trans.app.config.user_library_import_dir and os.path.exists( os.path.join( trans.app.config.user_library_import_dir, trans.user.email ) ):
        <a class="action-button" href="${h.url_for( controller='library', action='upload_library_dataset', library_id=library_id, folder_id=folder_id, replace_id=replace_id, upload_option='upload_directory' )}">Upload directory of files</a>
    %endif
    <a class="action-button" href="${h.url_for( controller='library', action='upload_library_dataset', library_id=library_id, folder_id=folder_id, replace_id=replace_id, upload_option='import_from_history' )}">Import datasets from your current history</a>
</div>
<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library', action='browse_library', obj_id=library_id )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

${render_upload_form( 'library', upload_option, action, library_id, folder_id, replace_dataset, file_formats, dbkeys, roles, history )}
