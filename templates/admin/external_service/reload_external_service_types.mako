<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>


%if message:
    ${render_msg( message, status )}
%endif
<form name="reload_external_service_types" action="${h.url_for( controller='external_service', action='reload_external_service_types' )}" method="post">
	<div class="toolForm">
	    <div class="toolFormTitle">Reload external service types</div>
	    <div class="form-row">
	        <label>Select external service type to reload:</label>
	        ${external_service_type_select_field.get_html()}
	        <div style="clear: both"></div>
	    </div>
	    <div class="form-row">
	        <input type="submit" name="reload_external_service_type_button" value="Reload"/>
	    </div>
	</div>
</form>