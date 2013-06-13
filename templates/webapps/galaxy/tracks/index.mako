<form id="form" method="POST">
    <div class="form-row">
        <label for="dbkey">Browser name:</label>
        <div class="form-row-input">
            <input type="text" name="title" id="title" value="Unnamed Browser"></input>
        </div>
        <div style="clear: both;"></div>
    </div>
    <div class="form-row">
        <label for="dbkey">Reference genome build (dbkey): </label>
        <div class="form-row-input">
            <select name="dbkey" id="dbkey" refresh_on_change="true">
                %for tmp_dbkey in dbkey_set:
                <option value="${tmp_dbkey}"
                %if tmp_dbkey == dbkey:
                selected="selected"
                %endif
                >${tmp_dbkey}</option>
                %endfor
            </select>
        </div>
        <div style="clear: both;"></div>
    </div>
    <div class="form-row">
        <label for="dataset_ids">Datasets to visualize: (${", ".join(available_tracks)} files are supported)</label>
        %for dataset_id, (dataset_ext, dataset_name) in datasets.iteritems():
        <div>
            <input type="checkbox" id="${dataset_id}" name="dataset_ids" value="${dataset_id}" />
            <label style="display:inline; font-weight: normal" for="${dataset_id}">[${dataset_ext}] ${dataset_name}</label>
        </div>
        %endfor

        <div style="clear: both;"></div>
    </div>
    <div class="form-row">
        <input type="submit" name="browse" value="Browse"/>
    </div>
</form>
