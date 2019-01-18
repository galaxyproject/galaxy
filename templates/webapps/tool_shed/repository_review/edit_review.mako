<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

<%
    from galaxy.web.form_builder import CheckboxField
    from tool_shed.grids.util import build_approved_select_field
    from tool_shed.util.container_util import STRSEP
%>

<%def name="stylesheets()">
    ${h.css('base')}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

${render_tool_shed_repository_actions( repository=repository, changeset_revision=review.changeset_revision )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">My review of repository '${repository.name | h}'</div>
    <div class="toolFormBody">
        <form name="edit_review" action="${h.url_for( controller='repository_review', action='edit_review', id=trans.security.encode_id( review.id ) )}" method="post" >
            <div class="form-row">
                <label>Repository revision:</label>
                <a class="action-button" href="${h.url_for( controller='repository_review', action='view_or_manage_repository', id=trans.security.encode_id( repository.id ), changeset_revision=review.changeset_revision )}">${changeset_revision_label}</a>
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
                <label>Approve this repository revision?</label>
                ${render_select(revision_approved_select_field)}
                <div class="toolParamHelp" style="clear: both;">
                    Individual components below may be approved without approving the repository revision.
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="revision_approved_button" value="Save"/>
                <div class="toolParamHelp" style="clear: both;">
                    All changes made on this page will be saved when any <b>Save</b> button is clicked.
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <table class="grid">
                    %for component_name, component_review_dict in components_dict.items():
                        <%
                            component = component_review_dict[ 'component' ]
                            encoded_component_id = trans.security.encode_id( component.id )
                            
                            component_review = component_review_dict[ 'component_review' ]
                            if component_review:
                                comment = component_review.comment or ''
                                rating = component_review.rating
                                approved_select_field_selected_value = component_review.approved
                                private = component_review.private
                            else:
                                comment = ''
                                rating = 0
                                approved_select_field_selected_value = None
                                private = False
                            
                            # Initialize Approved select field.
                            approved_select_field_name = '%s%sapproved' % ( component_name, STRSEP )
                            approved_select_field = build_approved_select_field( trans, name=approved_select_field_name, selected_value=approved_select_field_selected_value, for_component=True )
                            
                            # Initialize Private check box.
                            private_check_box_name = '%s%sprivate' % ( component_name, STRSEP )
                            private_check_box = CheckboxField( name=private_check_box_name, value=private )
                            
                            # Initialize star rating.
                            rating_name = '%s%srating' % ( component_name, STRSEP )
                            
                            # Initialize comment text area.
                            comment_name = '%s%scomment' % ( component_name, STRSEP )
                            
                            # Initialize the component id form field name.
                            component_id_name = '%s%scomponent_id' % ( component_name, STRSEP )
                            
                            # Initialize the Save button.
                            review_button_name = '%s%sreview_button' % ( component_name, STRSEP )
                        %>
                        <tr>
                            <td bgcolor="#D8D8D8"><b>${component.name | h}</b></td>
                            <td bgcolor="#D8D8D8">${component.description | h}</td>
                        </tr>
                        <tr>
                            <td colspan="2">
                                <table class="grid">
                                    <tr>
                                        <td>
                                            <label>Mark private:</label>
                                            ${render_checkbox(private_check_box)}
                                            <div class="toolParamHelp" style="clear: both;">
                                                A private review can be accessed only by the owner of the repository and authorized repository reviewers.
                                            </div>
                                            <div style="clear: both"></div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <label>Comments:</label>
                                            %if component_review:
                                                <pre><textarea name="${comment_name}" rows="3" cols="80">${comment | h}</textarea></pre>
                                            %else:
                                                <textarea name="${comment_name}" rows="3" cols="80"></textarea>
                                            %endif
                                            <div style="clear: both"></div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <label>Approved:</label>
                                            ${render_select(approved_select_field)}
                                            <div style="clear: both"></div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <label>Rating:</label>
                                            ${render_star_rating( rating_name, rating )}
                                            <div style="clear: both"></div>
                                            <div class="toolParamHelp" style="clear: both;">
                                                Rate this component only - the average of all component ratings defines the value of the repository rating.
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <input type="hidden" name="${component_id_name}" value="${encoded_component_id}"/>
                                            <input type="submit" name="${review_button_name}" value="Save"/>
                                            <div style="clear: both"></div>
                                            <div class="toolParamHelp" style="clear: both;">
                                                All changes made on this page will be saved when any <b>Save</b> button is clicked.
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    %endfor
                </table>
            </div>
        </form>
    </div>
</div>
