<form id="new-browser-form" method="post" onsubmit="continue_fn(); return false;">
    <div class="form-row">
        <label for="title">Browser name:</label>
        <div class="form-row-input">
            <input type="text" name="title" id="new-title" value="Unnamed Browser"></input>
        </div>
        <div style="clear: both;"></div>
    </div>
    <div class="form-row">
        <label for="dbkey">Reference genome build (dbkey): </label>
        <div class="form-row-input">
            <select name="dbkey" id="new-dbkey">
                %for dbkey in dbkey_set:
                    <option value="${dbkey}">${dbkey}</option>
                %endfor
            </select>
        </div>
        <div style="clear: both;"></div>
    </div>
</form>
