<%inherit file="/base.mako"/>

<%def name="title()">Add Dataset to Library from History</%def>
%if error_msg:
    <p>
        <div class="errormessage">${error_msg}</div>
        <div style="clear: both"></div>
    </p>
%endif
%if ok_msg:
    <p>
        <div class="donemessage">${ok_msg}</div>
        <div style="clear: both"></div>
    </p>
%endif
<p/>
<div class="toolForm">
    <div class="toolFormTitle">Active Datasets in your current history (${history.name})</div>
    <div class="toolFormBody">
        <form name="add_dataset_from_history">
            <input type="hidden" name="folder_id" value="${folder.id}"/>
            %for dataset in history.active_datasets:
                <div class="form-row">
                    <input name="ids" value="${dataset.id}" type="checkbox"/>${dataset.hid}: ${dataset.name}
                </div>
            %endfor
            <input type="submit" name="submit" value="Add Datasets"/>
        </form>
    </div>
</div>
