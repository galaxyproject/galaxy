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

%if providers:

<div class="form">
    <div class="form-title">Add credentials</div>
    <div class="form-body">
    <form name="Add credentials" action="${h.url_for( action='add' )}" method="post" >

           <%
            cls = "form-row"
            if error.has_key('cred_error'):
                cls += " form-row-error"
            %>
	            <div class="${cls}">
	            <label>Credentials name:</label>
	              <div class="form-row-input">
	              	<input type="text" name="credName" value="${credName}" size="40">
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
	            <label>Cloud provider name:</label>
	              <div class="form-row-input">
              		<select name="providerName" style="width:40em">
	              		<option value="">Select Provider...</option>
	              		%for provider in providers:
							<option value="${provider.name}">${provider.name}</option>
						%endfor
					</select>
					<br/>or <a href="${h.url_for( action='add_provider' )}">
					<span>register additional cloud provider</span></a>
				  </div>
				  %if error.has_key('provider_error'):
	              	<div class="form-row-error-message">${error['provider_error']}</div>
	              %endif
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
	              	<input type="text" name="accessKey" value="${accessKey}" size="40">
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
	              	<input type="password" name="secretKey" value="${secretKey}" size="40">
	              </div>
				  %if error.has_key('secret_key_error'):
	              	<div class="form-row-error-message">${error['secret_key_error']}</div>
	              %endif
	              <div style="clear: both"></div>
	            </div>
				
			
            <div class="form-row"><input type="submit" value="Add"></div>
    
        </form>
    </div>
</div>

%else:
	In order to add credentials, desired cloud provider needs to be registered first.<p/>
	Register <a href="${h.url_for( action='add_ec2' )}">
	<span>Amazon EC2 (us-east-1 region) automatically</span></a>
	or add
	<a href="${h.url_for( action='add_provider' )}">
	<span>custom cloud provider</span></a>.
%endif
