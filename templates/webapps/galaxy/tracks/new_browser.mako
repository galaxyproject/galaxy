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
                    <option value="${dbkey[1]}">${dbkey[0]}</option>
                %endfor
            </select>
        </div>
        <div style="clear: both;"></div>
    </div>
    <div class="form-row">
        Is the build not listed here? 
        <a href="${h.url_for( controller='user', action='dbkeys', use_panels=True )}">Add a Custom Build</a>
    </div>
    %if default_dbkey is not None:
        <script type="text/javascript">
            $("#new-dbkey option[value='${default_dbkey}']").attr("selected", true);
        </script>
    %endif
</form>
