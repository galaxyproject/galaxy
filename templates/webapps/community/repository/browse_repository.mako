<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    is_new = repository.is_new
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_upload = can_push
    can_browse_contents = not is_new
    can_rate = repository.user != trans.user
    can_manage = repository.user == trans.user
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
                <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ) )}">Manage repository</a>
            %else:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ) )}">View repository</a>
            %endif
            %if can_upload:
                <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
            %endif
            %if can_view_change_log:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">View change log</a>
            %endif
            %if can_rate:
                <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
            %endif
        </div>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if can_browse_contents:
    <div class="toolForm">
        <div class="toolFormTitle">Browse ${repository.name}</div>
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
