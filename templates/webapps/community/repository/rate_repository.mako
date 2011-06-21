<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    from urllib import quote_plus
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
</%def>

%if message:
    ${render_msg( message, status )}
%endif

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
            %if can_browse_contents:
                <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">Browse or delete repository files</a>
            %endif
            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='gz' )}">Download as a .tar.gz file</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='bz2' )}">Download as a .tar.bz2 file</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='zip' )}">Download as a zip file</a>
        </div>
    %endif
</ul>

%if repository.user != trans.user:
    <div class="toolForm">
        <div class="toolFormTitle">${repository.name}</div>
        <div class="toolFormBody">
            <div class="form-row">
                <label>Description:</label>
                ${repository.description}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Version:</label>
                ${repository.version}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Owner:</label>
                ${repository.user.username}
                <div style="clear: both"></div>
            </div>
        </div>
    </div>
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Rate and Review</div>
        <div class="toolFormBody">
            <form id="rate_repository" name="rate_repository" action="${h.url_for( controller='repository', action='rate_repository', id=trans.security.encode_id( repository.id ) )}" method="post">
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
                <div class="form-row">
                    <label>Your Rating:</label>
                    <%
                        if rra and rra.rating:
                            rating = rra.rating
                        else:
                            rating = 0
                    %>
                    ${render_star_rating( 'rating', rating )}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Review:</label>
                    %if rra and rra.comment:
                        <div class="form-row-input"><textarea name="comment" rows="5" cols="35">${rra.comment}</textarea></div>
                    %else:
                        <div class="form-row-input"><textarea name="comment" rows="5" cols="35"></textarea></div>
                    %endif
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <input type="submit" name="rate_button" id="rate_button" value="Submit" />
                </div>
            </form>
        </div>
    </div>
    <p/>
    %if repository.ratings and ( len( repository.ratings ) > 1 or repository.ratings[0] != rra ):
        <div class="toolForm">
            <div class="toolFormBody">
                %if display_reviews:
                    <div class="form-row">
                        <a href="${h.url_for( controller='repository', action='rate_repository', id=trans.security.encode_id( repository.id ), display_reviews=False )}"><label>Hide Reviews</label></a>
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
                                <td>${review.comment}</td>
                                <td>${time_ago( review.update_time )}</td>
                                <td>${review.user.username}</td>
                            </tr>
                        %endfor
                    </table>
                %else:
                    <div class="form-row">
                        <a href="${h.url_for( controller='repository', action='rate_repository', id=trans.security.encode_id( repository.id ), display_reviews=True )}"><label>Display Reviews</label></a>
                    </div>
                %endif
            </div>
        </div>
    %endif
%endif
