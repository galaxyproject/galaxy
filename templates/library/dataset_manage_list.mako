<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%def name="title()">List Datasets</%def>

<div class="toolForm">
    <div class="toolFormTitle">Edit Attributes</div>
    <div class="toolFormBody">
            %for lfda in lfdas:
            <div class="form-row">
                <label>${lfda.name}</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <a href="${h.url_for( controller='library', action='library_item_info', do_action='new_info', library_item_id=lfda.id, library_item_type='library_folder_dataset_association' )}">Add info</a>
                </div>
                
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <a href="${h.url_for( controller='root', action='edit', lid=lfda.id )}">Edit Dataset</a>
                </div>
                
                <div style="clear: both"></div>
            </div>
            %endfor
    </div>
</div>
