<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />

<%def name="javascripts()">
   ${parent.javascripts()}
   ${repository_installation_status_updater()}
   ${repository_installation_updater()}
   ${self.repository_installation_javascripts()}
</%def>

<%def name="repository_installation_javascripts()">
    <script type="text/javascript">
        %if context.get("initiate_repository_installation_ids"):
            $(document).ready(function( ){
                initiate_repository_installation( "${initiate_repository_installation_ids}", "${encoded_kwd}", "${reinstalling}" );
            });
        %endif
        var initiate_repository_installation = function ( iri_ids, encoded_kwd, reinstalling ) {
            // Make ajax call
            $.ajax( {
                type: "POST",
                url: "${h.url_for( controller='admin_toolshed', action='install_repositories' )}",
                dataType: "html",
                data: { tool_shed_repository_ids: iri_ids, encoded_kwd: encoded_kwd, reinstalling: reinstalling },
                success : function ( data ) {
                    console.log( "Initializing repository installation succeeded" );
                }
            });
        };
    </script>
</%def>

%if context.get("message"):
    ${render_msg( message, status )}
%endif

%if tool_shed_repositories:
    <div class="card">
        <div class="card-header">Monitor installing tool shed repositories</div>
        <div class="card-body overflow-auto">
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
%else:
    ${render_msg("There is no repository being installed.", "info")}
%endif
