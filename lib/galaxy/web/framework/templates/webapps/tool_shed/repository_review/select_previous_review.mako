<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

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

${render_tool_shed_repository_actions( repository=repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="warningmessage">
    You have elected to create a new review for revision <b>${changeset_revision_label}</b>of this repository.  Since previous revisions have been reviewed, 
    you can select a previous review to copy to your new review, or click the <b>Create a review without copying</b> button.
</div>
                        
<div class="toolForm">
    <div class="toolFormTitle">Select previous revision review of repository '${repository.name | h}'</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Revision for new review:</label>
            <a class="action-button" href="${h.url_for( controller='repository_review', action='view_or_manage_repository', id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">${changeset_revision_label}</a>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <table class="grid">
                <tr>
                </tr>
                    <td bgcolor="#D8D8D8" colspan="4"><b>Previous revision reviews of repository '${repository.name | h}' that can be copied to your new review</b></td>
                <tr>
                    <th>Reviewer</th>
                    <th>Revision reviewed</th>
                    <th>Repository rating</th>
                    <th>Approved</th>
                </tr>
                %for previous_changeset_revision, previous_changeset_revision_dict in previous_reviews_dict.items():
                    <%
                        previous_changeset_revision_label = previous_changeset_revision_dict[ 'changeset_revision_label' ]
                        previous_reviews = previous_changeset_revision_dict[ 'reviews' ]
                    %>
                    %for review in previous_reviews:
                        <%
                            encoded_review_id = trans.security.encode_id( review.id )
                            if review.approved not in [ None, 'None', 'none' ]:
                                approved_str = review.approved
                            else:
                                approved_str = ''
                            repository_rating_name = '%srepository_rating' % encoded_review_id
                        %>
                        <tr>
                            <td>
                                <div style="float:left;" class="menubutton split popup" id="${encoded_review_id}-popup">
                                    <a class="view-info" href="${h.url_for( controller='repository_review', action='browse_review', id=encoded_review_id )}">${review.user.username | h}</a>
                                </div>
                                <div popupmenu="${encoded_review_id}-popup">
                                    <a class="action-button" href="${h.url_for( controller='repository_review', action='create_review', id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision, previous_review_id=encoded_review_id )}">Copy this review</a>
                                </div>
                            </td>
                            <td>${previous_changeset_revision_label}</td>
                            <td>${render_star_rating( repository_rating_name, review.rating, disabled=True )}</td>
                            <td>${approved_str | h}</td>
                        </tr>
                    %endfor
                %endfor
            </table>
        </div>
        <div style="clear: both"></div>
        <a class="action-button" href="${h.url_for( controller='repository_review', action='create_review', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, create_without_copying=True )}">Create a review without copying</a>
    </div>
</div>
