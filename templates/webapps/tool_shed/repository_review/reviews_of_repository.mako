<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

<%
    if mine:
        title = "My reviews of repository '%s'" % repository.name
    else:
        title = "All reviews of repository '%s'" % repository.name
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${common_javascripts(repository)}
</%def>

${render_tool_shed_repository_actions( repository=repository )}

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
                                <a class="view-info" href="${h.url_for( controller='repository_review', action='view_or_manage_repository', id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">${changeset_revision_label}</a>
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
