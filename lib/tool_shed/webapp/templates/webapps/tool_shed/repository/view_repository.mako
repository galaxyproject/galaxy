<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    from tool_shed.util.basic_util import to_html_string

    is_new = repository.is_new()
    is_deprecated = repository.deprecated

    can_browse_contents = trans.webapp.name == 'tool_shed' and not is_new
    can_push = not is_deprecated and trans.app.security_agent.can_push( trans.app, trans.user, repository )
    can_download = not is_deprecated and not is_new and ( not is_malicious or can_push )
    can_view_change_log = trans.webapp.name == 'tool_shed' and not is_new
    changeset_revision_is_repository_tip = changeset_revision == repository.tip()

    if changeset_revision_is_repository_tip:
        tip_str = 'repository tip'
        sharable_link_label = 'Link to this repository:'
        sharable_link_changeset_revision = None
    else:
        tip_str = ''
        sharable_link_label = 'Link to this repository revision:'
        sharable_link_changeset_revision = changeset_revision

    if heads:
        multiple_heads = len( heads ) > 1
    else:
        multiple_heads = False

    if repository_metadata is None:
        revision_installable = False
    else:
        if repository_metadata.downloadable is None:
            revision_installable = 'unknown'
        else:
            revision_installable = repository_metadata.downloadable
%>

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
    ${h.css('base','library')}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${container_javascripts()}
</%def>

%if trans.webapp.name == 'tool_shed':
    ${render_tool_shed_repository_actions( repository=repository, metadata=metadata, changeset_revision=changeset_revision )}
%else:
    ${render_galaxy_repository_actions( repository=repository )}
%endif

%if message:
    ${render_msg( message, status )}
%endif

%if repository.deprecated:
    <div class="warningmessage">
        This repository has been marked as deprecated, so some tool shed features may be restricted.
    </div>
%endif:
%if multiple_heads:
    ${render_multiple_heads_message( heads )}
%endif
%if deprecated_repository_dependency_tups:
    ${render_deprecated_repository_dependencies_message( deprecated_repository_dependency_tups )}
%endif

%if len( changeset_revision_select_field.options ) > 1:
    <div class="toolForm">
        <div class="toolFormTitle">Repository revision</div>
        <div class="toolFormBody">
            <form name="change_revision" id="change_revision" action="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
                <div class="form-row">
                    ${render_select(changeset_revision_select_field)} <i>${tip_str}</i>
                    <div class="toolParamHelp" style="clear: both;">
                        Select a revision to inspect and download versions of Galaxy utilities from this repository.
                    </div>
                </div>
            </form>
        </div>
    </div>
    <p/>
%endif
<div class="toolForm">
    <div class="toolFormTitle">Repository <b>${repository.name | h}</b></div>
    <div class="toolFormBody">
        <div class="form-row">
            <b>Name:</b>\
            %if can_browse_contents:
                <a title="Browse the contents of this repository" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">${repository.name}</a>
            %else:
                ${repository.name | h}
            %endif
        </div>
        <div class="form-row">
            <b>Owner:</b>
            <a title="See all repositories owned by ${ repository.user.username | h }" href="${h.url_for( controller='repository', action='browse_repositories_by_user', user_id=trans.app.security.encode_id( repository.user.id ) )}">${ repository.user.username | h }</a>
        </div>
        <div class="form-row">
            <b>Synopsis:</b>
            ${repository.description | h}
        </div>
        %if repository.long_description:
            <div class="form-row">
                ${render_long_description( to_html_string( repository.long_description ) )}
            </div>
        %endif
        %if repository.homepage_url:
        <div class="form-row">
            <b>Content homepage:</b>
            <a href="${repository.homepage_url | h}" target="_blank">${repository.homepage_url | h}</a>
        </div>
        %endif
        %if repository.remote_repository_url:
        <div class="form-row">
            <b>Development repository:</b>
            <a href="${repository.remote_repository_url | h}" target="_blank">${repository.remote_repository_url | h}</a>
        </div>
        %endif
        <div class="form-row">
            <b>${sharable_link_label}</b>
            <a href="${ repository.share_url }" target="_blank">${ repository.share_url }</a>
            <button title="to clipboard" class="btn btn-secondary btn-sm" id="share_clipboard"><span class="fa fa-clipboard"></span></button>
        </div>
        %if can_download or can_push:
            <div class="form-row">
                <b>Clone this repository:</b>
                <code>hg clone <a title="Show in mercurial browser" href="${ repository.clone_url }">${ repository.clone_url }</a></code>
                <button title="to clipboard" class="btn btn-secondary btn-sm" id="clone_clipboard"><span class="fa fa-clipboard"></span></button>
            </div>
        %endif
        <div class="form-row">
            <b>Type:</b>
            ${repository.type | h}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <b>Revision:</b>
            %if can_view_change_log:
                <a title="See the revision history" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">${revision_label}</a>
            %else:
                ${revision_label}
            %endif
        </div>
        <div class="form-row">
            <b>This revision can be installed:</b>
            ${revision_installable}
        </div>
        <div class="form-row">
            <b>Times cloned / installed:</b>
            ${repository.times_downloaded}
        </div>
        %if trans.user_is_admin:
            <div class="form-row">
                <b>Location:</b>
                ${repository.repo_path( trans.app ) | h}
            </div>
            <div class="form-row">
                <b>Deleted:</b>
                ${repository.deleted}
            </div>
        %endif
    </div>
</div>
${render_repository_items( metadata, containers_dict, can_set_metadata=False, render_repository_actions_for='tool_shed' )}
%if repository.categories:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Categories</div>
        <div class="toolFormBody">
            %for rca in repository.categories:
                <div class="form-row">
                    <a href="${h.url_for( controller='repository', action='browse_repositories_in_category', id=trans.security.encode_id( rca.category.id ) )}">${rca.category.name | h}</a> - ${rca.category.description | h}
                </div>
            %endfor
            <div style="clear: both"></div>
        </div>
    </div>
%endif
%if trans.webapp.name == 'tool_shed' and trans.user and trans.app.config.smtp_server:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Notification on update</div>
        <div class="toolFormBody">
            <form name="receive_email_alerts" id="receive_email_alerts" action="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
                <div class="form-row">
                    <label>Receive email alerts:</label>
                    ${render_checkbox(alerts_check_box)}
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
                <div style="clear: both"></div>
                <div class="form-row">
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
                                <td>${render_review_comment( to_html_string( review.comment ) )}</td>
                                <td>${time_ago( review.update_time )}</td>
                                <td>${review.user.username}</td>
                            </tr>
                        %endfor
                    </table>
                </div>
                <div style="clear: both"></div>
            %else:
                <div class="form-row">
                    <a href="${h.url_for( controller='repository', action='view_repository', id=trans.security.encode_id( repository.id ), display_reviews=True )}"><label>Display Reviews</label></a>
                </div>
                <div style="clear: both"></div>
            %endif
        </div>
    </div>
%endif
<p/>
