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
            $( "#new_request" ).submit();
        }
    });
});
</script>

<%def name="javascripts()">
   ${parent.javascripts()}
   ${h.js("jquery.autocomplete", "autocomplete_tagging" )}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
</%def>

<br/>
<br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller=cntrller, cntrller=cntrller, action='list')}">
        <span>Browse requests</span></a>
    </li>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">Add a new request</div>
    %if len(select_request_type.options) == 1:
        There are no request types created for a new request.
    %else:
        <div class="toolFormBody">
            <form name="new_request" id="new_request" action="${h.url_for( controller='requests_common', action='new', cntrller=cntrller)}" method="post" >
                <div class="form-row">
                    <label>
                        Select request type
                    </label>
                    ${select_request_type.get_html()}
                </div>

               %if select_request_type.get_selected() != ('Select one', 'none'):
                   %for i, field in enumerate(widgets):
                        <div class="form-row">
                            <label>${field['label']}</label>
                            ${field['widget'].get_html()}
                            <div class="toolParamHelp" style="clear: both;">
                                ${field['helptext']}
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    %endfor                    
                    <div class="form-row">
                        <input type="submit" name="create_request_button" value="Save"/> 
                        <input type="submit" name="create_request_samples_button" value="Add samples"/>
                    </div>
               %endif
                <div class="form-row">
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="hidden" name="refresh" value="true" size="40"/>
                    </div>
                  <div style="clear: both"></div>
                </div>
	        </form>
	    </div>
</div>
%endif