<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    is_admin = trans.user_is_admin()
    is_new = repository.is_new
    can_contact_owner = trans.user and trans.user != repository.user
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_upload = can_push
    can_download = not is_new and ( not is_malicious or can_push )
    can_browse_contents = not is_new
    can_rate = trans.user and repository.user != trans.user
    can_manage = is_admin or repository.user == trans.user
    can_view_change_log = not is_new
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "jquery.rating", "dynatree_skin/ui.dynatree" )}
    <style type="text/css">
    ul.fileBrowser,
    ul.toolFile {
        margin-left: 0;
        padding-left: 0;
        list-style: none;
    }
    ul.fileBrowser {
        margin-left: 20px;
    }
    .fileBrowser li,
    .toolFile li {
        padding-left: 20px;
        background-repeat: no-repeat;
        background-position: 0;
        min-height: 20px;
    }
    .toolFile li {
        background-image: url( ${h.url_for( '/static/images/silk/page_white_compressed.png' )} );
    }
    .fileBrowser li {
        background-image: url( ${h.url_for( '/static/images/silk/page_white.png' )} );
    }
    </style>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "jquery.rating", "ui.core", "jquery.cookie", "jquery.dynatree" )}
    ${common_javascripts(repository)}
</%def>

<br/><br/>
<ul class="manage-table-actions">
    %if is_new:
        <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
    %else:
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            %if can_manage:
                <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip )}">Manage repository</a>
            %else:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, webapp='community' )}">View repository</a>
            %endif
            %if can_upload:
                <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
            %endif
            %if can_view_change_log:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ), webapp='community' )}">View change log</a>
            %endif
            %if can_rate:
                <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
            %endif
            %if can_download:
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, file_type='gz' )}">Download as a .tar.gz file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, file_type='bz2' )}">Download as a .tar.bz2 file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, file_type='zip' )}">Download as a zip file</a>
            %endif
        </div>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if can_browse_contents:
    <div class="toolForm">
        <div class="toolFormTitle">Browse ${repository.name} revision ${repository.tip} (repository tip)</div>
        %if can_download:
            <div class="form-row">
                <label>Clone this repository:</label>
                ${render_clone_str( repository )}
            </div>
        %endif
        %if can_push:
            <form name="select_files_to_delete" id="select_files_to_delete" action="${h.url_for( controller='repository', action='select_files_to_delete', id=trans.security.encode_id( repository.id ))}" method="post" >
                <div class="form-row" >
                    <label>Contents:</label>
                    <div id="tree" >
                        Loading...
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        Click on a file to display it's contents below.  You may delete files from the repository by clicking the check box next to each file and clicking the <b>Delete selected files</b> button.
                    </div>
                    <input id="selected_files_to_delete" name="selected_files_to_delete" type="hidden" value=""/>
                </div>
                <div class="form-row">
                    <label>Message:</label>
                    <div class="form-row-input">
                        %if commit_message:
                            <textarea name="commit_message" rows="3" cols="35">${commit_message}</textarea>
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
