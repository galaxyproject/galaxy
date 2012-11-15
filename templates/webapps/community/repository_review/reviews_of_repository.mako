<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
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
    if mine:
        title = "My reviews of repository '%s'" % repository.name
        review_revision_label = "Manage my review of this revision"
    else:
        title = "All reviews of repository '%s'" % repository.name
        review_revision_label = "Inspect reviews of this revision"
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

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
            <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip( trans.app ) )}">Manage repository</a>
        %else:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip( trans.app ) )}">View repository</a>
        %endif
        %if can_view_change_log:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.security.encode_id( repository.id ) )}">View change log</a>
        %endif
        %if can_rate:
            <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.security.encode_id( repository.id ) )}">Rate repository</a>
        %endif
        %if can_browse_contents:
            <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">${browse_label | h}</a>
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
    <div class="toolFormTitle">${title | h}</div>
    <div class="toolFormBody">
        <div class="form-row">
            <table class="grid">
                <tr>
                    <th>Revision</th>
                    <th>Reviewers</th>
                    <th>Installable</th>
                </tr>
                %for changeset_revision, revision_dict in reviews_dict.items():
                    <%
                        changeset_revision_label = revision_dict[ 'changeset_revision_label' ]
                        repository_reviews = revision_dict[ 'repository_reviews' ]
                        repository_metadata_reviews = revision_dict[ 'repository_metadata_reviews' ]
                        reviewers_str = ''
                        if repository_reviews:
                            for repository_review in repository_reviews:
                                reviewers_str += '<a class="view-info" href="'
                                if repository_review.user == trans.user:
                                    reviewers_str += 'edit_review'
                                else:
                                    reviewers_str += 'browse_review'
                                reviewers_str += '?id=%s">%s</a>' % ( trans.security.encode_id( repository_review.id ), repository_review.user.username )
                                reviewers_str += ' | '
                            reviewers_str = reviewers_str.rstrip( '| ' )
                        if revision_dict[ 'installable' ]:
                            installable_str = 'yes'
                        else:
                            installable_str = ''
                        can_add_review = revision_dict[ 'can_add_review' ]
                    %>
                    <tr>
                        <td>
                            <div style="float:left;" class="menubutton split popup" id="${changeset_revision}-popup">
                                <a class="view-info" href="${h.url_for( controller='repository_review', action='view_or_manage_repository', id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">${changeset_revision_label | h}</a>
                            </div>
                            <div popupmenu="${changeset_revision}-popup">
                                %if repository_reviews:
                                    <a class="action-button" href="${h.url_for( controller='repository_review', action='manage_repository_reviews_of_revision', id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Browse reviews of this revision</a>
                                %elif can_add_review:
                                    <a class="action-button" href="${h.url_for( controller='repository_review', action='create_review', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Add a review to this revision</a>
                                %endif
                            </div>
                        </td>
                        <td>${reviewers_str}</td>
                        <td>${installable_str | h}</td>
                    </tr>
                %endfor
            </table>
        </div>
        <div style="clear: both"></div>
    </div>
</div>
