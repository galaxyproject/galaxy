<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

<%
    from tool_shed.grids.util import build_approved_select_field
    from tool_shed.util.container_util import STRSEP

    if installable:
        installable_str = 'yes'
    else:
        installable_str = 'no'
    can_review_repositories = trans.app.security_agent.user_can_review_repositories( trans.user )
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
    ${h.css('base','jquery.rating')}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/jquery/jquery.rating" )}
    ${common_javascripts(repository)}
</%def>

${render_tool_shed_repository_actions( repository=repository, changeset_revision=changeset_revision )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Revision reviews of repository '${repository.name | h}'</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Revision:</label>
            <a class="action-button" href="${h.url_for( controller='repository_review', action='view_or_manage_repository', id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">${changeset_revision_label}</a>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Revision is installable:</label>
            ${installable_str | h}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            %if reviews:
                <table class="grid">
                    <tr>
                        <th>Reviewer</th>
                        <th>Repository rating</th>
                        <th>Approved</th>
                        <th></th>
                    </tr>
                    %for review in reviews:
                        <%
                            encoded_review_id = trans.security.encode_id( review.id )
                            approved_select_field_name = '%s%sapproved' % ( encoded_review_id, STRSEP )
                            approved_select_field_selected_value = review.approved
                            approved_select_field = build_approved_select_field( trans, name=approved_select_field_name, selected_value=approved_select_field_selected_value, for_component=False )
                            if review.approved not in [ None, 'None', 'none' ]:
                                approved_str = review.approved
                            else:
                                approved_str = ''
                            repository_rating_name = '%srepository_rating' % encoded_review_id
                        %>
                        <tr>
                            <td>
                                <div style="float:left;" class="menubutton split popup" id="${encoded_review_id}-popup">
                                    <a class="view-info" href="${h.url_for( controller='repository_review', action='repository_reviews_by_user', id=trans.security.encode_id( review.user.id ) )}">${review.user.username | h}</a>
                                </div>
                                <div popupmenu="${encoded_review_id}-popup">
                                    %if review.user == trans.user:
                                        <a class="action-button" href="${h.url_for( controller='repository_review', action='edit_review', id=encoded_review_id )}">Edit my review</a>
                                    %else:
                                        <a class="action-button" href="${h.url_for( controller='repository_review', action='browse_review', id=encoded_review_id )}">Browse this review</a>
                                    %endif
                                </div>
                            </td>
                            <td>${render_star_rating( repository_rating_name, review.rating, disabled=True )}</td>
                            %if review.user == trans.user:
                                <form name="approve_repository_review" action="${h.url_for( controller='repository_review', action='approve_repository_review', id=encoded_review_id ) }" method="post" >
                                    <td>${approved_select_field.get_html()}</td>
                                    <td><input type="submit" name="approve_repository_review_button" value="Save"/></td>
                                </form>
                            %else:
                                <td>${approved_str | h}</td>
                                <td></td>
                            %endif
                        </tr>
                    %endfor
                </table>
            %else:
                <label>This repository revision has not yet been reviewed:</label>
                %if can_review_repositories:
                    <a class="action-button" href="${h.url_for( controller='repository_review', action='create_review', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Add a review to this revision</a>
                    <div style="clear: both"></div>
                %endif
            %endif
        </div>
        <div style="clear: both"></div>
    </div>
</div>
