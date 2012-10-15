<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/external_service/common.mako" import="*" />

%if message:
    ${render_msg( message, status )}
%endif

<form name="create_external_service" action="${h.url_for( controller='external_service', action='create_external_service' )}" method="post">
    <div class="toolForm">
        <div class="toolFormTitle">New external service</div>
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
        <input type="submit" name="create_external_service_button" value="Save"/>
    </div>
</form>
