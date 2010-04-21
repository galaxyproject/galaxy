<form id="new-browser-form" action="javascript:void(0);" method="post" onsubmit="return false;">
    <div class="form-row">
        <label for="new-title">Browser name:</label>
        <div class="form-row-input">
            <input type="text" name="title" id="new-title" value="Unnamed"></input>
        </div>
        <div style="clear: both;"></div>
    </div>
    <div class="form-row">
        <label for="new-dbkey">Reference genome build (dbkey): </label>
        <div class="form-row-input">
            <select name="dbkey" id="new-dbkey">
                %for dbkey in dbkeys:
                    <option value="${dbkey[0]}">${dbkey[1]}</option>
                %endfor
                
                %if user_keys:
                    %for key, chrom_dict in user_keys.iteritems():
                        <option value="${key}">${chrom_dict['name']} (${key})</option>
                    %endfor
                %endif
            </select>
        </div>
        <div style="clear: both;"></div>
    </div>
</form>
