<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Add credentials</%def>

<%def name="javascripts()">
${parent.javascripts()}
<script type="text/javascript">
$(function(){
    $("input:text:first").focus();
})
</script>
</%def>

%if header:
    ${header}
%endif

%if credential:

<div class="form">
    <div class="form-title">Edit credentials</div>
    <div class="form-body">
	<form name="edit_credentials" action="${h.url_for( action='edit_credentials', id=trans.security.encode_id(credential.id), edited="true" )}" method="post" >
	
           <%
            cls = "form-row"
            if error.has_key('cred_error'):
                cls += " form-row-error"
            %>
	            <div class="${cls}">
	            <label>Credentials name:</label>
	              <div class="form-row-input">
	              	<input type="text" name="credName" value="${credential.name}" size="40">
	              </div>
				  %if error.has_key('cred_error'):
	              	<div class="form-row-error-message">${error['cred_error']}</div>
	              %endif
	              <div style="clear: both"></div>
                </div>
            
			
			<%
            cls = "form-row"
            if error.has_key('provider_error'):
                cls += " form-row-error"
            %>
			<div class="${cls}">
            <label>Cloud provider name (type):</label>
              <div class="form-row-input">${credential.provider.name} (${credential.provider.type})</div>
			<div style="clear: both"></div>
            </div>
			<%
            cls = "form-row"
            if error.has_key('access_key_error'):
                cls += " form-row-error"
            %>
	            <div class="${cls}">
	            <label>Access key:</label>
	              <div class="form-row-input">
	              	<input type="text" name="accessKey" value="${credential.access_key}" size="40">
	              </div>
				  %if error.has_key('access_key_error'):
	              	<div class="form-row-error-message">${error['access_key_error']}</div>
	              %endif
	              <div style="clear: both"></div>
	            </div>
			
			<%
            cls = "form-row"
            if error.has_key('secret_key_error'):
                cls += " form-row-error"
            %>
	            <div class="${cls}">
	            <label>Secret key:</label>
	              <div class="form-row-input">
	              	<input type="password" name="secretKey" value="${credential.secret_key}" size="40">
	              </div>
				  %if error.has_key('secret_key_error'):
	              	<div class="form-row-error-message">${error['secret_key_error']}</div>
	              %endif
	              <div style="clear: both"></div>
	            </div>
			
            <div class="form-row"><input type="submit" value="Edit"></div>
        </form>
    </div>
</div>

%else:
	Specified credentials could not be found. 
%endif
