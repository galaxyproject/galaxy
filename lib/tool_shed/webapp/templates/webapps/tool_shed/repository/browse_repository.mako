<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />

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
    ${common_javascripts(repository)}
</%def>

<%
    is_new = repository.is_new()
    can_push = trans.app.security_agent.can_push( trans.app, trans.user, repository )
    can_download = not is_new and ( not is_malicious or can_push )
    can_browse_contents = not is_new
%>

${render_tool_shed_repository_actions( repository, metadata=metadata, changeset_revision=changeset_revision )}

%if message:
    ${render_msg( message, status )}
%endif

%if can_browse_contents:
    <div class="toolForm">
        <div class="toolFormTitle">Repository '${repository.name | h}' revision ${repository.tip() | h} (repository tip)</div>
        %if can_download:
            <div class="form-row">
                <label>Clone this repository:</label>
                ${render_clone_str( repository )}
            </div>
        %endif
        <form name="repository_type">
            ${render_repository_type_select_field( repository_type_select_field, render_help=False )}
        </form>
        <div class="toolFormBody">
            <div class="form-row" >
                <label>Contents:</label>
                <div id="tree" >
                    Loading...
                </div>
            </div>
            <div class="form-row">
                <div id="file_contents" class="toolParamHelp" style="clear: both;background-color:#FAFAFA;"></div>
            </div>
        </div>
    </div>
    <p/>
%endif
