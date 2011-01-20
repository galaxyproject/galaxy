
<%def name="display_dict( result_dict )">
    %for key, value in result_dict.items():
        <div class="form-row">
            <label>${key}</label>
            ${display_item( value )}
            <div style="clear: both"></div>
        </div>
    %endfor
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
        ${item}
    %endif
</%def>
