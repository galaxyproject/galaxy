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
            <input type="hidden" name="folder_id" value="${folder.id}"/>
            %for dataset in history.active_datasets:
                <div class="form-row">
                    <input name="ids" value="${dataset.id}" type="checkbox"/>${dataset.hid}: ${dataset.name}
                </div>
            %endfor
            <input type="submit" name="add_dataset_from_history_button" value="Add selected datasets"/>
        </form>
    </div>
</div>
