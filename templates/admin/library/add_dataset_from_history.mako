<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Add Dataset to Library from History</%def>
%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Active datasets in your current history (${history.name})</div>
    <div class="toolFormBody">
        <form name="add_dataset_from_history">
            %if replace_dataset is not None:
            <input type="hidden" name="replace_id" value="${replace_dataset.id}"/>
            <div class="form-row">
                You are currently selecting a new file to replace '<a href="${h.url_for( controller='admin', action='dataset', id=replace_dataset.library_folder_dataset_association.id )}">${replace_dataset.name}</a>'.
                <div style="clear: both"></div>
            </div>
            %else:
            <input type="hidden" name="folder_id" value="${folder.id}"/>
            %endif
            %for dataset in history.active_datasets:
                <div class="form-row">
                    <input name="ids" value="${dataset.id}" type="checkbox"/>${dataset.hid}: ${dataset.name}
                </div>
            %endfor
            <input type="submit" name="add_dataset_from_history_button" value="Add selected datasets"/>
        </form>
    </div>
</div>
