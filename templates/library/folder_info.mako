<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common.mako" import="render_available_templates" />
<%namespace file="/library/common.mako" import="render_library_item_info_for_edit" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library', action='browse_library', id=library_id )}"><span>Browse this library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=folder ):
    %if render_templates not in [ 'False', False ]:
        ${render_available_templates( folder, library_id, restrict=restrict )}
    %endif
%endif

<div class="toolForm">
    <div class="toolFormTitle">Edit folder name and description</div>
    <div class="toolFormBody">
        %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=folder ):
            <form name="folder" action="${h.url_for( controller='library', action='folder', rename=True, id=folder.id, library_id=library_id )}" method="post" >
                <div class="form-row">
                    <label>Name:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="name" value="${folder.name}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Description:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="description" value="${folder.description}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <input type="submit" name="rename_folder_button" value="Save"/>
            </form>
        %else:
            <div class="form-row">
                <b>Name:</b>&nbsp;${folder.name}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <b>Description:</b>&nbsp;${folder.description}
                <div style="clear: both"></div>
            </div>
        %endif
        </div>
    </div>
    <p/>

<% folder.refresh() %>
%if folder.library_folder_info_associations:
    ${render_library_item_info_for_edit( folder, library_id )}
%elif folder.library_folder_info_template_associations:
    ${render_available_templates( folder, library_id, restrict=True )}
%else:
    ${render_available_templates( folder, library_id, restrict=False )}
%endif
