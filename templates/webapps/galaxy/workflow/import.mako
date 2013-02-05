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
        <div class="toolFormTitle">Import Galaxy workflow</div>
        <div class="toolFormBody">
            <form name="import_workflow" id="import_workflow" action="${h.url_for( controller='workflow', action='import_workflow' )}" enctype="multipart/form-data" method="POST">
                <div class="form-row">
                    <label>Galaxy workflow URL:</label> 
                    <input type="text" name="url" value="${url}" size="40">
                    <div class="toolParamHelp" style="clear: both;">
                        If the workflow is accessible via a URL, enter the URL above and click <b>Import</b>.
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Galaxy workflow file:</label>
                    <div class="form-row-input">
                        <input type="file" name="file_data"/>
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        If the workflow is in a file on your computer, choose it and then click <b>Import</b>.
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <input type="submit" class="primary-button" name="import_button" value="Import">
                </div>
            </form>
            <hr/>
            <div class="form-row">
                <label>Import a Galaxy workflow from myExperiment:</label>
                <div class="form-row-input">
                    <a href="${h.url_for( myexperiment_target_url )}">
                        Visit myExperiment
                    </a>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    Click the link above to visit myExperiment and browse for Galaxy workflows.
                </div>
                <div style="clear: both"></div>
            </div>
        </div>
    </div>
</%def>
