<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    is_new = repository.is_new
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_rate = not is_new and trans.user and repository.user != trans.user
    can_upload = can_push
    can_browse_contents = not is_new
    can_view_change_log = not is_new
    if can_push:
        browse_label = 'Browse or delete repository files'
    else:
        browse_label = 'Browse repository files'
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
    ${h.css( "jquery.rating" )}
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
    ${h.js( "jquery.rating" )}
    ${common_javascripts(repository)}
</%def>

<br/><br/>
<ul class="manage-table-actions">
    %if is_new and can_upload:
        <li><a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a></li>
    %else:
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            %if can_upload:
                <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
            %endif
            %if can_view_change_log:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">View change log</a>
            %endif
            %if can_rate:
                <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
            %endif
            %if can_browse_contents:
                <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">${browse_label}</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='gz' )}">Download as a .tar.gz file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='bz2' )}">Download as a .tar.bz2 file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='zip' )}">Download as a zip file</a>
            %endif
        </div>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${repository.name}</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Clone this repository:</label>
            ${render_clone_str( repository )}
        </div>
        <div class="form-row">
            <label>Name:</label>
            %if can_browse_contents:
                <a href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">${repository.name}</a>
            %else:
                ${repository.name}
            %endif
        </div>
        <div class="form-row">
            <label>Synopsis:</label>
            ${repository.description}
        </div>
        %if repository.long_description:
            <div class="form-row">
                <label>Detailed description:</label>
                <pre>${repository.long_description}</pre>
                <div style="clear: both"></div>
            </div>
        %endif
        <div class="form-row">
            <label>Version:</label>
            %if can_view_change_log:
                <a href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">${repository.revision}</a>
            %else:
                ${repository.revision}
            %endif
        </div>
        <div class="form-row">
            <label>Owner:</label>
            ${repository.user.username}
        </div>
        <div class="form-row">
            <label>Times downloaded:</label>
            ${repository.times_downloaded}
        </div>
        %if trans.user_is_admin():
            <div class="form-row">
                <label>Location:</label>
                ${repository.repo_path}
            </div>
            <div class="form-row">
                <label>Deleted:</label>
                ${repository.deleted}
            </div>
        %endif
    </div>
</div>
%if repository.categories:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Categories</div>
        <div class="toolFormBody">
            %for rca in repository.categories:
                <div class="form-row">
                    ${rca.category.name}
                </div>
            %endfor
            <div style="clear: both"></div>
        </div>
    </div>
%endif
%if metadata:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Repository metadata</div>
        <div class="toolFormBody">
            %if 'tools' in metadata:
                <div class="form-row">
                    <table width="100%">
                        <tr bgcolor="#D8D8D8" width="100%">
                            <td><label>Tools:</label></td>
                        </tr>
                    </table>
                </div>
                <div class="form-row">
                    <% tool_dicts = metadata[ 'tools' ] %>
                    <table class="grid">
                        <tr>
                            <td><b>name</b></td>
                            <td><b>description</b></td>
                            <td><b>version</b></td>
                            <td><b>requirements</b></td>
                        </tr>
                        %for tool_dict in tool_dicts:
                            <tr>
                                <td><a href="${h.url_for( controller='repository', action='display_tool', repository_id=trans.security.encode_id( repository.id ), tool_config=tool_dict[ 'tool_config' ] )}">${tool_dict[ 'name' ]}</a></td>
                                <td>${tool_dict[ 'description' ]}</td>
                                <td>version: ${tool_dict[ 'version' ]}</td>
                                <td>
                                    <%
                                        if 'requirements' in tool_dict:
                                            requirements = tool_dict[ 'requirements' ]
                                        else:
                                            requirements = None
                                    %>
                                    %if requirements:
                                        <%
                                            requirements_str = ''
                                            for requirement_dict in tool_dict[ 'requirements' ]:
                                                requirements_str += '%s (%s), ' % ( requirement_dict[ 'name' ], requirement_dict[ 'type' ] )
                                            requirements_str = requirements_str.rstrip( ', ' )
                                        %>
                                        ${requirements_str}
                                    %else:
                                        none
                                    %endif
                                </td>
                            </tr>
                        %endfor
                    </table>
                </div>
                <div style="clear: both"></div>
            %endif
            %if 'workflows' in metadata:
                <div class="form-row">
                    <table width="100%">
                        <tr bgcolor="#D8D8D8" width="100%">
                            <td><label>Workflows:</label></td>
                        </tr>
                    </table>
                </div>
                <div style="clear: both"></div>
                <div class="form-row">
                    <% workflow_dicts = metadata[ 'workflows' ] %>
                    <table class="grid">
                        <tr>
                            <td><b>name</b></td>
                            <td><b>format-version</b></td>
                            <td><b>annotation</b></td>
                        </tr>
                        %for workflow_dict in workflow_dicts:
                            <tr>
                                <td>${workflow_dict[ 'name' ]}</td>
                                <td>${workflow_dict[ 'format-version' ]}</td>
                                <td>${workflow_dict[ 'annotation' ]}</td>
                            </tr>
                        %endfor
                    </table>
                </div>
                <div style="clear: both"></div>
            %endif
        </div>
    </div>
%endif
%if trans.user and trans.app.config.smtp_server:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Notification on update</div>
        <div class="toolFormBody">
            <form name="receive_email_alerts" id="receive_email_alerts" action="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
                <div class="form-row">
                    <label>Receive email alerts:</label>
                    ${alerts_check_box.get_html()}
                    <div class="toolParamHelp" style="clear: both;">
                        Check the box and click <b>Save</b> to receive email alerts when updates to this repository occur.
                    </div>
                </div>
                <div class="form-row">
                    <input type="submit" name="receive_email_alerts_button" value="Save"/>
                </div>
            </form>
        </div>
    </div>
%endif
%if repository.ratings:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Rating</div>
        <div class="toolFormBody">
            <div class="form-row">
                <label>Times Rated:</label>
                ${num_ratings}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Average Rating:</label>
                ${render_star_rating( 'avg_rating', avg_rating, disabled=True )}
                <div style="clear: both"></div>
            </div>
        </div>
    </div>
    <p/>
    <div class="toolForm">
        <div class="toolFormBody">
            %if display_reviews:
                <div class="form-row">
                    <a href="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ), display_reviews=False )}"><label>Hide Reviews</label></a>
                </div>
                <table class="grid">
                    <thead>
                        <tr>
                            <th>Rating</th>
                            <th>Comments</th>
                            <th>Reviewed</th>
                            <th>User</th>
                        </tr>
                    </thead>
                    <% count = 0 %>
                    %for review in repository.ratings:
                        <%
                            count += 1
                            name = 'rating%d' % count
                        %>
                        <tr>
                            <td>${render_star_rating( name, review.rating, disabled=True )}</td>
                            <td><pre>${review.comment}</pre></td>
                            <td>${time_ago( review.update_time )}</td>
                            <td>${review.user.username}</td>
                        </tr>
                    %endfor
                </table>
            %else:
                <div class="form-row">
                    <a href="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ), display_reviews=True )}"><label>Display Reviews</label></a>
                </div>
            %endif
        </div>
    </div>
%endif
<p/>
