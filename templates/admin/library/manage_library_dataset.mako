<%inherit file="/base.mako"/>
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/library/common.mako" import="render_available_templates" />

<%
    roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all()
%>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Set version of ${library_dataset.library_dataset_dataset_association.name}</div>
    <div class="toolFormBody">
        <form name="library_dataset_version" action="${h.url_for( controller='admin', action='library_dataset' )}" method="post">
            <input type="hidden" name="id" value="${library_dataset.id}"/>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <div class="form-row">
                        <input type="radio" name="set_lda_id" value="${library_dataset.library_dataset_dataset_association.id}" checked><a href="${h.url_for( controller='admin', action='dataset', ldda_id=library_dataset.library_dataset_dataset_association.id )}">${library_dataset.library_dataset_dataset_association.name}</a> (current)
                        <a id="dataset-${library_dataset.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        <div popupmenu="dataset-${library_dataset.id}-popup">
                            <a class="action-button" href="${h.url_for( controller='admin', action='dataset', replace_id=library_dataset.id )}">Replace this dataset with a new version</a>
                        </div>
                        %for expired_dataset in library_dataset.expired_datasets:
                            <br/>
                            <input type="radio" name="set_lda_id" value="${expired_dataset.id}" ><a href="${h.url_for( controller='admin', action='dataset', ldda_id=expired_dataset.id )}">${expired_dataset.name}</a>
                        %endfor
                    </div>
                </div>
                <div style="clear: both"></div>
            </div>
            %if library_dataset.expired_datasets:
                <div class="form-row">
                    <input type="submit" name="change_version" value="Save"/>
                </div>
            %endif
        </form>
    </div>
</div>
<p/>

${render_permission_form( library_dataset, library_dataset.library_dataset_dataset_association.name, h.url_for( controller='admin', action='library_dataset' ), 'id', library_dataset.id, roles )}

<div class="toolForm">
    <div class="toolFormTitle">Edit Attributes for ${library_dataset.library_dataset_dataset_association.name}</div>
    <div class="toolFormBody">
        <form name="edit_attributes" action="${h.url_for( controller='admin', action='library_dataset' )}" method="post">
            <input type="hidden" name="id" value="${library_dataset.id}"/>
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="${library_dataset.name}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Info:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="info" value="${library_dataset.info}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div> 
            <div class="form-row">
                <input type="submit" name="edit_attributes_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
<p/>

${render_available_templates( library_dataset.library_dataset_dataset_association )}
