<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
    is_complete = request.is_complete
    is_submitted = request.is_submitted
    is_unsubmitted = request.is_unsubmitted
    can_add_samples = is_unsubmitted
    can_reject = is_admin and is_submitted
    can_submit_request = request.samples and is_unsubmitted
%>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="request-${request.id}-popup" class="menubutton">Request Actions</a></li>
    <div popupmenu="request-${request.id}-popup">
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Browse this request</a>
        %if can_submit_request:
            <a class="action-button" confirm="More samples cannot be added to this request once it is submitted. Click OK to submit." href="${h.url_for( controller='requests_common', action='submit_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Submit this request</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request_history', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">View history</a>
        %if can_reject:
            <a class="action-button" href="${h.url_for( controller='requests_admin', action='reject_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Reject this request</a>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Edit sequencing request "${request.name}"</div>
    <div class="toolFormBody">
        <form name="edit_basic_request_info" id="edit_basic_request_info" action="${h.url_for( controller='requests_common', action='edit_basic_request_info', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}" method="post" >
            %for i, field in enumerate( widgets ):
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
                <input type="submit" name="edit_basic_request_info_button" value="Save"/> 
            </div>
        </form>
    </div>
</div>
<p/>
<div class="toolForm">
    <div class="toolFormTitle">Email notification settings</div>
    <div class="toolFormBody">
        <form name="edit_email_settings" id="edit_email_settings" action="${h.url_for( controller='requests_common', action='edit_email_settings', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}" method="post" >
            <% 
                email_address = ''
                emails = ''
                additional_email_addresses = []
                if request.notification:
                    for e in request.notification[ 'email' ]:
                       if e == request.user.email:
                           email_address = 'checked'
                       else:
                           additional_email_addresses.append( e )
                if additional_email_addresses:
                    emails = '\r\n'.join( additional_email_addresses )
            %>
            <div class="form-row">
                <label>Send to:</label>
                <input type="checkbox" name="email_address" value="true" ${email_address}>${request.user.email} (sequencing request owner)<input type="hidden" name="email_address" value="true">
            </div>
            <div class="form-row">
                <label>Additional email addresses:</label>
                <textarea name="additional_email_addresses" rows="3" cols="40">${emails}</textarea>
                <div class="toolParamHelp" style="clear: both;">
                    Enter one email address per line
                </div>
            </div>
            <div class="form-row">
                <label>Select sample states to send email notification:</label>
                %for sample_state in request.type.states:
                    <%  
                        email_state = ''
                        if request.notification and sample_state.id in request.notification[ 'sample_states' ]:
                            email_state = 'checked'
                     %>
                    <input type="checkbox" name=sample_state_${sample_state.id} value="true" ${email_state} >${sample_state.name}<input type="hidden" name=sample_state_${sample_state.id} value="true">
                    <br/>
                %endfor
                <div class="toolParamHelp" style="clear: both;">
                    Email notification will be sent when all the samples of this sequencing request are in the selected states.
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="edit_email_settings_button" value="Save"/> 
            </div>
        </form>
    </div>
</div>
