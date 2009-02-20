<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if library_dataset == library_dataset.library_dataset_dataset_association.library_dataset:
    <b><i>This is the latest version of this library dataset</i></b>
%else:
    <font color="red"><b><i>This is an expired version of this library dataset</i></b></font>
%endif
<p/>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='browse_library', id=library_id )}"><span>Browse this library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Set version of ${library_dataset.name}</div>
    <div class="toolFormBody">
        <form name="library_dataset_version" action="${h.url_for( controller='admin', action='library_dataset', id=library_dataset.id, library_id=library_id, versions=True )}" method="post">
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <div class="form-row">
                        <input type="radio" name="set_lda_id" value="${library_dataset.library_dataset_dataset_association.id}" checked>${library_dataset.name} (current)
                        <a id="dataset-${library_dataset.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        <div popupmenu="dataset-${library_dataset.id}-popup">
                            <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', id=library_dataset.library_dataset_dataset_association.id, library_id=library_id, information=True )}">Edit this dataset's information</a>
                            <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', id=library_dataset.library_dataset_dataset_association.id, library_id=library_id, permissions=True )}">Edit this dataset's permissions</a>
                            <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', replace_id=library_dataset.id, library_id=library_id )}">Replace this dataset with a new version</a>
                        </div>
                        %for ldda in library_dataset.expired_datasets:
                            <br/>
                            <input type="radio" name="set_lda_id" value="${ldda.id}" >${ldda.name}
                            <a id="ldda-${ldda.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                            <div popupmenu="ldda-${ldda.id}-popup">
                                <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', id=ldda.id, library_id=library_id, information=True )}">Edit this dataset's information</a>
                                <a class="action-button" href="${h.url_for( controller='admin', action='library_dataset_dataset_association', id=ldda.id, library_id=library_id, permissions=True )}">Edit this dataset's permissions</a>
                            </div>
                        %endfor
                    </div>
                </div>
                <div style="clear: both"></div>
            </div>
            %if library_dataset.expired_datasets:
                <div class="form-row">
                    <input type="submit" name="change_version_button" value="Save"/>
                </div>
            %endif
        </form>
    </div>
</div>
