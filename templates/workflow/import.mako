<%inherit file="/webapps/galaxy/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "workflow" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="workflow"
    self.message_box_visible=False
%>
</%def>

<%def name="title()">Import Galaxy workflow</%def>

<%def name="center_panel()">
    %if message:
        ${render_msg( message, status )}
    %endif
    <div class="toolForm"> 
        <div class="toolFormTitle">Import an exported Galaxy workflow file</div>
        <div class="toolFormBody">
            <form name="import_workflow" id="import_workflow" action="${h.url_for( controller='workflow', action='import_workflow' )}" enctype="multipart/form-data" method="POST">
                <div class="form-row">
                    <label>URL for exported Galaxy workflow:</label> 
                    <input type="text" name="url" value="${url}" size="40">
                    <div class="toolParamHelp" style="clear: both;">
                        If the workflow is accessible via an URL, enter the URL above and click the <b>Import</b> button.
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Exported Galaxy workflow file:</label>
                    <div class="form-row-input">
                        <input type="file" name="file_data"/>
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        If the workflow is stored locally in a file, browse and select it and then click the <b>Import</b> button.
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <input type="submit" class="primary-button" name="import_button" value="Import">
                </div>
            </form>
        </div>
    </div>
</%def>
