<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

<%
    from galaxy.web.framework.helpers import time_ago
    is_new = repository.is_new()
    can_push = trans.app.security_agent.can_push( trans.app, trans.user, repository )
    can_download = not is_new and ( not is_malicious or can_push )
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
    ${parent.stylesheets()}
    ${h.css('base')}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

%if message:
    ${render_msg( message, status )}
%endif

${render_tool_shed_repository_actions( repository, metadata=None, changeset_revision=None )}

%if repository.user != trans.user:
    <div class="toolForm">
        <div class="toolFormTitle">${repository.name | h}</div>
        %if can_download:
            <div class="form-row">
                <label>Clone this repository:</label>
                ${render_clone_str( repository )}
            </div>
        %endif
        <div class="toolFormBody">
            <div class="form-row">
                <label>Type:</label>
                ${repository.type | h}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                ${repository.description | h}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Revision:</label>
                ${revision_label}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Owner:</label>
                ${repository.user.username | h}
                <div style="clear: both"></div>
            </div>
        </div>
    </div>
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Repository '${repository.name | h}'</div>
        <div class="toolFormBody">
            <form id="rate_repository" name="rate_repository" action="${h.url_for( controller='repository', action='rate_repository', id=trans.security.encode_id( repository.id ) )}" method="post">
                <div class="form-row">
                    <label>Times Rated:</label>
                    ${num_ratings | h}
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
                    <input type="submit" name="rate_button" id="rate_button" value="Submit" />
                </div>
            </form>
        </div>
    </div>
    <p/>
%endif
