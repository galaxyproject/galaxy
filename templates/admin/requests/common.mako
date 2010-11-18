<%def name="render_state( element_count, state_name, state_desc )">
    <div class="repeat-group-item">
        <div class="form-row">
            <label>${1+element_count}. State name:</label>
            <input type="text" name="state_name_${element_count}" value="${state_name}" size="40"/>
            <input type="submit" name="remove_state_button" value="Remove state ${1+element_count}"/>
        </div>
        <div class="form-row">
            <label>Description:</label>
            <input type="text" name="state_desc_${element_count}" value="${state_desc}" size="40"/>
            <div class="toolParamHelp" style="clear: both;">
                optional
            </div>
        </div>
        <div style="clear: both"></div>
   </div>
</%def>
