<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
       else:
           return '/base.mako'
%>

<%inherit file="${inherit(context)}"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <div class="form-row">
            <div class="warningmessage">
                Upload a single exported capsule file.  Uploading may take a while, depending upon the size of the file.
                Wait until the contents of the file are displayed in your browser after clicking the <b>Upload</b> button below.
            </div>
            <div style="clear: both"></div>
        </div>
    </div>
</div>

<div class="toolForm">
    <div class="toolFormTitle">Upload a repository capsule</div>
    <div class="toolFormBody">
        <form id="upload_capsule" name="upload_capsule" action="${h.url_for( controller='repository', action='upload_capsule' )}" enctype="multipart/form-data" method="post">
            <div class="form-row">
                <label>File:</label>
                <div class="form-row-input">
                    <input type="file" name="file_data"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Url:</label>
                <div class="form-row-input">
                    <input name="url" type="textfield" value="${url | h}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" class="primary-button" name="upload_capsule_button" value="Upload">
            </div>
        </form>
    </div>
</div>
