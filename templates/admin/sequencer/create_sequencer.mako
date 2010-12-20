<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/sequencer/common.mako" import="*" />

%if message:
    ${render_msg( message, status )}
%endif

<form name="create_sequencer" action="${h.url_for( controller='sequencer', action='create_sequencer' )}" method="post">
    <div class="toolForm">
        <div class="toolFormTitle">New sequencer</div>
        %if widgets:
	        %for i, field in enumerate( widgets ):
	            <div class="form-row">
	                <label>${field['label']}:</label>
	                ${field['widget'].get_html()}
	                <div class="toolParamHelp" style="clear: both;">
	                    ${field['helptext']}
	                </div>
	                <div style="clear: both"></div>
	            </div>
	        %endfor
        %endif
    </div>
    <div class="form-row">
        <input type="submit" name="create_sequencer_button" value="Save"/>
    </div>
</form>
