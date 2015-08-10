<%inherit file="/base.mako"/>
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />

<%def name="javascripts()">
   ${parent.javascripts()}
   ${repository_installation_status_updater()}
   ${repository_installation_updater()}
   ${self.repository_installation_javascripts()}
</%def>

<%def name="repository_installation_javascripts()">
    <%
    import json
    repositories = []
    for repository in tool_shed_repositories:
        repository_dict = dict( name=repository.name,
                                owner=repository.owner,
                                revision=repository.changeset_revision,
                                toolshed=repository.tool_shed,
                                id=trans.security.encode_id( repository.id ),
                                reinstalling=reinstalling )
        repositories.append( repository_dict )
    repositories = json.dumps( repositories, indent=2 )
    %><pre>${repositories}</pre>
    <script type="text/javascript">
        var repositories = ${repositories}
        $(document).ready(function( ){
            initiate_repository_installation( repositories, reinstalling );
        });
        var initiate_repository_installation = function ( repositories, reinstalling ) {
            // Make ajax call
            $.ajax( {
                type: "POST",
                url: galaxy_config.root + 'api/tool_shed_repositories/install',
                dataType: "html",
                data: { tool_shed_repository_ids: iri_ids, encoded_kwd: encoded_kwd, reinstalling: reinstalling },
                success : function ( data ) {
                    console.log( "Initializing repository installation succeeded" );
                },
            });
        };
    </script>
</%def>

%if tool_shed_repositories:
    <div class="toolForm">
        <div class="toolFormTitle">Monitor installing tool shed repositories</div>
        <div class="toolFormBody">
            <table class="grid">
                <tr>
                    <td>Name</td>
                    <td>Description</td>
                    <td>Owner</td>
                    <td>Revision</td>
                    <td>Status</td>
                </tr>
                %for tool_shed_repository in tool_shed_repositories:
                    <%
                        encoded_repository_id = trans.security.encode_id( tool_shed_repository.id )
                        ids_of_tool_dependencies_missing_or_being_installed = [ trans.security.encode_id( td.id ) for td in tool_shed_repository.tool_dependencies_missing_or_being_installed ]
                        link_to_manage_tool_dependencies = tool_shed_repository.status in [ trans.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES ]
                    %>
                    <tr>
                        <td>
                            %if link_to_manage_tool_dependencies:
                                <a class="view-info" href="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', tool_dependency_ids=ids_of_tool_dependencies_missing_or_being_installed )}">
                                    ${tool_shed_repository.name|h}
                                </a>
                            %else:
                                <a class="view-info" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=encoded_repository_id )}">
                                    ${tool_shed_repository.name|h}
                                </a>
                            %endif
                        </td>
                        <td>${tool_shed_repository.description}</td>
                        <td>${tool_shed_repository.owner}</td>
                        <td>${tool_shed_repository.changeset_revision}</td>
                        <td><div id="RepositoryStatus-${encoded_repository_id}">${tool_shed_repository.status|h}</div></td>
                    </tr>
                %endfor
            </table>
            <br clear="left"/>
        </div>
    </div>
%endif
