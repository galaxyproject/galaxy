<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<script type="text/javascript">
$( function() {
    $( "select[refresh_on_change='true']").change( function() {
        var refresh = false;
        var refresh_on_change_values = $( this )[0].attributes.getNamedItem( 'refresh_on_change_values' )
        if ( refresh_on_change_values ) {
            refresh_on_change_values = refresh_on_change_values.value.split( ',' );
            var last_selected_value = $( this )[0].attributes.getNamedItem( 'last_selected_value' );
            for( i= 0; i < refresh_on_change_values.length; i++ ) {
                if ( $( this )[0].value == refresh_on_change_values[i] || ( last_selected_value && last_selected_value.value == refresh_on_change_values[i] ) ){
                    refresh = true;
                    break;
                }
            }
        }
        else {
            refresh = true;
        }
        if ( refresh ){
            $( "#edit_request" ).submit();
        }
    });
});
</script>

<br/>
<br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='list', operation='show_request', id=trans.security.encode_id(request.id) )}">
        <span>Browse this request</span></a>
    </li>
    <li>
        <a class="action-button"  href="${h.url_for( controller='requests_admin', action='list')}">
        <span>Browse requests</span></a>
    </li>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">Edit request "${request.name}" from ${request.user.email}</div>
    %if len(select_request_type.options) == 1:
        There are no request types created for a new request.
    %else:
        <div class="toolFormBody">
            <form name="edit_request" id="edit_request" action="${h.url_for( controller='requests_admin', action='edit', request_id=request.id)}" method="post" >
                <div class="form-row">
                    <label>
                        Select Request Type:
                    </label>
                    ${select_request_type.get_html()}
                </div>

               %if select_request_type.get_selected() != ('Select one', 'none'):
                   %for i, field in enumerate(widgets):
                        <div class="form-row">
                            <label>${field['label']}</label>
                            ${field['widget'].get_html()}
                            %if field['label'] == 'Library' and new_library:
                                ${new_library.get_html()}
                            %endif
                            <div class="toolParamHelp" style="clear: both;">
                                ${field['helptext']}
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    %endfor                    
                    <div class="form-row">
                        <div style="float: left; width: 250px; margin-right: 10px;">
                            <input type="hidden" name="refresh" value="true" size="40"/>
                        </div>
                      <div style="clear: both"></div>
                    </div>
                    <div class="form-row">
                        <input type="submit" name="save_changes_request_button" value="Save changes"/> 
                        ##<input type="submit" name="edit_samples_button" value="Edit samples"/>
                    </div>
               %endif
        </form>
    </div>
</div>
%endif