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
    ${h.css( "jquery.rating", "dynatree_skin/ui.dynatree" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/jquery/jquery.rating", "libs/jquery/jquery-ui", "libs/jquery/jquery.cookie", "libs/jquery/jquery.dynatree" )}
    ${common_javascripts(repository)}
</%def>

<%
    is_new = repository.is_new( trans.app )
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
        <div class="toolFormTitle">Repository '${repository.name | h}' revision ${repository.tip( trans.app ) | h} (repository tip)</div>
        %if can_download:
            <div class="form-row">
                <label>Clone this repository:</label>
                ${render_clone_str( repository )}
            </div>
        %endif
        <form name="repository_type">
            ${render_repository_type_select_field( repository_type_select_field, render_help=False )}
        </form>
        %if can_push:
            <form name="select_files_to_delete" id="select_files_to_delete" action="${h.url_for( controller='repository', action='select_files_to_delete', id=trans.security.encode_id( repository.id ))}" method="post" >
                <div class="form-row" >
                    <label>Contents:</label>
                    <div id="tree" >
                        Loading...
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        Click on a file to display its contents below.  You may delete files from the repository by clicking the check box next to each file and clicking the <b>Delete selected files</b> button.
                    </div>
                    <input id="selected_files_to_delete" name="selected_files_to_delete" type="hidden" value=""/>
                </div>
                <div class="form-row">
                    <label>Message:</label>
                    <div class="form-row-input">
                        %if commit_message:
                            <textarea name="commit_message" rows="3" cols="35">${commit_message | h}</textarea>
                        %else:
                            <textarea name="commit_message" rows="3" cols="35"></textarea>
                        %endif
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        This is the commit message for the mercurial change set that will be created if you delete selected files.
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <input type="submit" name="select_files_to_delete_button" value="Delete selected files"/>
                </div>
                <div class="form-row">
                    <div id="file_contents" class="toolParamHelp" style="clear: both;background-color:#FAFAFA;"></div>
                </div>
            </form>
        %else:
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
        %endif
    </div>
    <p/>
%endif
