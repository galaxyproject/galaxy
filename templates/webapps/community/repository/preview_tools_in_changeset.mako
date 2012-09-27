<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    is_new = repository.is_new
    can_contact_owner = trans.user and trans.user != repository.user
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_rate = not is_new and trans.user and repository.user != trans.user
    can_upload = can_push
    can_download = not is_new and ( not is_malicious or can_push )
    can_browse_contents = not is_new
    can_view_change_log = not is_new
    if can_push:
        browse_label = 'Browse or delete repository tip files'
    else:
        browse_label = 'Browse repository tip files'
    has_readme = metadata and 'readme' in metadata
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
    <li><a class="action-button" href="${h.url_for( controller='repository', action='install_repositories_by_revision', repository_ids=trans.security.encode_id( repository.id ), webapp=webapp, changeset_revisions=changeset_revision )}">Install to local Galaxy</a></li>
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Tool Shed Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        %if has_readme:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_readme', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, webapp=webapp )}">View README</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_categories', webapp=webapp )}">Browse valid repositories</a>
        <a class="action-button" href="${h.url_for( controller='repository', action='find_tools', webapp=webapp )}">Search for valid tools</a>
        <a class="action-button" href="${h.url_for( controller='repository', action='find_workflows', webapp=webapp )}">Search for workflows</a>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Repository ${repository.name}</div>
    <div class="toolFormBody">
        %if len( changeset_revision_select_field.options ) > 1:
            <form name="change_revision" id="change_revision" action="${h.url_for( controller='repository', action='preview_tools_in_changeset', repository_id=trans.security.encode_id( repository.id ) )}" method="post" >
                <div class="form-row">
                    <%
                        if changeset_revision == repository.tip:
                            tip_str = 'repository tip'
                        else:
                            tip_str = ''
                    %>
                    ${changeset_revision_select_field.get_html()} <i>${tip_str}</i>
                    <div class="toolParamHelp" style="clear: both;">
                        Select a revision to inspect and download versions of tools from this repository.
                    </div>
                </div>
            </form>
        %else:
            <div class="form-row">
                <label>Revision:</label>
                ${revision_label}
            </div>
        %endif
    </div>
</div>
<p/>
${render_repository_items( repository_metadata_id, metadata, webapp=webapp )}
