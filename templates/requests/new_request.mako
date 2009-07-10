<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${title}</div>
    <div class="toolFormBody">
        <form name="sample" action="${h.url_for( controller='requests', action='new', save=True, request_form_id=request_form_id, request_type_id=request_type.id )}" method="post" >
            %for i, field in enumerate(widgets):
                <div class="form-row">
                    <label>${field['label']}</label>
                    ${field['widget'].get_html()}
                    <div class="toolParamHelp" style="clear: both;">
                        ${field['helptext']}
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endfor                    
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="new" value="submitted" size="40"/>
                </div>
              <div style="clear: both"></div>
            </div>
            <input type="submit" name="create_library_button" value="Save"/>
        </form>
    </div>
</div>