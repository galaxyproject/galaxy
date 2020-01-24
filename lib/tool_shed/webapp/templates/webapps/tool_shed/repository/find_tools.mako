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
    <div class="toolFormTitle">Search repositories for valid tools</div>
    <div class="toolFormBody">
        <div class="form-row">
            Valid tools are those that properly load in Galaxy.  Enter any combination of the following tool attributes to find repositories that contain 
            valid tools matching the search criteria.<br/><br/>
            Comma-separated strings may be entered in each field to expand search criteria.  Each field must contain the same number of comma-separated
            strings if these types of search strings are entered in more than one field.
        </div>
        <div style="clear: both"></div>
        <form name="find_tools" id="find_tools" action="${h.url_for( controller='repository', action='find_tools' )}" method="post" >
            <div class="form-row">
                <label>Tool id:</label>
                <input name="tool_id" type="textfield" value="${tool_id | h}" size="40"/>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Tool name:</label>
                <input name="tool_name" type="textfield" value="${tool_name | h}" size="40"/>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Tool version:</label>
                <input name="tool_version" type="textfield" value="${tool_version | h}" size="40"/>
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
                <input type="submit" value="Search repositories"/>
            </div>
        </form>
    </div>
</div>
