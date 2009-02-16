<%inherit file="/base.mako"/>
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common.mako" import="render_available_templates" />
<%namespace file="/library/common.mako" import="render_existing_library_item_info" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

library_dataset: ${library_dataset}

<%def name="title()">Edit Library Dataset Attributes</%def>

%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=library_dataset ):
    <%namespace file="/dataset/security_common.mako" import="render_permission_form" />
    ${render_permission_form( library_dataset, library_dataset.name, h.url_for( action='library_dataset' ), 'id', library_dataset.id, trans.user.all_roles() )}
%endif

%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=library_dataset ):
    <div class="toolForm">
        <div class="toolFormTitle">Edit attributes of ${library_dataset.name}</div>
        <div class="toolFormBody">
            <form name="edit_attributes" action="${h.url_for( controller='library', action='library_dataset', id=library_dataset.id, library_id=library_id )}" method="post">
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
                    <label>Set Dataset Version:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <div class="form-row">
                        <input type="radio" name="set_lda_id" value="${library_dataset.library_dataset_dataset_association.id}" checked><a href="${h.url_for( controller='library', action='library_dataset_dataset_association', id=library_dataset.library_dataset_dataset_association.id, library_id=library_id )}">${library_dataset.name}</a> (current)
                        %if refered_lda == library_dataset.library_dataset_dataset_association:
                            (your version)
                        %endif
                        %for expired_dataset in library_dataset.expired_datasets:
                        <br>
                        <input type="radio" name="set_lda_id" value="${expired_dataset.id}" ><a href="${h.url_for( controller='library', action='library_dataset_dataset_association', id=expired_dataset.id, library_id=library_id )}">${expired_dataset.name}</a>
                        %if refered_lda == expired_dataset:
                            (your version)
                        %endif
                        %endfor
                        </div>
                        <div class="form-row">
                            Click <a href="${h.url_for( controller='library', action='library_dataset_dataset_association', replace_id=library_dataset.id, library_id=library_id )}">here</a> to replace this dataset with a new version.
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
        <div class="toolFormTitle">View attributes of ${library_dataset.name}</div>
        <div class="toolFormBody">
            <div class="form-row">
                <b>Name:</b> ${library_dataset.name}
                <div style="clear: both"></div>
                <b>Info:</b> ${library_dataset.info}
                <div style="clear: both"></div>
                <b>Dataset Versions:</b>
                <div style="clear: both"></div>
                <a href="${h.url_for( controller='library', action='library_dataset_dataset_association', id=library_dataset.library_dataset_dataset_association.id, library_id=library_id )}">${library_dataset.name}</a> (current)
                %if refered_lda == library_dataset.library_dataset_dataset_association:
                    (your version)
                %endif
                %for expired_dataset in library_dataset.expired_datasets:
                    <br/>
                    <a href="${h.url_for( controller='library', action='library_dataset_dataset_association', id=expired_dataset.id, library_id=library_id )}">${expired_dataset.name}</a>
                    %if refered_lda == expired_dataset:
                        (your version)
                    %endif
                %endfor
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="toolForm">
            ${render_existing_library_item_info( library_dataset )}
        </div>
    </div>
%endif
%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library_dataset ):
    ${render_available_templates( library_dataset )}
%endif
