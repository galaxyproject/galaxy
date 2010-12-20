<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/sequencer/common.mako" import="*" />

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="sequencer-${sequencer.id}-popup" class="menubutton">Sequencer Actions</a></li>
    <div popupmenu="sequencer-${sequencer.id}-popup">
        %if not sequencer.deleted:
            <li><a class="action-button" href="${h.url_for( controller='sequencer', action='edit_sequencer', id=trans.security.encode_id( sequencer.id ) )}">Edit sequencer</a></li>
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

<div class="toolForm">
    <div class="toolFormTitle">Sequencer information</div>
    ${render_sequencer( sequencer )}
</div>
