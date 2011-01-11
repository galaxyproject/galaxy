
<%def name="display_dict( result_dict )">
    <div class="form-row">
    %for key, value in result_dict.items():
            <label>
                ${key}
            </label>
            ${display_item( value )}
    %endfor
    </div>
</%def>


<%def name="display_list( items )">
    <ul>
    %for item in items:
        <li>${display_item( item ) }</li>
    %endfor
    </ul>
</%def>

<%def name="display_item( item )">
    %if isinstance( item, ( list, tuple ) ):
        ${display_list( item )}
    %elif isinstance( item, dict ):
        ${display_dict( item )}
    %else:
        <div class="form-row-input">${item}</div>
        <div style="clear: both"></div>
    %endif
</%def>