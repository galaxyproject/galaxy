<%inherit file="/base.mako"/>
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/library/common.mako" import="render_available_templates" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%def name="title()">Edit Library Dataset Attributes</%def>

<%
    roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all()
%>


${render_permission_form( dataset, dataset.name, h.url_for( action='library_dataset' ), 'id', dataset.id, roles )}

<div class="toolForm">
    <div class="toolFormTitle">Edit Attributes</div>
    <div class="toolFormBody">
        <form name="edit_attributes" action="${h.url_for( controller='admin', action='library_dataset' )}" method="post">
            <input type="hidden" name="id" value="${dataset.id}"/>
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="${dataset.name}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Info:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="info" value="${dataset.info}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div> 
            <div class="form-row">
                <label>Set Dataset Version:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <div class="form-row">
                    <input type="radio" name="set_lda_id" value="${dataset.library_dataset_dataset_association.id}" checked><a href="${h.url_for( controller='admin', action='dataset', id=dataset.library_dataset_dataset_association.id )}">${dataset.library_dataset_dataset_association.name}</a> (current)
                    %for expired_dataset in dataset.expired_datasets:
                    <br>
                    <input type="radio" name="set_lda_id" value="${expired_dataset.id}" ><a href="${h.url_for( controller='admin', action='dataset', id=expired_dataset.id )}">${expired_dataset.name}</a>
                    %endfor
                    </div>
                    <div class="form-row">
                    Replace this dataset with a new version: <a href="${h.url_for( controller='admin', action='dataset', replace_id=dataset.id )}">upload</a> | from your history
                    </div>
                    <div style="clear: both"></div>
                    
                </div>
                <div style="clear: both"></div>
            </div> 
            <div class="form-row">
                <input type="submit" name="save" value="Save"/>
            </div>
        </form>
    </div>
</div>
<p/>

${render_available_templates( dataset )}