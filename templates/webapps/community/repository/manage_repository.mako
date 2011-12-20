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
    can_set_metadata = not is_new
    can_rate = not is_new and trans.user and repository.user != trans.user
    can_view_change_log = not is_new
    if can_push:
        browse_label = 'Browse or delete repository tip files'
    else:
        browse_label = 'Browse repository tip files'
    can_set_malicious = metadata and can_set_metadata and is_admin and changeset_revision == repository.tip
    can_reset_all_metadata = is_admin and len( repo ) > 0
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
        <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
    %else:
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            %if can_upload:
                <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
            %endif
            %if can_view_change_log:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ), webapp='community' )}">View change log</a>
            %endif
            %if can_rate:
                <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
            %endif
            %if can_browse_contents:
                <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ), webapp='community' )}">${browse_label}</a>
            %endif
            %if can_contact_owner:
                <a class="action-button" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ), webapp='community' )}">Contact repository owner</a>
            %endif
            %if can_reset_all_metadata:
                <a class="action-button" href="${h.url_for( controller='repository', action='reset_all_metadata', id=trans.security.encode_id( repository.id ), webapp='community' )}">Reset all repository metadata</a>
            %endif
            %if can_download:
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='gz' )}">Download as a .tar.gz file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='bz2' )}">Download as a .tar.bz2 file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='zip' )}">Download as a zip file</a>
            %endif
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
            <form name="change_revision" id="change_revision" action="${h.url_for( controller='repository', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
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
        <form name="edit_repository" id="edit_repository" action="${h.url_for( controller='repository', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            %if can_download:
                <div class="form-row">
                    <label>Clone this repository:</label>
                    ${render_clone_str( repository )}
                </div>
            %endif
            <div class="form-row">
                <label>Name:</label>
                %if repository.times_downloaded > 0:
                    ${repo_name}
                %else:
                    <input name="repo_name" type="textfield" value="${repo_name}" size="40"/>
                %endif
                <div class="toolParamHelp" style="clear: both;">
                    Repository names cannot be changed if the repository has been cloned.
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Synopsis:</label>
                <input name="description" type="textfield" value="${description}" size="80"/>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Detailed description:</label>
                %if long_description:
                    <pre><textarea name="long_description" rows="3" cols="80">${long_description}</textarea></pre>
                %else:
                    <textarea name="long_description" rows="3" cols="80"></textarea>
                %endif
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Revision:</label>
                %if can_view_change_log:
                    <a href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">${revision_label}</a>
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
            %if is_admin:
                <div class="form-row">
                    <label>Location:</label>
                    ${repository.repo_path}
                </div>
                <div class="form-row">
                    <label>Deleted:</label>
                    ${repository.deleted}
                </div>
            %endif
            <div class="form-row">
                <input type="submit" name="edit_repository_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
${render_repository_items( repository_metadata_id, metadata, can_set_metadata=True )}
<p/>
<div class="toolForm">
    <div class="toolFormTitle">Manage categories</div>
    <div class="toolFormBody">
        <form name="categories" id="categories" action="${h.url_for( controller='repository', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>Categories</label>
                <select name="category_id" multiple>
                    %for category in categories:
                        %if category.id in selected_categories:
                            <option value="${trans.security.encode_id( category.id )}" selected>${category.name}</option>
                        %else:
                            <option value="${trans.security.encode_id( category.id )}">${category.name}</option>
                        %endif
                    %endfor
                </select>
                <div class="toolParamHelp" style="clear: both;">
                    Multi-select list - hold the appropriate key while clicking to select multiple categories.
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="manage_categories_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
%if trans.app.config.smtp_server:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Notification on update</div>
        <div class="toolFormBody">
            <form name="receive_email_alerts" id="receive_email_alerts" action="${h.url_for( controller='repository', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
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
<p/>
<div class="toolForm">
    <div class="toolFormTitle">Grant authority to make changes</div>
    <div class="toolFormBody">
        <table class="grid">
            <tr>
                <td>${repository.user.username}</td>
                <td>owner</td>
                <td>&nbsp;</td>
            </tr>
            %for username in current_allow_push_list:
                %if username != repository.user.username:
                    <tr>
                        <td>${username}</td>
                        <td>write</td>
                        <td><a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.security.encode_id( repository.id ), user_access_button='Remove', remove_auth=username )}">remove</a>
                    </tr>
                %endif
            %endfor
        </table>
        <br clear="left"/>
        <form name="user_access" id="user_access" action="${h.url_for( controller='repository', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>Username:</label>
                ${allow_push_select_field.get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    Multi-select usernames to grant permission to make changes to this repository
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="user_access_button" value="Grant access"/>
            </div>
        </form>
    </div>
</div>
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
                    <a href="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ), display_reviews=False, webapp='community' )}"><label>Hide Reviews</label></a>
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
                    <a href="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ), display_reviews=True, webapp='community' )}"><label>Display Reviews</label></a>
                </div>
            %endif
        </div>
    </div>
%endif
<p/>
%if can_set_malicious:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Malicious repository tip</div>
        <div class="toolFormBody">
            <form name="malicious" id="malicious" action="${h.url_for( controller='repository', action='set_metadata', id=trans.security.encode_id( repository.id ), ctx_str=changeset_revision )}" method="post">
                <div class="form-row">
                    <label>Define repository tip as malicious:</label>
                    ${malicious_check_box.get_html()}
                    <div class="toolParamHelp" style="clear: both;">
                        Check the box and click <b>Save</b> to define this repository's tip as malicious, restricting it from being download-able.
                    </div>
                </div>
                <div class="form-row">
                    <input type="submit" name="malicious_button" value="Save"/>
                </div>
            </form>
        </div>
    </div>
%endif
<p/>
