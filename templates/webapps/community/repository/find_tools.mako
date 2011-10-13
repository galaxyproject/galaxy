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

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Search repositories for valid tools</div>
    <div class="toolFormBody">
        <div class="form-row">
            Valid tools are those that properly load in Galaxy.  Enter any combination of the following tool attributes to locate matching valid tools.
        </div>
        <div style="clear: both"></div>
        <form name="find_tools" id="find_tools" action="${h.url_for( controller='repository', action='find_tools' )}" method="post" >
            <div class="form-row">
                <label>Tool id:</label>
                <input name="tool_id" type="textfield" value="${tool_id}" size="40"/>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Tool name:</label>
                <input name="tool_name" type="textfield" value="${tool_name}" size="40"/>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Tool version:</label>
                <input name="tool_version" type="textfield" value="${tool_version}" size="40"/>
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
