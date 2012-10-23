<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

%if trans.webapp.name == 'galaxy':
    <br/><br/>
    <ul class="manage-table-actions">
        <li><a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_categories' )}">Browse valid repositories</a></li>
        <li><a class="action-button" href="${h.url_for( controller='repository', action='find_workflows' )}">Search for workflows</a></li>
    </ul>
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
                ${exact_matches_check_box.get_html()}
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
