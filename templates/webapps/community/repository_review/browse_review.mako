<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />

<%
    from galaxy.web.form_builder import CheckboxField
    from galaxy.webapps.community.controllers.common import STRSEP
    can_manage_repository = is_admin or repository.user == trans.user
%>

<%def name="stylesheets()">
    ${h.css('base','panel_layout','jquery.rating')}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/jquery/jquery.rating" )}
</%def>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="review-${review.id}-popup" class="menubutton">Review Actions</a></li>
    <div popupmenu="review-${review.id}-popup">
        %if can_manage_repository:
            <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=review.changeset_revision )}">Manage repository</a>
        %else:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=review.changeset_revision )}">View repository</a>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Review of repository '${repository.name}'</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Reviewer:</label>
            ${review.user.username}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Repository revision:</label>
            <a class="action-button" href="${h.url_for( controller='repository_review', action='view_or_manage_repository', id=trans.security.encode_id( repository.id ), changeset_revision=review.changeset_revision )}">${changeset_revision_label}</a>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Repository owner:</label>
            ${repository.user.username}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Repository synopsis:</label>
            ${repository.description}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            %if review.component_reviews:
                <table class="grid">
                    %for component_review in review.component_reviews:
                        <%
                            component = component_review.component
                            
                            # Initialize Private check box.
                            private_check_box_name = '%s%sprivate' % ( component.name, STRSEP )
                            private_check_box = CheckboxField( name=private_check_box_name, checked=component_review.private )
                            
                            # Initialize star rating.
                            rating_name = '%s%srating' % ( component.name, STRSEP )
                            
                            review_comment = component_review.comment.replace( '\n', '<br/>' )
                        %>
                        <tr>
                            <td bgcolor="#D8D8D8"><b>${component.name}</b></td>
                            <td bgcolor="#D8D8D8">${component.description}</td>
                        </tr>
                        <tr>
                            <td colspan="2">
                                <table class="grid">
                                    <tr>
                                        <td>
                                            <label>Private:</label>
                                            ${private_check_box.get_html( disabled=True )}
                                            <div class="toolParamHelp" style="clear: both;">
                                                A private review can be accessed only by the owner of the repository and the IUC.
                                            </div>
                                            <div style="clear: both"></div>
                                        </td>
                                    </tr>
                                    %if component_review.comment:
                                        <tr>
                                            <td>
                                                <div overflow-wrap:normal;overflow:hidden;word-break:keep-all;word-wrap:break-word;line-break:strict;>
                                                    ${review_comment}
                                                </div>
                                            </td>
                                        </tr>
                                    %endif
                                    <tr>
                                        <td>
                                            <label>Approved:</label>
                                            ${component_review.approved}
                                            <div style="clear: both"></div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <label>Rating:</label>
                                            ${render_star_rating( rating_name, component_review.rating, disabled=True )}
                                            <div style="clear: both"></div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    %endfor
                </table>
            %else:
                This review has not yet been started.
            %endif
        </div>
    </div>
</div>
