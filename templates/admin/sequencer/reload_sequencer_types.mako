<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>


%if message:
    ${render_msg( message, status )}
%endif
<form name="create_sequencer" action="${h.url_for( controller='sequencer', action='reload_sequencer_types' )}" method="post">
	<div class="toolForm">
	    <div class="toolFormTitle">Reload sequencer types</div>
	    <div class="form-row">
	        <label>Select sequencer type to reload:</label>
	        ${sequencer_type_select_field.get_html()}
	        <div style="clear: both"></div>
	    </div>
	    <div class="form-row">
	        <input type="submit" name="reload_sequencer_type_button" value="Reload"/>
	    </div>
	</div>
</form>