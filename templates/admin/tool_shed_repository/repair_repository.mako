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
    The following repositories will be inspected and repaired in the order listed to ensure each repository and all of it's tool dependencies are correctly
    installed.  Click <b>Repair</b> to inspect and repair these repositories. 
</div>

<div class="toolForm">
    <div class="toolFormTitle">Repair tool shed repository '${repository.name}'</div>
        <br/><br/>
        <form name="repair_repository" id="repair_repository" action="${h.url_for( controller='admin_toolshed', action='repair_repository', id=trans.security.encode_id( repository.id ), repair_dict=encoded_repair_dict )}" method="post" >
            <% ordered_repo_info_dicts = repair_dict.get( 'ordered_repo_info_dicts', [] ) %>
            <table class="grid">
                <tr><th  bgcolor="#D8D8D8">Name</th><th  bgcolor="#D8D8D8">Owner</th><th  bgcolor="#D8D8D8">Changeset revision</th></tr>
                %for repo_info_dict in ordered_repo_info_dicts:
                    <%
                        for name, repo_info_tuple in repo_info_dict.items():
                            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = repo_info_tuple
                            break
                    %>
                    <tr>
                        <td>${name | h}</td>
                        <td>${repository_owner | h}</td>
                        <td>${changeset_revision | h}</td>
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
