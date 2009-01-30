<%inherit file="/base.mako"/>
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common.mako" import="render_existing_library_item_info" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%def name="title()">Edit Library Dataset Attributes</%def>

%if trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_MANAGE, dataset ):
    <%namespace file="/dataset/security_common.mako" import="render_permission_form" />
    ${render_permission_form( dataset, dataset.name, h.url_for( action='library_dataset' ), 'id', dataset.id, trans.user.all_roles() )}
%endif

%if trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_MODIFY, dataset ):
<div class="toolForm">
    <div class="toolFormTitle">Edit Attributes</div>
    <div class="toolFormBody">
        <form name="edit_attributes" action="${h.url_for( controller='library', action='library_dataset' )}" method="post">
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
                    <input type="radio" name="set_lda_id" value="${dataset.library_dataset_dataset_association.id}" checked><a href="${h.url_for( controller='root', action='edit', lid=dataset.library_dataset_dataset_association.id )}">${dataset.library_dataset_dataset_association.name}</a> (current)
                    %if refered_lda == dataset.library_dataset_dataset_association:
                        (your version)
                    %endif
                    %for expired_dataset in dataset.expired_datasets:
                    <br>
                    <input type="radio" name="set_lda_id" value="${expired_dataset.id}" ><a href="${h.url_for( controller='root', action='edit', lid=expired_dataset.id )}">${expired_dataset.name}</a>
                    %if refered_lda == expired_dataset:
                        (your version)
                    %endif
                    %endfor
                    </div>
                    <div class="form-row">
                        Click <a href="${h.url_for( controller='library', action='dataset', replace_id=dataset.id )}">here</a> to replace this dataset with a new version.
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
%else:
    <div class="toolForm">
        <div class="toolFormTitle">View Attributes</div>
        <div class="toolFormBody">
            <div class="form-row">
                <b>Name:</b> ${dataset.name}
                <div style="clear: both"></div>
                <b>Info:</b> ${dataset.info}
                <div style="clear: both"></div>
                <b>Dataset Versions:</b>
                <div style="clear: both"></div>
                    <a href="${h.url_for( controller='root', action='edit', lid=dataset.library_dataset_dataset_association.id )}">${dataset.library_dataset_dataset_association.name}</a> (current)
                    %if refered_lda == dataset.library_dataset_dataset_association:
                        (your version)
                    %endif
                    %for expired_dataset in dataset.expired_datasets:
                    <br>
                    <a href="${h.url_for( controller='root', action='edit', lid=expired_dataset.id )}">${expired_dataset.name}</a>
                    %if refered_lda == expired_dataset:
                        (your version)
                    %endif
                    %endfor
                    </div>
                        <div style="clear: both"></div>
            </div> 
        </div>
    </div>
    <p />

%endif
<p/>

${render_existing_library_item_info( dataset )}
