<%inherit file="/base.mako"/>

<%def name="render_tool_shed_repository_actions( repository, metadata=None, changeset_revision=None )">
    <%
        from tool_shed.util.metadata_util import is_malicious

        if repository.metadata_revisions:
            has_metadata = True
        else:
            has_metadata = False

        is_admin = trans.user_is_admin

        if is_admin or trans.app.security_agent.user_can_administer_repository( trans.user, repository ):
            can_administer = True
        else:
            can_administer = False

        if repository.deprecated:
            is_deprecated = True
        else:
            is_deprecated = False

        if repository.is_new():
            is_new = True
        else:
            is_new = False

        if is_malicious( trans.app, trans.security.encode_id( repository.id ), repository.tip() ):
            changeset_is_malicious = True
        else:
            changeset_is_malicious = False

        can_browse_contents = not is_new

        if not is_new and trans.user and ( is_admin or repository.user == trans.user ) and not is_deprecated:
            can_deprecate = True
        else:
            can_deprecate = False

        if not is_deprecated and trans.app.security_agent.can_push( trans.app, trans.user, repository ):
            can_push = True
        else:
            can_push = False

        if not is_deprecated and not is_new and not changeset_is_malicious:
            can_download = True
        else:
            can_download = False

        if ( can_administer or can_push ) and not repository.deleted and not repository.deprecated and not is_new:
            can_reset_all_metadata = True
        else:
            can_reset_all_metadata = False

        if not is_new and not is_deprecated and trans.user and repository.user != trans.user:
            can_rate = True
        else:
            can_rate = False

        if not is_new and not is_deprecated:
            can_set_metadata = True
        else:
            can_set_metadata = False

        if changeset_revision is not None:
            if changeset_revision == repository.tip():
                changeset_revision_is_repository_tip = True
            else:
                changeset_revision_is_repository_tip = False
        else:
            changeset_revision_is_repository_tip = False

        if trans.user and ( is_admin or repository.user == trans.user ) and is_deprecated:
            can_undeprecate = True
        else:
            can_undeprecate = False

        can_view_change_log = not is_new

        if can_push:
            browse_label = 'Browse or delete repository tip files'
        else:
            browse_label = 'Browse repository tip files'
    %>

    <br/><br/>
    <ul class="manage-table-actions">
        %if is_new:
            %if can_undeprecate:
                <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='deprecate', id=trans.security.encode_id( repository.id ), mark_deprecated=False )}">Mark repository as not deprecated</a>
            %endif
        %else:
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                %if can_administer:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip() )}">Manage repository</a>
                %else:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip() )}">View repository</a>
                %endif
                %if can_view_change_log:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">View change log</a>
                %endif
                %if can_browse_contents:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">${browse_label | h}</a>
                %endif
                %if can_rate:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
                %endif
                %if can_reset_all_metadata:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='reset_all_metadata', id=trans.security.encode_id( repository.id ) )}">Reset all repository metadata</a>
                %endif
                %if can_deprecate:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='deprecate', id=trans.security.encode_id( repository.id ), mark_deprecated=True )}" confirm="Click Ok to deprecate this repository.">Mark repository as deprecated</a>
                %endif
                %if can_undeprecate:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='deprecate', id=trans.security.encode_id( repository.id ), mark_deprecated=False )}">Mark repository as not deprecated</a>
                %endif
                %if can_administer:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='manage_repository_admins', id=trans.security.encode_id( repository.id ) )}">Manage repository administrators</a>
                %endif
                %if can_download:
                    %if metadata is not None and changeset_revision is not None:
                        <a class="action-button" href="${h.url_for( controller='repository', action='export', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Export this revision</a>
                    %endif
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip(), file_type='gz' )}">Download as a .tar.gz file</a>
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip(), file_type='bz2' )}">Download as a .tar.bz2 file</a>
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip(), file_type='zip' )}">Download as a zip file</a>
                %endif
            </div>
        %endif
    </ul>
</%def>

<%def name="render_galaxy_repository_actions( repository=None )">
    <br/><br/>
    <ul class="manage-table-actions">
        %if repository:
            <li><a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='preview_tools_in_changeset', repository_id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Browse repository</a></li>
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Tool Shed Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='browse_valid_categories' )}">Browse valid repositories</a>
                <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='find_tools' )}">Search for valid tools</a>
            </div>
        %else:
            <li><a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='browse_valid_categories' )}">Browse valid repositories</a></li>
            <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='find_tools' )}">Search for valid tools</a>
        %endif
    </ul>
</%def>
