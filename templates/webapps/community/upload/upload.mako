<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="title()">Upload</%def>

<h2>Upload</h2>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Upload</div>
    <div class="toolFormBody">
    ## TODO: nginx
    <form id="upload_form" name="upload_form" action="${h.url_for( controller='upload', action='upload' )}" enctype="multipart/form-data" method="post">
    <div class="form-row">
        <label>Upload Type</label>
        <div class="form-row-input">
            <select name="upload_type">
                %for type_id, type_name in upload_types:
                    %if type_id == selected_upload_type:
                        <option value="${type_id}" selected>${type_name}</option>
                    %else:
                        <option value="${type_id}">${type_name}</option>
                    %endif
                %endfor
            </select>
        </div>
        <div class="toolParamHelp" style="clear: both;">
            Need help creating a tool file?  See help below.
        </div>
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>File:</label>
        <div class="form-row-input"><input type="file" name="file_data"/></div>
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Category</label>
        <div class="form-row-input">
            <select name="category_id">
                %for category in categories:
                    %if category.id in selected_categories:
                        <option value="${trans.security.encode_id( category.id )}" selected>${category.name}</option>
                    %else:
                        <option value="${trans.security.encode_id( category.id )}">${category.name}</option>
                    %endif
                %endfor
            </select>
        </div>
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
        <input type="submit" class="primary-button" name="upload_button" value="Upload">
    </div>
    </form>
    </div>
</div>
<div class="toolHelp">
    <div class="toolHelpBody">
        <p><strong>Tool Files</strong></p>
    </div>
</div>
