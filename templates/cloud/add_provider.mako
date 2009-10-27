<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Add provider</%def>

<%def name="javascripts()">
${parent.javascripts()}
<script type="text/javascript">
$(function(){
    
	$("input:text:first").focus();
	
	$("#type").change(function() {
		if ($(this).val() == 'ec2') {
			clear();
			$("#autofill").attr( 'disabled', true );
			$("#autofill").attr( 'checked', false );
			$("#name").val( "EC2" );
			$("#region_name").val( "us-east-1" );
			$("#region_endpoint").val( "us-east-1.ec2.amazonaws.com" );
			$("#is_secure").val("1");
			$("#debug").val("");
			$("#path").val("/");
		}
		else if ($(this).val() == 'eucalyptus') {
			clear();
			$("#autofill").attr( 'disabled', false );
		}
	});
})


function af(){
	
	if ( $("#autofill").attr('checked') ) {
		$("#region_name").val("eucalyptus");
		$("#region_endpoint").val("mayhem9.cs.ucsb.edu");
		$("#is_secure").val("0");
		$("#port").val("8773");
		$("#path").val("/services/Eucalyptus");
	}
	else {
		clear();
	}
}

function clear() {
	$("#name").val("");
	$("#region_name").val("");
	$("#region_endpoint").val("");
	$("#is_secure").val("");
	$("#port").val("");
	$("#proxy").val("");
	$("#proxy_port").val("");
	$("#proxy_user").val("");
	$("#proxy_pass").val("");
	$("#debug").val("");
	$("#https_connection_factory").val("");
	$("#path").val("");

}

</script>
</%def>

%if header:
    ${header}
%endif

<div class="form">
    <div class="form-title">Add cloud provider</div>
    <div class="form-body">
    <form name="add_provider_form" action="${h.url_for( action='add_provider' )}" method="post" >
			<%
			cls = "form-row"
			if error.has_key('type_error'):
				cls += " form-row-error"
			%>
		   	<div class="${cls}">
			<label>Provider type:</label>
			<div class="form-row-input">
				<select id="type" name="type" style="width:40em">
					<option value="">Select Provider...</option>
					<option value="eucalyptus">Eucalyptus</option>
					<option value="ec2">Amazon EC2</option>
				</select>
			<br/>
			<input type="checkbox" id="autofill" onclick="javascript:af()" disabled="true">			
				auto fill using Eucalyptus Public Cloud values
			</div>
			%if error.has_key('type_error'):
            	<div class="form-row-error-message">${error['type_error']}</div>
            %endif
			<div style="clear: both"></div>
		   	</div>
				  
		    <%
            cls = "form-row"
            if error.has_key('name_error'):
                cls += " form-row-error"
            %>
            <div class="${cls}">
            <label>Provider name:</label>
            <div class="form-row-input">
            	<input type="text" id="name" name="name" value="${name}" size="40">
            </div>
			%if error.has_key('name_error'):
            	<div class="form-row-error-message">${error['name_error']}</div>
            %endif
            <div style="clear: both"></div>
            </div>
            
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>Region name:</label>
            <div id="region_selection" class="form-row-input">
            	<input type="text" name="region_name" id="region_name" value="${region_name}" size="40">
            </div>
			%if error.has_key('name_error'):
            	<div class="form-row-error-message">${error['name_error']}</div>
            %endif
			<div style="clear: both"></div>
            </div>
			
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>Region endpoint:</label>
            <div class="form-row-input">
            	<input type="text" name="region_endpoint" id="region_endpoint" value="${region_endpoint}" size="40">
            </div>
			<div style="clear: both"></div>
            </div>
			
			 <%
            cls = "form-row"
            if error.has_key('is_secure_error'):
                cls += " form-row-error"
            %>
            <div class="${cls}">
            <label>Is secure ('O' for False or '1' for True):</label>
            <div class="form-row-input">
            	<input type="text" name="is_secure" id="is_secure" value="${is_secure}" size="40">
            </div>
			%if error.has_key('is_secure_error'):
            	<div class="form-row-error-message">${error['is_secure_error']}; you entered: '${is_secure}'</div>
            %endif
			<div style="clear: both"></div>
            </div>
			
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>Host:</label>
            <div class="form-row-input">
            	<input type="text" name="host" value="${host}" size="40">
            </div>
			<div style="clear: both"></div>
            </div>
			
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>Port:</label>
            <div class="form-row-input">
            	<input type="text" name="port" id="port" value="${port}" size="40">
            </div>
			<div style="clear: both"></div>
            </div>
			
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>Proxy:</label>
            <div class="form-row-input">
            	<input type="text" name="proxy" value="${proxy}" size="40">
            </div>
			<div style="clear: both"></div>
            </div>
			
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>Proxy port:</label>
            <div class="form-row-input">
            	<input type="text" name="proxy_port" value="${proxy_port}" size="40">
            </div>
			<div style="clear: both"></div>
            </div>
			
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>Proxy user:</label>
            <div class="form-row-input">
            	<input type="text" name="proxy_user" value="${proxy_user}" size="40">
            </div>
			<div style="clear: both"></div>
            </div>
			
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>Proxy pass:</label>
            <div class="form-row-input">
            	<input type="text" name="proxy_pass" value="${proxy_pass}" size="40">
            </div>
			<div style="clear: both"></div>
            </div>
			
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>Debug:</label>
            <div class="form-row-input">
            	<input type="text" name="debug" value="${debug}" size="40">
            </div>
			<div style="clear: both"></div>
            </div>
			
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>HTTPS connection factory:</label>
            <div class="form-row-input">
            	<input type="text" name="https_connection_factory" value="${https_connection_factory}" size="40">
            </div>
			<div style="clear: both"></div>
            </div>
			
			<%
            cls = "form-row"
            %>
            <div class="${cls}">
            <label>Path:</label>
            <div class="form-row-input">
            	<input type="text" name="path" id="path" value="${path}" size="40">
            </div>
			<div style="clear: both"></div>
            </div>
			
            <div class="form-row"><input type="submit" value="Add"></div>
    
        </form>
		
    </div>
</div>
