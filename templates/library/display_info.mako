<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<p/>

<div class="toolForm">
    <div class="toolFormTitle">Available Library Item Info</div>
    <div class="toolFormBody">
            %for template_info_element in item_info.library_item_info_template.elements:
                <div class="form-row">
                    <label>
                       ${template_info_element.name}:
                    </label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        ${item_info.get_element_by_template_element( template_info_element ).contents}
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        ${template_info_element.description}
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endfor
    </div>
</div>
