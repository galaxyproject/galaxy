<%inherit file="/base.mako"/>

<%def name="render_tool_shed_repository_actions( repository, repo=None, metadata=None, changeset_revision=None )">
    <%
        from tool_shed.util.review_util import can_browse_repository_reviews, changeset_revision_reviewed_by_user, get_review_by_repository_id_changeset_revision_user_id
        from tool_shed.util.shed_util_common import changeset_is_malicious

        has_metadata = repository.metadata_revisions
        has_readme = metadata and 'readme' in metadata
        is_admin = trans.user_is_admin()
        is_deprecated = repository.deprecated
        is_new = repository.is_new( trans.app )
        is_malicious = changeset_is_malicious( trans, trans.security.encode_id( repository.id ), repository.tip( trans.app ) )

        can_browse_contents = not is_new
        can_browse_reviews = can_browse_repository_reviews( trans, repository )
        can_contact_owner = trans.user and trans.user != repository.user
        can_deprecate = not is_new and trans.user and ( is_admin or repository.user == trans.user ) and not is_deprecated
        can_push = not is_deprecated and trans.app.security_agent.can_push( trans.app, trans.user, repository )
        can_download = not is_deprecated and not is_new and ( not is_malicious or can_push )
        if not is_deprecated:
            if repo and len( repo ) > 0:
                can_reset_all_metadata = True
            else:
                can_reset_all_metadata = False
        else:
            can_reset_all_metadata = False
        can_upload = can_push and not is_deprecated
        can_rate = not is_new and not is_deprecated and trans.user and repository.user != trans.user
        if changeset_revision:
            can_review_repository = has_metadata and not is_deprecated and trans.app.security_agent.user_can_review_repositories( trans.user )
            reviewed_by_user = changeset_revision_reviewed_by_user( trans, trans.user, repository, changeset_revision )
        else:
            can_review_repository = False
            reviewed_by_user = False

        # Determine if the current changeset revision has been reviewed by the current user.
        if reviewed_by_user:
            review = get_review_by_repository_id_changeset_revision_user_id( trans=trans,
                                                                             repository_id=trans.security.encode_id( repository.id ),
                                                                             changeset_revision=changeset_revision,
                                                                             user_id=trans.security.encode_id( trans.user.id ) )
            review_id = trans.security.encode_id( review.id )
        else:
            review_id = None

        can_set_metadata = not is_new and not is_deprecated
        if changeset_revision:
            if changeset_revision == repository.tip( trans.app ):
                changeset_revision_is_repository_tip = True
            else:
                changeset_revision_is_repository_tip = False
        else:
            changeset_revision_is_repository_tip = False
        can_set_malicious = metadata and can_set_metadata and is_admin and changeset_revision_is_repository_tip
        can_undeprecate = trans.user and ( is_admin or repository.user == trans.user ) and is_deprecated
        can_manage = is_admin or repository.user == trans.user
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
                <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ) )}">Upload files to repository</a>
            %endif
        %else:
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                %if can_review_repository:
                    %if reviewed_by_user:
                        <a class="action-button" href="${h.url_for( controller='repository_review', action='edit_review', id=review_id )}">Manage my review of this revision</a>
                    %else:
                        <a class="action-button" href="${h.url_for( controller='repository_review', action='create_review', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Add a review to this revision</a>
                    %endif
                %endif
                %if can_browse_reviews:
                    <a class="action-button" href="${h.url_for( controller='repository_review', action='manage_repository_reviews', id=trans.app.security.encode_id( repository.id ) )}">Browse reviews of this repository</a>
                %endif
                %if can_upload:
                    <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ) )}">Upload files to repository</a>
                %endif
                %if can_manage:
                    <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip( trans.app ) )}">Manage repository</a>
                %else:
                    <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip( trans.app ) )}">View repository</a>
                %endif
                %if can_view_change_log:
                    <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">View change log</a>
                %endif
                %if can_browse_contents:
                    <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">${browse_label | h}</a>
                %endif
                %if can_rate:
                    <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
                %endif
                %if can_contact_owner:
                    <a class="action-button" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ) )}">Contact repository owner</a>
                %endif
                %if can_reset_all_metadata:
                    <a class="action-button" href="${h.url_for( controller='repository', action='reset_all_metadata', id=trans.security.encode_id( repository.id ) )}">Reset all repository metadata</a>
                %endif
                %if can_deprecate:
                    <a class="action-button" href="${h.url_for( controller='repository', action='deprecate', id=trans.security.encode_id( repository.id ), mark_deprecated=True )}" confirm="Click Ok to deprecate this repository.">Mark repository as deprecated</a>
                %endif
                %if can_undeprecate:
                    <a class="action-button" href="${h.url_for( controller='repository', action='deprecate', id=trans.security.encode_id( repository.id ), mark_deprecated=False )}">Mark repository as not deprecated</a>
                %endif
                %if can_download:
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
            <li><a class="action-button" href="${h.url_for( controller='repository', action='install_repositories_by_revision', repository_ids=trans.security.encode_id( repository.id ), changeset_revisions=changeset_revision )}">Install to Galaxy</a></li>
            <li><a class="action-button" href="${h.url_for( controller='repository', action='preview_tools_in_changeset', repository_id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Browse repository</a></li>
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Tool Shed Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                <a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_categories' )}">Browse valid repositories</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='find_tools' )}">Search for valid tools</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='find_workflows' )}">Search for workflows</a>
            </div>
        %else:
            <li><a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_categories' )}">Browse valid repositories</a></li>
            <a class="action-button" href="${h.url_for( controller='repository', action='find_tools' )}">Search for valid tools</a>
            <li><a class="action-button" href="${h.url_for( controller='repository', action='find_workflows' )}">Search for workflows</a></li>
        %endif
    </ul>
</%def>
