<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    is_new = repository.is_new
    can_contact_owner = trans.user and trans.user != repository.user
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_rate = not is_new and trans.user and repository.user != trans.user
    can_upload = can_push
    can_download = not is_new and ( not is_malicious or can_push )
    can_browse_contents = webapp == 'community' and not is_new
    can_view_change_log = webapp == 'community' and not is_new
    if can_push:
        browse_label = 'Browse or delete repository tip files'
    else:
        browse_label = 'Browse repository tip files'
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
    %if webapp == 'community':
        %if is_new and can_upload:
            <li><a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp=webapp )}">Upload files to repository</a></li>
        %else:
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                %if can_upload:
                    <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp=webapp )}">Upload files to repository</a>
                %endif
                %if can_view_change_log:
                    <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">View change log</a>
                %endif
                %if can_rate:
                    <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">Rate repository</a>
                %endif
                %if can_browse_contents:
                    <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">${browse_label}</a>
                %endif
                %if can_contact_owner:
                    <a class="action-button" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ), webapp=webapp )}">Contact repository owner</a>
                %endif
                %if can_download:
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='gz', webapp=webapp )}">Download as a .tar.gz file</a>
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='bz2', webapp=webapp )}">Download as a .tar.bz2 file</a>
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='zip', webapp=webapp )}">Download as a zip file</a>
                %endif
            </div>
        %endif
    %else:
        <li><a class="action-button" href="${h.url_for( controller='repository', action='install_repository_revision', repository_id=trans.security.encode_id( repository.id ), webapp=webapp, changeset_revision=changeset_revision )}">Install to local Galaxy</a></li>
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Tool Shed Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            <a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_repositories', webapp=webapp )}">Browse valid repositories</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='find_tools', webapp=webapp )}">Search for valid tools</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='find_workflows', webapp=webapp )}">Search for workflows</a>
        </div>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if len( changeset_revision_select_field.options ) > 1:
    <div class="toolForm">
        <div class="toolFormTitle">Repository revision</div>
        <div class="toolFormBody">
            <form name="change_revision" id="change_revision" action="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ), webapp=webapp )}" method="post" >
                <div class="form-row">
                    <%
                        if changeset_revision == repository.tip:
                            tip_str = 'repository tip'
                        else:
                            tip_str = ''
                    %>
                    ${changeset_revision_select_field.get_html()} <i>${tip_str}</i>
                    <div class="toolParamHelp" style="clear: both;">
                        Select a revision to inspect and download versions of tools from this repository.
                    </div>
                </div>
            </form>
        </div>
    </div>
    <p/>
%endif
<div class="toolForm">
    <div class="toolFormTitle">${repository.name}</div>
    <div class="toolFormBody">
        %if can_download:
            <div class="form-row">
                <label>Clone this repository:</label>
                ${render_clone_str( repository )}
            </div>
        %endif
        <div class="form-row">
            <label>Name:</label>
            %if can_browse_contents:
                <a href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">${repository.name}</a>
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
            <label>Revision:</label>
            %if can_view_change_log:
                <a href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">${revision_label}</a>
            %else:
                ${revision_label}
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
${render_repository_items( repository_metadata_id, metadata, webapp=webapp )}
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
%if webapp == 'community' and trans.user and trans.app.config.smtp_server:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Notification on update</div>
        <div class="toolFormBody">
            <form name="receive_email_alerts" id="receive_email_alerts" action="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ), webapp=webapp )}" method="post" >
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
                    <a href="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ), display_reviews=False, webapp=webapp )}"><label>Hide Reviews</label></a>
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
                    <a href="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ), display_reviews=True, webapp=webapp )}"><label>Display Reviews</label></a>
                </div>
            %endif
        </div>
    </div>
%endif
<p/>
