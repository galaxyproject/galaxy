<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

${render_galaxy_repository_actions( repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="warningmessage">
    <p>
        Purging the repository named <b>${repository.name}</b> will result in deletion of all records for the
        following associated items from the database.  Click the <b>Purge</b> button to purge this repository
        and its associated items.
    </p>
</div>

<div class="toolForm">
    <div class="toolFormTitle">Purge tool shed repository <b>${repository.name}</b></div>
        <form name="purge_repository" id="purge_repository" action="${h.url_for( controller='admin_toolshed', action='purge_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <%
                tool_versions = 0
                tool_dependencies = 0
                required_repositories = 0
                orphan_repository_repository_dependency_association_records = 0
                orphan_repository_dependency_records = 0
                # Count this repository's tool version lineage chain links that will be purged.
                for tool_version in repository.tool_versions:
                    for tool_version_association in tool_version.parent_tool_association:
                        tool_versions += 1
                    for tool_version_association in tool_version.child_tool_association:
                        tool_versions += 1
                    tool_versions += 1
                # Count this repository's associated tool dependencies that will be purged.
                for tool_dependency in repository.tool_dependencies:
                    tool_dependencies += 1
                # Count this repository's associated required repositories that will be purged.
                for rrda in repository.required_repositories:
                    required_repositories += 1
                # Count any "orphan" repository_dependency records associated with the repository but not with any
                # repository_repository_dependency_association records that will be purged.
                for orphan_repository_dependency in \
                    trans.sa_session.query( trans.app.install_model.RepositoryDependency ) \
                                    .filter( trans.app.install_model.RepositoryDependency.table.c.tool_shed_repository_id == repository.id ):
                    for orphan_rrda in \
                        trans.sa_session.query( trans.app.install_model.RepositoryRepositoryDependencyAssociation ) \
                                        .filter( trans.app.install_model.RepositoryRepositoryDependencyAssociation.table.c.repository_dependency_id == orphan_repository_dependency.id ):
                        orphan_repository_repository_dependency_association_records += 1
                    orphan_repository_dependency_records += 1
            %>
            <table class="grid">
                <tr><td>Tool version records</td><td>${tool_versions}</td><tr>
                <tr><td>Tool dependency records</td><td>${tool_dependencies}</td><tr>
                <tr><td>Repository dependency records</td><td>${required_repositories}</td><tr>
                <tr><td>Orphan repository_repository_dependency_association records</td><td>${orphan_repository_repository_dependency_association_records}</td><tr>
                <tr><td>Orphan repository_dependency records</td><td>${orphan_repository_dependency_records}</td><tr>
            </table>
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="submit" name="purge_repository_button" value="Purge"/>
            </div>
        </form>
    </div>
</div>
