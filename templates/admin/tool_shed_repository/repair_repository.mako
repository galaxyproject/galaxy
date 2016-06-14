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
        The following repositories will be inspected and repaired in the order listed to ensure each repository and all of its tool dependencies are
        correctly installed.
    </p>
    <p>
        Existing system processes associated with repositories or tool dependencies that are currently being installed will not be automatically
        terminated.  If possible, make sure no installation processes are still running for repositories whose status is or includes <b>cloning</b>,
        <b>setting tool versions</b>, <b>installing repository dependencies</b>, or <b>installing tool dependencies</b> before clicking the <b>Repair</b>
        button.
    </p>
    <p>
        All repositories that do not display an <b>Installed</b> status will be removed from disk and reinstalled.
    </p>
    <p>
        Click <b>Repair</b> to inspect and repair these repositories.
    </p>
</div>

<div class="toolForm">
    <div class="toolFormTitle">Repair tool shed repository <b>${repository.name|h}</b></div>
        <form name="repair_repository" id="repair_repository" action="${h.url_for( controller='admin_toolshed', action='repair_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <input type="hidden" name="repair_dict" value="${encoded_repair_dict|h}"/>
            <%
                from tool_shed.util.repository_util import get_tool_shed_repository_status_label
                ordered_repo_info_dicts = repair_dict.get( 'ordered_repo_info_dicts', [] ) 
            %>
            <table class="grid">
                <tr>
                    <th bgcolor="#D8D8D8">Name</th>
                    <th bgcolor="#D8D8D8">Owner</th>
                    <th bgcolor="#D8D8D8">Changeset revision</th>
                    <th bgcolor="#D8D8D8">Status</th>
                </tr>
                %for repo_info_dict in ordered_repo_info_dicts:
                    <%
                        for name, repo_info_tuple in repo_info_dict.items():
                            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = repo_info_tuple
                            break
                        status_label = get_tool_shed_repository_status_label( trans.app,
                                                                              tool_shed_repository=None,
                                                                              name=name,
                                                                              owner=repository_owner,
                                                                              changeset_revision=changeset_revision,
                                                                              repository_clone_url=repository_clone_url )
                    %>
                    <tr>
                        <td>${name | h}</td>
                        <td>${repository_owner | h}</td>
                        <td>${changeset_revision | h}</td>
                        <td>${status_label}</td>
                    </tr>
                %endfor
            </table>
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="submit" name="repair_repository_button" value="Repair"/>
            </div>
        </form>
    </div>
</div>
