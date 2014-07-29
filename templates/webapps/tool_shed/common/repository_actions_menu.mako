<%inherit file="/base.mako"/>

<%def name="render_tool_shed_repository_actions( repository, metadata=None, changeset_revision=None )">
    <%
        from tool_shed.util.review_util import can_browse_repository_reviews, changeset_revision_reviewed_by_user, get_review_by_repository_id_changeset_revision_user_id
        from tool_shed.util.metadata_util import is_malicious

        if repository.metadata_revisions:
            has_metadata = True
        else:
            has_metadata = False

        is_admin = trans.user_is_admin()

        if is_admin or trans.app.security_agent.user_can_administer_repository( trans.user, repository ):
            can_administer = True
        else:
            can_administer = False

        if repository.deprecated:
            is_deprecated = True
        else:
            is_deprecated = False

        if repository.is_new( trans.app ):
            is_new = True
        else:
            is_new = False

        if is_malicious( trans.app, trans.security.encode_id( repository.id ), repository.tip( trans.app ) ):
            changeset_is_malicious = True
        else:
            changeset_is_malicious = False

        can_browse_contents = not is_new

        if can_browse_repository_reviews( trans.app, trans.user, repository ):
            can_browse_reviews = True
        else:
            can_browse_reviews = False

        if trans.user and trans.user != repository.user:
            can_contact_owner = True
        else:
            can_contact_owner = False
        
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

        if can_push and not is_deprecated:
            can_upload = True
        else:
            can_upload = False

        if not is_new and not is_deprecated and trans.user and repository.user != trans.user:
            can_rate = True
        else:
            can_rate = False
        
        if metadata is not None and changeset_revision is not None:
            if has_metadata and not is_deprecated and trans.app.security_agent.user_can_review_repositories( trans.user ):
                can_review_repository = True
            else:
                can_review_repository = False
            if changeset_revision_reviewed_by_user( trans.user, repository, changeset_revision ):
                reviewed_by_user = True
            else:
                reviewed_by_user = False
        else:
            can_review_repository = False
            reviewed_by_user = False

        if reviewed_by_user:
            review = get_review_by_repository_id_changeset_revision_user_id( app=trans.app,
                                                                             repository_id=trans.security.encode_id( repository.id ),
                                                                             changeset_revision=changeset_revision,
                                                                             user_id=trans.security.encode_id( trans.user.id ) )
            review_id = trans.security.encode_id( review.id )
        else:
            review_id = None

        if not is_new and not is_deprecated:
            can_set_metadata = True
        else:
            can_set_metadata = False

        if changeset_revision is not None:
            if changeset_revision == repository.tip( trans.app ):
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
            %if can_upload:
                <a class="action-button" target="galaxy_main" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ) )}">Upload files to repository</a>
            %endif
            %if can_undeprecate:
                <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='deprecate', id=trans.security.encode_id( repository.id ), mark_deprecated=False )}">Mark repository as not deprecated</a>
            %endif
        %else:
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                %if can_review_repository:
                    %if reviewed_by_user:
                        <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository_review', action='edit_review', id=review_id )}">Manage my review of this revision</a>
                    %else:
                        <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository_review', action='create_review', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Add a review to this revision</a>
                    %endif
                %endif
                %if can_browse_reviews:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository_review', action='manage_repository_reviews', id=trans.app.security.encode_id( repository.id ) )}">Browse reviews of this repository</a>
                %endif
                %if can_upload:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ) )}">Upload files to repository</a>
                %endif
                %if can_administer:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip( trans.app ) )}">Manage repository</a>
                %else:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip( trans.app ) )}">View repository</a>
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
                %if can_contact_owner:
                    <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ) )}">Contact repository owner</a>
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
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip( trans.app ), file_type='gz' )}">Download as a .tar.gz file</a>
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip( trans.app ), file_type='bz2' )}">Download as a .tar.bz2 file</a>
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip( trans.app ), file_type='zip' )}">Download as a zip file</a>
                %endif
            </div>
        %endif
    </ul>
</%def>

<%def name="render_galaxy_repository_actions( repository=None )">
    <br/><br/>
    <ul class="manage-table-actions">
        %if repository:
            <li><a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='install_repositories_by_revision', repository_ids=trans.security.encode_id( repository.id ), changeset_revisions=changeset_revision )}">Install to Galaxy</a></li>
            <li><a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='preview_tools_in_changeset', repository_id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Browse repository</a></li>
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Tool Shed Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='browse_valid_categories' )}">Browse valid repositories</a>
                <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='find_tools' )}">Search for valid tools</a>
                <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='find_workflows' )}">Search for workflows</a>
            </div>
        %else:
            <li><a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='browse_valid_categories' )}">Browse valid repositories</a></li>
            <a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='find_tools' )}">Search for valid tools</a>
            <li><a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='find_workflows' )}">Search for workflows</a></li>
        %endif
    </ul>
</%def>
