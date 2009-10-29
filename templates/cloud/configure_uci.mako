<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Configure new UCI</%def>

<%def name="javascripts()">
${parent.javascripts()}
<script type="text/javascript">

var providers_zones = ${h.to_json_string(providersToZones)};

$(function(){
    $("input:text:first").focus();
	
	$("#credName").change(function() {
		var zones = providers_zones[ $(this).val() ];
		var zones_select = $("#zones");
		
		zones_select.children().remove();
		
		for (var i in zones) {
			var zone = zones[i];
			var new_option = $('<option value="' + zone + '">' + zone + '</option>');
			new_option.appendTo(zones_select);
		}
		
	});
})
</script>
</%def>

%if header:
    ${header}
%endif

<div class="form">
    <div class="form-title">Configure new Galaxy instance</div>
    <div class="form-body">
    <form name="Configure new UCI" action="${h.url_for( action='configureNew' )}" method="post" >
        
           <%
            cls = "form-row"
            if error.has_key('inst_error'):
                cls += " form-row-error"
            %>
	            <div class="${cls}">
	            <label>Instance name:</label>
	              <div class="form-row-input">
	              	<input type="text" name="instanceName" value="${instanceName}" size="40">
	              </div>
				  %if error.has_key('inst_error'):
	              	<div class="form-row-error-message">${error['inst_error']}</div>
	              %endif
	              <div style="clear: both"></div>
                </div>
            
			<%
            cls = "form-row"
            if error.has_key('cred_error'):
                cls += " form-row-error"
            %>
			    <div class="${cls}">
	            <label>Name of registered credentials to use:</label>
	              <div class="form-row-input">
	              	<select id="credName" name="credName" style="width:40em">
	              		<option value="">Select Credential...</option>
	              		% for cred in credName:
	              			<option value="${cred.name}">${cred.name}</option>
						%endfor
	              	</select>
	              </div>
				  %if error.has_key('cred_error'):
	              	<div class="form-row-error-message">${error['cred_error']}</div>
	              %endif
				  <div style="clear: both"></div>
	            </div>
			
			
			<%
            cls = "form-row"
            if error.has_key('vol_error'):
                cls += " form-row-error"
            %>
	            <div class="${cls}">
	            <label>Permanent storage size (1-1000GB):<br/>(Note: you will be able to add more storage later)</label>
	              <div class="form-row-input">
	              	<input type="text" name="volSize" value="${volSize}" size="40">
	              </div>
				  %if error.has_key('vol_error'):
	              	<div class="form-row-error-message">${error['vol_error']}</div>
	              %endif
	              <div style="clear: both"></div>
	            </div>
			
			<%
            cls = "form-row"
            if error.has_key('zone_error'):
                cls += " form-row-error"
            %>
			    <div class="${cls}">
	            <label>Zone to create storage in:</label>
	              <div class="form-row-input">
	              	<select id="zones" name="zone" style="width:40em">
	              	</select>
	              </div>
				   %if error.has_key('zone_error'):
	              	<div class="form-row-error-message">${error['zone_error']}</div>
	              %endif
				  <div style="clear: both"></div>
	            </div>
				
			
            <div class="form-row"><input type="submit" value="Add"></div>
    
        </form>
    </div>
</div>
