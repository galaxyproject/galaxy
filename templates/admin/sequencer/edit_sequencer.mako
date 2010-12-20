<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/requests/common.mako" import="*" />

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="sequencer-${sequencer.id}-popup" class="menubutton">Sequencer Actions</a></li>
    <div popupmenu="sequencer-${sequencer.id}-popup">
        %if not sequencer.deleted:
            <li><a class="action-button" href="${h.url_for( controller='sequencer', action='view_sequencer', id=trans.security.encode_id( sequencer.id ) )}">Browse sequencer</a></li>
            <li><a class="action-button" href="${h.url_for( controller='sequencer', action='edit_sequencer_form_definition', id=trans.security.encode_id( sequencer.id ) )}">Edit form definition</a></li>
            <li><a class="action-button" href="${h.url_for( controller='sequencer', action='delete_sequencer', id=trans.security.encode_id( sequencer.id ) )}">Delete sequencer</a></li>
        %endif
        %if sequencer.deleted:
            <li><a class="action-button" href="${h.url_for( controller='sequencer', action='undelete_sequencer', id=trans.security.encode_id( sequencer.id ) )}">Undelete configuration</a></li>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<form name="edit_sequencer" action="${h.url_for( controller='sequencer', action='edit_sequencer', id=trans.security.encode_id( sequencer.id ) )}" method="post" >
    <div class="toolForm">
        <div class="toolFormTitle">Edit sequencer</div>
        %for i, field in enumerate( widgets ):
            <div class="form-row">
                <label>${field['label']}:</label>
                ${field['widget'].get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    ${field['helptext']}
                </div>
                <div style="clear: both"></div>
            </div>
        %endfor  
    </div>
    <div class="form-row">
        <input type="submit" name="edit_sequencer_button" value="Save"/>
    </div>
</form>
