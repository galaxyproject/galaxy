<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Add machine image</%def>

<%def name="javascripts()">
${parent.javascripts()}
<script type="text/javascript">
$(function(){
   //$("input:text:first").focus();
})
</script>
</%def>

%if header:
    ${header}
%endif

<div class="form">
    <div class="form-title">Add machine image</div>
    <div class="form-body">
	<form name="add_image" action="${h.url_for( action='add_new_image' )}" method="post" >
			<%
            cls = "form-row"
            if error.has_key('provider_error'):
                cls += " form-row-error"
            %>
		    <div class="${cls}">
            <label>Cloud provider type:</label>
              <div class="form-row-input">
          		<select name="provider_type" style="width:40em">
              		<option value="">Select Provider Type...</option>
              		<option value="eucalyptus">Eucalyptus</option>
					<option value="ec2">Amazon EC2</option>
				</select>
			  </div>
			  %if error.has_key('provider_error'):
              	<div class="form-row-error-message">${error['provider_error']}</div>
              %endif
              <div style="clear: both"></div>
            </div>
			
            <%
            cls = "form-row"
            if error.has_key('id_error'):
                cls += " form-row-error"
            %>
	            <div class="${cls}">
	            <label>Machine Image ID (AMI or EMI):</label>
	              <div class="form-row-input">
	              	<input type="text" name="image_id" value="${image_id}" size="40">
	              </div>
				  %if error.has_key('id_error'):
	              	<div class="form-row-error-message">${error['id_error']}</div>
	              %endif
	              <div style="clear: both"></div>
                </div>
            
			<%
            cls = "form-row"
            if error.has_key('manifest_error'):
                cls += " form-row-error"
            %>
	            <div class="${cls}">
	            <label>Manifest:</label>
	              <div class="form-row-input">
	              	<input type="text" name="manifest" value="${manifest}" size="40">
	              </div>
				  %if error.has_key('manifest_error'):
	              	<div class="form-row-error-message">${error['manifest_error']}</div>
	              %endif
	              <div style="clear: both"></div>
	            </div>
			
			
			<%
            cls = "form-row"
            if error.has_key('arch_error'):
                cls += " form-row-error"
            %>
		    <div class="${cls}">
            <label>Image architecture:</label>
              <div class="form-row-input">
          		<select name="architecture" style="width:40em">
              		<option value="">Select Architecture Type...</option>
              		<option value="i386">i386 (32 bit)</option>
					<option value="x86_64">x86_64 (64 bit)</option>
				</select>
			  </div>
			  %if error.has_key('arch_error'):
              	<div class="form-row-error-message">${error['arch_error']}</div>
              %endif
              <div style="clear: both"></div>
            </div>
				
            <div class="form-row"><input type="submit" value="Add"></div>
        </form>
    </div>
</div>