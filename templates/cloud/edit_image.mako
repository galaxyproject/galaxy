<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Edit machine image</%def>

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

%if image:

<div class="form">
    <div class="form-title">Edit image</div>
    <div class="form-body">
	<form name="edit_image" action="${h.url_for( action='editImage', id=trans.security.encode_id(image.id), edited="true" )}" method="post" >
			<%
            cls = "form-row"
            if error.has_key('provider_error'):
                cls += " form-row-error"
            %>
	            <div class="${cls}">
	            <label>Provider type:</label>
	              <div class="form-row-input">
	              	${image.provider_type}
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
	              	<input type="text" name="image_id" value="${image.image_id}" size="40">
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
	              	<input type="text" name="manifest" value="${image.manifest}" size="40">
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
	            <label>Architecture:</label>
	              <div class="form-row-input">
	              	<input type="text" name="architecture" value="${image.architecture}" size="40">
	              </div>
				  %if error.has_key('arch_error'):
	              	<div class="form-row-error-message">${error['arch_error']}</div>
	              %endif
	              <div style="clear: both"></div>
	            </div>
			
            <div class="form-row"><input type="submit" value="Save"></div>
        </form>
    </div>
</div>

%else:
	Specified machine image could not be found. 
%endif
