<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

${render_galaxy_repository_actions( repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${repository.name}</div>
    <div class="toolFormBody">
        <form name="deactivate_or_uninstall_repository" id="deactivate_or_uninstall_repository" action="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>Description:</label>
                ${repository.description}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Revision:</label>
                ${repository.changeset_revision}</a>
            </div>
            <div class="form-row">
                <label>Tool shed:</label>
                ${repository.tool_shed}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Owner:</label>
                ${repository.owner}
            </div>
            <div class="form-row">
                <label>Deleted:</label>
                ${repository.deleted}
            </div>
            <div class="form-row">
                %if repository.can_deactivate:
                    <% deactivate_uninstall_button_text = "Deactivate or Uninstall" %>
                    ${remove_from_disk_check_box.get_html()}
                    <label for="repository" style="display: inline;font-weight:normal;">Check to uninstall or leave blank to deactivate</label>
                    <br/><br/>
                    <label>Deactivating this repository will result in the following:</label>
                    <div class="toolParamHelp" style="clear: both;">
                            * The repository and all of it's contents will remain on disk.
                    </div>
                    %if repository.includes_tools_for_display_in_tool_panel:
                        <div class="toolParamHelp" style="clear: both;">
                            * The repository's tools will not be loaded into the tool panel.
                        </div>
                    %endif
                    %if repository.includes_tool_dependencies:
                        <div class="toolParamHelp" style="clear: both;">
                            * The repository's installed tool dependencies will remain on disk.
                        </div>
                    %endif
                    %if repository.includes_datatypes:
                        <div class="toolParamHelp" style="clear: both;">
                            * The repository's datatypes, datatype converters and display applications will be eliminated from the datatypes registry.
                        </div>
                    %endif
                    <div class="toolParamHelp" style="clear: both;">
                        * The repository record's deleted column in the tool_shed_repository database table will be set to True.
                    </div>
                    <br/>
                %else:
                    <% deactivate_uninstall_button_text = "Uninstall" %>
                    ##hack to mimic check box
                    <input type="hidden" name="remove_from_disk" value="true"/><input type="hidden" name="remove_from_disk" value="true"/>
                %endif
                <label>Uninstalling this repository will result in the following:</label>
                <div class="toolParamHelp" style="clear: both;">
                    * The repository and all of it's contents will be removed from disk.
                </div>
                %if repository.includes_tools_for_display_in_tool_panel:
                    <div class="toolParamHelp" style="clear: both;">
                        * The repository's tool tag sets will be removed from the tool config file in which they are defined.
                    </div>
                %endif
                %if repository.includes_tool_dependencies:
                    <div class="toolParamHelp" style="clear: both;">
                        * The repository's installed tool dependencies will be removed from disk.
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        * Each associated tool dependency record's status column in the tool_dependency database table will be set to 'Uninstalled'.
                    </div>
                %endif
                %if repository.includes_datatypes:
                    <div class="toolParamHelp" style="clear: both;">
                        * The repository's datatypes, datatype converters and display applications will be eliminated from the datatypes registry.
                    </div>
                %endif
                <div class="toolParamHelp" style="clear: both;">
                    * The repository record's deleted column in the tool_shed_repository database table will be set to True.
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    * The repository record's uninstalled column in the tool_shed_repository database table will be set to True.
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="deactivate_or_uninstall_repository_button" value="${deactivate_uninstall_button_text}"/>
            </div>
        </form>
    </div>
</div>
