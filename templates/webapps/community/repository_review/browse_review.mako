<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />

<%
    from galaxy.web.form_builder import CheckboxField
    from galaxy.webapps.community.util.container_util import STRSEP
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
    <div class="toolFormTitle">Review of repository '${repository.name | h}'</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Reviewer:</label>
            ${review.user.username}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Repository revision:</label>
            <a class="action-button" href="${h.url_for( controller='repository_review', action='view_or_manage_repository', id=trans.security.encode_id( repository.id ), changeset_revision=review.changeset_revision )}">${changeset_revision_label | h}</a>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Repository owner:</label>
            ${repository.user.username | h}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Repository synopsis:</label>
            ${repository.description | h}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            %if review.component_reviews:
                <table class="grid">
                    %for component_review in review.component_reviews:
                        <%
                            can_browse = trans.app.security_agent.user_can_browse_component_review( component_review, trans.user )
                            component = component_review.component
                            if can_browse:
                                # Initialize Private check box.
                                private_check_box_name = '%s%sprivate' % ( component.name, STRSEP )
                                private_check_box = CheckboxField( name=private_check_box_name, checked=component_review.private )
                                
                                # Initialize star rating.
                                rating_name = '%s%srating' % ( component.name, STRSEP )
                        %>
                        <tr>
                            <td bgcolor="#D8D8D8"><b>${component.name | h}</b></td>
                            <td bgcolor="#D8D8D8">${component.description | h}</td>
                        </tr>
                        <tr>
                            <td colspan="2">
                            %if can_browse:
                                    <table class="grid">
                                        <tr>
                                            <td>
                                                <label>Private:</label>
                                                ${private_check_box.get_html( disabled=True )}
                                                <div class="toolParamHelp" style="clear: both;">
                                                    A private review can be accessed only by the owner of the repository and authorized repository reviewers.
                                                </div>
                                                <div style="clear: both"></div>
                                            </td>
                                        </tr>
                                        %if component_review.comment:
                                            <tr>
                                                <td>
                                                    <div overflow-wrap:normal;overflow:hidden;word-break:keep-all;word-wrap:break-word;line-break:strict;>
                                                        ${ escape_html_add_breaks( component_review.comment ) }
                                                    </div>
                                                </td>
                                            </tr>
                                        %endif
                                        <tr>
                                            <td>
                                                <label>Approved:</label>
                                                ${component_review.approved | h}
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
                                %else:
                                    You are not authorized to access the review of this component since it has been marked private.
                                %endif
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
