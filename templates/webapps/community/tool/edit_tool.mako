<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="title()">Edit Tool</%def>

<h2>Edit Tool: ${tool.name} ${tool.version} (${tool.tool_id})</h2>

%if message:
    ${render_msg( message, status )}
%endif

<form id="tool_edit_form" name="tool_edit_form" action="${h.url_for( controller='tool_browser', action='edit_tool' )}" enctype="multipart/form-data" method="post">
<input type="hidden" name="id" value="${encoded_id}"/>
<div class="toolForm">
    <div class="toolFormTitle">Edit Tool</div>
    <div class="toolFormBody">
    <div class="form-row">
        <label>Categories:</label>
        <div class="form-row-input">
            <select name="category" multiple size=5 style="min-width: 250px;">
                %for category in categories:
                    %if category.id in [ tool_category.id for tool_category in tool.categories ]:
                        <option value="${category.id}" selected>${category.name}</option>
                    %else:
                        <option value="${category.id}">${category.name}</option>
                    %endif
                %endfor
            </select>
        </div>
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Description:</label>
        <div class="form-row-input"><textarea name="description" rows="5" cols="35">${tool.user_description}</textarea></div>
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <input type="submit" class="primary-button" name="save_button" value="Save">
    </div>
    </div>
</div>

<p/>

<div class="toolForm">
    <div class="toolFormTitle">Upload new version</div>
    <div class="toolFormBody">
    <div class="form-row">
        <label>File:</label>
        <div class="form-row-input"><input type="file" name="file_data"/></div>
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>URL:</label>
        <div class="form-row-input"><input type="text" name="url" style="width: 100%;"/></div>
        <div class="toolParamHelp" style="clear: both;">
            Instead of uploading directly from your computer, you may instruct Galaxy to download the file from a Web or FTP address.
        </div>
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <input type="submit" class="primary-button" name="save_button" value="Save">
    </div>
</div>
</form>
