<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

<%
    from galaxy.web.framework.helpers import time_ago
    from tool_shed.util.basic_util import to_html_string
    from tool_shed.util.metadata_util import is_malicious
    from tool_shed.repository_types.util import TOOL_DEPENDENCY_DEFINITION

    if repository.metadata_revisions:
        has_metadata = True
    else:
        has_metadata = False

    is_admin = trans.user_is_admin()
    is_new = repository.is_new( trans.app )

    if repository.deprecated:
        is_deprecated = True
    else:
        is_deprecated = False

    if is_malicious( trans.app, trans.security.encode_id( repository.id ), repository.tip( trans.app ) ):
        changeset_is_malicious = True
    else:
        changeset_is_malicious = False

    if not is_deprecated and trans.app.security_agent.can_push( trans.app, trans.user, repository ):
        can_push = True
    else:
        can_push = False

    if not is_deprecated and not is_new and ( not changeset_is_malicious or can_push ):
        can_download = True
    else:
        can_download = False

    if has_metadata and not is_deprecated and trans.app.security_agent.user_can_review_repositories( trans.user ):
        can_review_repository = True
    else:
        can_review_repository = False

    if not is_new and not is_deprecated:
        can_set_metadata = True
    else:
        can_set_metadata = False

    if changeset_revision == repository.tip( trans.app ):
        changeset_revision_is_repository_tip = True
    else:
        changeset_revision_is_repository_tip = False

    if metadata and can_set_metadata and is_admin and changeset_revision_is_repository_tip:
        can_set_malicious = True
    else:
        can_set_malicious = False

    can_view_change_log = not is_new

    if repository_metadata and repository_metadata.includes_tools:
        includes_tools = True
    else:
        includes_tools = False

    if changeset_revision_is_repository_tip:
        tip_str = 'repository tip'
        sharable_link_label = 'Sharable link to this repository:'
        sharable_link_changeset_revision = None
    else:
        tip_str = ''
        sharable_link_label = 'Sharable link to this repository revision:'
        sharable_link_changeset_revision = changeset_revision

    if repository_metadata is None:
        can_render_skip_tool_test_section = False
    else:
        if repository_metadata.changeset_revision is None:
            can_render_skip_tool_test_section = False
        else:
            if includes_tools or repository.type == TOOL_DEPENDENCY_DEFINITION:
                can_render_skip_tool_test_section = True
            else:
                can_render_skip_tool_test_section = False
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
    ${h.css('base','library','jquery.rating')}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js("libs/jquery/jquery.rating", "libs/jquery/jstorage" )}
    ${container_javascripts()}
</%def>

${render_tool_shed_repository_actions( repository, metadata=metadata, changeset_revision=changeset_revision )}

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
            <form name="change_revision" id="change_revision" action="${h.url_for( controller='repository', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
                <div class="form-row">
                    ${changeset_revision_select_field.get_html()} <i>${tip_str}</i>
                    <div class="toolParamHelp" style="clear: both;">
                        %if can_review_repository:
                            Select a revision to inspect for adding or managing a review or for download or installation.
                        %else:
                            Select a revision to inspect for download or installation.
                        %endif
                    </div>
                </div>
            </form>
        </div>
    </div>
    <p/>
%endif
<div class="toolForm">
    <div class="toolFormTitle">Repository '${repository.name | h}'</div>
    <div class="toolFormBody">
        <form name="edit_repository" id="edit_repository" action="${h.url_for( controller='repository', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>${sharable_link_label}</label>
                ${render_sharable_str( repository, changeset_revision=sharable_link_changeset_revision )}
            </div>
            %if can_download or can_push:
                <div class="form-row">
                    <label>Clone this repository:</label>
                    ${render_clone_str( repository )}
                </div>
            %endif
            <div class="form-row">
                <label>Name:</label>
                %if repository.times_downloaded > 0:
                    ${repository.name}
                %else:
                    <input name="repo_name" type="textfield" value="${repository.name | h}" size="40"/>
                %endif
                <div class="toolParamHelp" style="clear: both;">
                    Repository names cannot be changed if the repository has been cloned.
                </div>
                <div style="clear: both"></div>
            </div>
            ${render_repository_type_select_field( repository_type_select_field, render_help=True )}
            <div class="form-row">
                <label>Synopsis:</label>
                <input name="description" type="textfield" value="${description | h}" size="80"/>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Detailed description:</label>
                %if long_description:
                    <pre><textarea name="long_description" rows="3" cols="80">${long_description | h}</textarea></pre>
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
                ${repository.user.username | h}
            </div>
            <div class="form-row">
                <label>This revision can be installed:</label>
                ${revision_installable}
            </div>
            <div class="form-row">
                <label>Times cloned / installed:</label>
                ${repository.times_downloaded | h}
            </div>
            %if is_admin:
                <div class="form-row">
                    <label>Location:</label>
                    ${repository.repo_path( trans.app ) | h}
                </div>
                <div class="form-row">
                    <label>Deleted:</label>
                    ${repository.deleted | h}
                </div>
            %endif
            <div class="form-row">
                <input type="submit" name="edit_repository_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
${render_repository_items( metadata, containers_dict, can_set_metadata=True, render_repository_actions_for='tool_shed' )}
%if can_render_skip_tool_test_section:
    <p/>
    <div class="toolForm">
        %if repository.type == TOOL_DEPENDENCY_DEFINITION:
            <div class="toolFormTitle">Automated tool dependency test</div>
        %else:
            <div class="toolFormTitle">Automated tool tests</div>
        %endif
        <div class="toolFormBody">
            <form name="skip_tool_tests" id="skip_tool_tests" action="${h.url_for( controller='repository', action='manage_repository', id=trans.security.encode_id( repository.id ), changeset_revision=str( repository_metadata.changeset_revision ) )}" method="post" >
                <div class="form-row">
                    %if repository.type == TOOL_DEPENDENCY_DEFINITION:
                        <label>Skip automated testing of this tool dependency recipe</label>
                    %else:
                        <label>Skip automated testing of tools in this revision:</label>
                    %endif
                    ${skip_tool_tests_check_box.get_html()}
                    <div class="toolParamHelp" style="clear: both;">
                        %if repository.type == TOOL_DEPENDENCY_DEFINITION:
                            Check the box and click <b>Save</b> to skip automated testing of this tool dependency recipe.
                        %else:
                            Check the box and click <b>Save</b> to skip automated testing of the tools in this revision.
                        %endif
                    </div>
                </div>
                <div style="clear: both"></div>
                <div class="form-row">
                <label>Reason for skipping automated testing:</label>
                %if skip_tool_test:
                    <pre><textarea name="skip_tool_tests_comment" rows="3" cols="80">${skip_tool_test.comment | h}</textarea></pre>
                %else:
                    <textarea name="skip_tool_tests_comment" rows="3" cols="80"></textarea>
                %endif
                </div>
                <div style="clear: both"></div>
                <div class="form-row">
                    <input type="submit" name="skip_tool_tests_button" value="Save"/>
                </div>
            </form>
        </div>
    </div>
%endif
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
                            <option value="${trans.security.encode_id( category.id )}" selected>${category.name | h}</option>
                        %else:
                            <option value="${trans.security.encode_id( category.id )}">${category.name | h}</option>
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
                <td>${repository.user.username | h}</td>
                <td>owner</td>
                <td>&nbsp;</td>
            </tr>
            %for username in current_allow_push_list:
                %if username != repository.user.username:
                    <tr>
                        <td>${username | h}</td>
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
                ${num_ratings | h}
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
                                <td>${review.user.username | h}</td>
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
%if can_set_malicious:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Malicious repository tip</div>
        <div class="toolFormBody">
            <form name="malicious" id="malicious" action="${h.url_for( controller='repository', action='set_malicious', id=trans.security.encode_id( repository.id ), ctx_str=changeset_revision )}" method="post">
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
