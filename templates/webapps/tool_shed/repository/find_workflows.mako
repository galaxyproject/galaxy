<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_galaxy_repository_actions" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

%if trans.webapp.name == 'galaxy':
    ${render_galaxy_repository_actions( repository=None )}
%endif

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Search repositories for workflows</div>
    <div class="toolFormBody">
        <div class="form-row">
            Enter a workflow name to find repositories that contain workflows matching the search criteria, or leave blank to find all repositories that contain a workflow.<br/><br/>
            Comma-separated strings may be entered to expand search criteria.
        </div>
        <div style="clear: both"></div>
        <form name="find_workflows" id="find_workflows" action="${h.url_for( controller='repository', action='find_workflows' )}" method="post" >
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Workflow name:</label>
                <input name="workflow_name" type="textfield" value="${workflow_name | h}" size="40"/>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Exact matches only:</label>
                ${render_checkbox(exact_matches_check_box)}
                <div class="toolParamHelp" style="clear: both;">
                    Check the box to match text exactly (text case doesn't matter as all strings are forced to lower case).
                </div>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="submit" name="find_workflows_button" value="Search repositories"/>
            </div>
        </form>
    </div>
</div>
