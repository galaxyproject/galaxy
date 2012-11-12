<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    from galaxy.webapps.community.controllers.repository_review import build_approved_select_field
    from galaxy.webapps.community.controllers.common import STRSEP
    is_admin = trans.user_is_admin()
    is_new = repository.is_new( trans.app )
    can_browse_contents = not is_new
    can_contact_owner = trans.user and trans.user != repository.user
    can_manage = is_admin or repository.user == trans.user
    can_push = trans.app.security_agent.can_push( trans.app, trans.user, repository )
    can_rate = not is_new and trans.user and repository.user != trans.user
    can_view_change_log = not is_new
    if can_push:
        browse_label = 'Browse or delete repository tip files'
    else:
        browse_label = 'Browse repository tip files'
    if installable:
        installable_str = 'yes'
    else:
        installable_str = 'no'
    can_review_repositories = trans.app.security_agent.user_can_review_repositories( trans.user )
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
    ${h.css('base','panel_layout','jquery.rating')}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/jquery/jquery.rating" )}
    ${common_javascripts(repository)}
</%def>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        %if can_manage:
            <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Manage repository</a>
        %else:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">View repository</a>
        %endif
        %if can_view_change_log:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.security.encode_id( repository.id ) )}">View change log</a>
        %endif
        %if can_rate:
            <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.security.encode_id( repository.id ) )}">Rate repository</a>
        %endif
        %if can_browse_contents:
            <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">${browse_label}</a>
        %endif
        %if can_contact_owner:
            <a class="action-button" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ) )}">Contact repository owner</a>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Revision reviews of repository '${repository.name | h}'</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Revision:</label>
            <a class="action-button" href="${h.url_for( controller='repository_review', action='view_or_manage_repository', id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">${changeset_revision_label | h}</a>
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
