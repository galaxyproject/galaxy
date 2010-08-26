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
        <a class="action-button"  href="${h.url_for( controller=cntrller, action='list', operation='show', id=trans.security.encode_id(request.id))}">
        <span>Browse this request</span></a>
    </li>
    <li>
        <a class="action-button"  href="${h.url_for( controller=cntrller, action='list')}">
        <span>Browse all requests</span></a>
    </li>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">Edit sequencing request "${request.name}"</div>
    <div class="toolFormBody">
        <form name="edit_request" id="edit_request" action="${h.url_for( controller='requests_common', cntrller=cntrller, action='edit', id=trans.security.encode_id(request.id))}" method="post" >
           %for i, field in enumerate(widgets):
                <div class="form-row">
                    <label>${field['label']}</label>
                    ${field['widget'].get_html()}
                    %if field['label'] == 'Data library' and new_library:
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
                <input type="submit" name="save_changes_request_button" value="Save"/> 
           </div>
        </form>
    </div>
    <div class="toolFormTitle">Email notification settings</div>
    <div class="toolFormBody">
        <form name="settings" id="settings" action="${h.url_for( controller='requests_common', cntrller=cntrller, action='email_settings', id=trans.security.encode_id(request.id))}" method="post" >
            <% 
                email_user = ''
                email_additional = []
                for e in request.notification['email']:
                   if e == request.user.email:
                       email_user = 'checked'
                   else:
                       email_additional.append(e)
                emails = '\r\n'.join(email_additional)
            
            %>

            <div class="form-row">
                <label>Send to:</label>
                <input type="checkbox" name="email_user" value="true" ${email_user}>${request.user.email} (Sequencing request owner)<input type="hidden" name="email_user" value="true">
            </div>
            <div class="form-row">
                <label>Additional email addresses:</label>
                <textarea name="email_additional" rows="3" cols="40">${emails}</textarea>
                <div class="toolParamHelp" style="clear: both;">
                    Enter one email address per line
                </div>
            </div>
            <div class="form-row">
                <label>Select sample state(s) to send email notification:</label>
                %for ss in request.type.states:
                    <%  
                        email_state = ''
                        if ss.id in request.notification['sample_states']:
                            email_state = 'checked'
                     %>
                    <input type="checkbox" name=sample_state_${ss.id} value="true" ${email_state} >${ss.name}<input type="hidden" name=sample_state_${ss.id} value="true">
                    <br/>
                %endfor
                <div class="toolParamHelp" style="clear: both;">
                    Email notification would be sent when all the samples of this sequencing request are in the selected state(s).
                </div>
            </div>
          
            <div class="form-row">
                <input type="submit" name="save_button" value="Save"/> 
            </div>
        </form>
    </div>

</div>
