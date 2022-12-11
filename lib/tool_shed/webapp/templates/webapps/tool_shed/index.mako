<%inherit file="/webapps/tool_shed/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="stylesheets()">
    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}

</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

<%def name="init()">
    ${parent.init()}
    <%
        self.has_left_panel=True
        self.has_right_panel=False
        self.active_view="tools"
    %>
    %if trans.app.config.require_login and not trans.user:
        <script type="text/javascript">
            if ( window != top ) {
                top.location.href = location.href;
            }
        </script>
    %endif
</%def>

<%def name="left_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>${trans.app.shed_counter.unique_valid_tools | h} valid tools on ${util.unicodify( trans.app.shed_counter.generation_time ) | h}</div>
    </div>
    <div class="unified-panel-body">
        <div class="toolMenu">
            <div class="toolSectionList">
                %if user_id or repository_id:
                    ## The route in was a sharable url, and may have included a changeset_revision, although we don't check for it.
                    <div class="toolSectionPad"></div>
                    <div class="toolSectionTitle">
                        All Repositories
                    </div>
                    <div class="toolTitle">
                        <a href="${h.url_for( controller='repository', action='index' )}">Browse by category</a>
                    </div>
                %else:
                    %if repository_metadata:
                        <div class="toolSectionPad"></div>
                        <div class="toolSectionTitle">
                            Search
                        </div>
                        <div class="toolSectionBody">
                            <div class="toolTitle">
                                <a target="galaxy_main" href="${h.url_for( controller='repository', action='find_tools' )}">Search for valid tools</a>
                            </div>
                        </div>
                        <div class="toolSectionPad"></div>
                        <div class="toolSectionTitle">
                            Valid Galaxy Utilities
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_tools' )}">Tools</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_datatypes' )}">Custom datatypes</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_repository_dependencies' )}">Repository dependency definitions</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_tool_dependencies' )}">Tool dependency definitions</a>
                        </div>
                    %endif
                    <div class="toolSectionPad"></div>
                    <div class="toolSectionTitle">
                        All Repositories
                    </div>
                    <div class="toolTitle">
                        <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_categories' )}">Browse by category</a>
                    </div>
                    %if trans.user:
                        %if trans.user.active_repositories or can_administer_repositories:
                            <div class="toolSectionPad"></div>
                            <div class="toolSectionTitle">
                                Repositories I Can Change
                            </div>
                            <div class="toolTitle">
                                <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_repositories_i_own' )}">Repositories I own</a>
                            </div>
                            %if can_administer_repositories:
                                <div class="toolTitle">
                                    <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_repositories_i_can_administer' )}">Repositories I can administer</a>
                                </div>
                            %endif
                            %if has_deprecated_repositories:
                                <div class="toolTitle">
                                    <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_deprecated_repositories_i_own' )}">Deprecated repositories I own</a>
                                </div>
                            %endif
                            <div class="toolTitle">
                                <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_my_writable_repositories' )}">My writable repositories</a>
                            </div>
                            <div class="toolTitle">
                                <a target="galaxy_main" href="${h.url_for( controller='repository', action='reset_metadata_on_my_writable_repositories_in_tool_shed' )}">Reset metadata on my repositories</a>
                            </div>
                            <div class="toolTitle">
                                <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_my_writable_repositories_missing_tool_test_components' )}">Latest revision: missing tool tests</a>
                            </div>
                            <div class="toolTitle">
                                <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_my_writable_repositories_with_invalid_tools' )}">Latest revision: invalid tools</a>
                            </div>
                        %endif
                        <div class="toolSectionPad"></div>
                        <div class="toolSectionTitle">
                            Available Actions
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='repository', action='create_repository' )}">Create new repository</a>
                        </div>
                        %if trans.app.config.enable_galaxy_flavor_docker_image:
                            <div class="toolTitle">
                                <a target="galaxy_main" href="${h.url_for( controller='repository', action='create_galaxy_docker_image' )}">Create Galaxy Docker Image</a>
                            </div>
                        %endif
                    %else:
                        <div class="toolSectionPad"></div>
                        <div class="toolSectionTitle">
                            Available Actions
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='/user', action='login' )}">Login to create a repository</a>
                        </div>
                        %if trans.app.config.enable_galaxy_flavor_docker_image:
                            <div class="toolTitle">
                                <a target="galaxy_main" href="${h.url_for( controller='repository', action='create_galaxy_docker_image' )}">Create Galaxy Docker Image</a>
                            </div>
                        %endif
                    %endif
                %endif
            </div>
        </div>
    </div>
</%def>

<%def name="center_panel()">
    <%
        if trans.app.config.require_login and not trans.user:
            center_url = h.url_for( controller='user', action='login', message=message, status=status )
        elif repository_id and changeset_revision:
            # Route in was a sharable url: /view/{owner}/{name}/{changeset_revision}.
            center_url = h.url_for( controller='repository', action='view_repository', id=repository_id, changeset_revision=changeset_revision, message=message, status=status )
        elif repository_id:
            # Route in was a sharable url: /view/{owner}/{name}.
            center_url = h.url_for( controller='repository', action='view_repository', id=repository_id, message=message, status=status )
        elif user_id:
            # Route in was a sharable url: /view/{owner}.
            center_url = h.url_for( controller='repository', action='browse_repositories', operation="repositories_by_user", user_id=user_id, message=message, status=status )
        else:
            center_url = h.url_for( controller='repository', action='browse_categories', message=message, status=status )
    %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"></iframe>
</%def>
