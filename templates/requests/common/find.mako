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
            $( "#find_request" ).submit();
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
    <div class="toolFormTitle">Find samples</div>
    <div class="toolFormBody">
        <form name="find_request" id="find_request" action="${h.url_for( controller='requests_common', action='find', cntrller=cntrller)}" method="post" >
            <div class="form-row">
                <label>Find in sequencing requests in state:</label>
                <select name="request_state"> 
                    <option value="In Progress" selected>In-Progress</option> 
                    <option value="Complete">Complete</option>
                    <option value="Both">Both</option> 
                </select>
            </div>
            <div class="form-row">
                <label>Find by sample:</label>
                <select name="search_type"> 
                    <option value="name" selected>name</option> 
                    <option value="bar_code">barcode</option> 
                </select>
            </div>
            <div class="form-row">
                <input type="text" name="search_string" size="40" value="">
                <input type="submit" name="go_button" value="Go"/>  
            </div>
            %if results:
	            <div class="form-row">
                    <label><i>${results}</i></label> 
	            </div>
	        %endif
            <div class="form-row">
	            %if samples:
	                %for s in samples:
	                    <div class="form-row">
	                        <a href="${h.url_for( controller=cntrller, action='list', operation='show', id=trans.security.encode_id(s.request.id))}"><label>Sequencing request: ${s.request.name} | Type: ${s.request.type.name} | State: ${s.request.state()}</label></a>
                            %if cntrller == 'requests_admin':
                               <i>User: ${s.request.user.email}</i>
                            %endif
					        <div class="toolParamHelp" style="clear: both;">
	                            Sample: ${s.name}<br/>
	                            Barcode: ${s.bar_code}<br/>
	                            State: ${s.current_state().name}
					        </div>
	                    </div>
	                    <br/>
	                %endfor
	            %endif
	            
            </div>
        </form>
    </div>
</div>
