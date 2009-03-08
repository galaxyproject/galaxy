<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='browse_library', id=library_id )}"><span>Browse this library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%
    library_item_ids = {}
    if isinstance( library_item, trans.app.model.Library ):
        library_item_type = 'library'
        library_item_desc = 'library'
    elif isinstance( library_item, trans.app.model.LibraryFolder ):
        library_item_ids[ 'folder_id' ] = library_item.id
        library_item_type = 'folder'
        library_item_desc = 'folder'
    elif isinstance( library_item, trans.app.model.LibraryDataset ):
        library_item_ids[ 'library_dataset_id' ] = library_item.id
        library_item_type = 'library_dataset'
        library_item_desc = 'dataset'
    elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
        library_item_ids[ 'ldda_id' ] = library_item.id
        library_item_type = 'library_dataset_dataset_association'
        library_item_desc = 'library dataset'
    # Always pass a library_id
    library_item_ids[ 'library_id' ] = library_id
%>

<div class="toolForm">
    <div class="toolFormTitle">Create a new information template for ${library_item_desc} '${library_item.name}'</div>
    <div class="toolFormBody">
        <div class="form-row">
            <form name="new_info_template" action="${h.url_for( controller='admin', action='info_template', **library_item_ids )}" method="post">
                <input type="hidden" name="new_template" value="True"/>
                Create a new template with <input type="text" size="3" name="num_fields" value="5"/> fields
                <input type="submit" class="primary-button" name="create_info_template_button" id="create_info_template_button" value="Go"/>
            </form>
        </div>
    </div>
</div>
