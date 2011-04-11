<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    from urllib import quote_plus

    if cntrller in [ 'tool' ] and can_edit:
        menu_label = 'Edit information or submit for approval'
    else:
        menu_label = 'Edit information'
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

<%def name="title()">Rate Tool</%def>

<h2>Rate Tool</h2>

${tool.get_state_message()}
<p/>

<ul class="manage-table-actions">
    %if can_approve_or_reject:
        <li><a class="action-button" href="${h.url_for( controller='admin', action='set_tool_state', state=trans.model.Tool.states.APPROVED, id=trans.security.encode_id( tool.id ), cntrller=cntrller )}">Approve</a></li>
        <li><a class="action-button" href="${h.url_for( controller='admin', action='set_tool_state', state=trans.model.Tool.states.REJECTED, id=trans.security.encode_id( tool.id ), cntrller=cntrller )}">Reject</a></li>
    %endif
    <li><a class="action-button" id="tool-${tool.id}-popup" class="menubutton">Tool Actions</a></li>
    <div popupmenu="tool-${tool.id}-popup">
        %if can_edit:
            <a class="action-button" href="${h.url_for( controller='common', action='edit_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">${menu_label}</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='common', action='view_tool_history', id=trans.security.encode_id( tool.id ), cntrller=cntrller )}">Tool history</a>
        %if can_download:
            <a class="action-button" href="${h.url_for( controller='common', action='download_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Download tool</a>
        %endif
        %if can_delete:
            <a class="action-button" href="${h.url_for( controller='common', action='delete_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}" confirm="Are you sure you want to delete this tool?">Delete tool</a>
        %endif
        %if can_upload_new_version:
            <a class="action-button" href="${h.url_for( controller='common', action='upload_new_tool_version', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Upload a new version</a>
        %endif
        %if can_purge:
            <li><a class="action-button" href="${h.url_for( controller='admin', action='purge_tool', id=trans.security.encode_id( tool.id ), cntrller=cntrller )}" confirm="Purging removes records from the database, are you sure you want to purge this tool?">Purge tool</a></li>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if can_rate:
    <div class="toolForm">
        <div class="toolFormTitle">${tool.name}</div>
        <div class="toolFormBody">
            <div class="form-row">
                <label>Tool Id:</label>
                ${tool.tool_id}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Version:</label>
                ${tool.version}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                ${tool.description}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>User Description:</label>
                %if tool.user_description:
                    <pre>${tool.user_description}</pre>
                %endif
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Uploaded By:</label>
                ${tool.user.username}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Date Uploaded:</label>
                ${time_ago( tool.create_time )}
                <div style="clear: both"></div>
            </div>
        </div>
    </div>
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Rate and Review</div>
        <div class="toolFormBody">
            <form id="rate_tool" name="rate_tool" action="${h.url_for( controller='common', action='rate_tool', id=trans.security.encode_id( tool.id ), cntrller=cntrller )}" method="post">
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
                        if tra and tra.rating:
                            rating = tra.rating
                        else:
                            rating = 0
                    %>
                    ${render_star_rating( 'rating', rating )}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Review:</label>
                    %if tra and tra.comment:
                        <div class="form-row-input"><textarea name="comment" rows="5" cols="35">${tra.comment}</textarea></div>
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
    %if tool.ratings and ( len( tool.ratings ) > 1 or tool.ratings[0] != tra ):
        <div class="toolForm">
            <div class="toolFormBody">
                %if display_reviews:
                    <div class="form-row">
                        <a href="${h.url_for( controller='common', action='rate_tool', id=trans.security.encode_id( tool.id ), cntrller=cntrller, display_reviews=False )}"><label>Hide Reviews</label></a>
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
                        %for review in tool.ratings:
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
                        <a href="${h.url_for( controller='common', action='rate_tool', id=trans.security.encode_id( tool.id ), cntrller=cntrller, display_reviews=True )}"><label>Display Reviews</label></a>
                    </div>
                %endif
            </div>
        </div>
    %endif
%endif
