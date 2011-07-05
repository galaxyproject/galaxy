<%namespace file="/display_common.mako" import="render_message" />
<%namespace file="/grid_base.mako" import="*" />
<%namespace file="/grid_common.mako" import="*" />
<%inherit file="/grid_base.mako" />

## Render grid header.
<%def name="render_grid_header( grid, repo_grid, render_title=True)">
    <div class="grid-header">
        %if render_title:
            ${grid_title()}
        %endif
        %if grid.global_actions:
            <ul class="manage-table-actions">
                %if len( grid.global_actions ) < 4:
                    %for action in grid.global_actions:
                        <li><a class="action-button" href="${h.url_for( **action.url_args )}">${action.label}</a></li>
                    %endfor
                %else:
                    <li><a class="action-button" id="action-8675309-popup" class="menubutton">Actions</a></li>
                    <div popupmenu="action-8675309-popup">
                        %for action in grid.global_actions:
                            <a class="action-button" href="${h.url_for( **action.url_args )}">${action.label}</a>
                        %endfor
                    </div>
                %endif
            </ul>
        %endif
        ${render_grid_filters( repo_grid, render_advanced_search=False )}
    </div>
</%def>

<%def name="make_grid( grid, repo_grid )">
    <div class="loading-elt-overlay"></div>
    <table>
        <tr>
            <td width="75%">${self.render_grid_header( grid, repo_grid )}</td>
            <td></td>
            <td></td>
        </tr>
        <tr>
            <td width="100%" id="grid-message" valign="top">${render_message( message, status )}</td>
            <td></td>
            <td></td>
        </tr>
    </table>
    ${render_grid_table( grid, show_item_checkboxes )}
</%def>

<%def name="grid_body( grid )">
    <%
        from galaxy.webapps.community.controllers.repository import RepositoryListGrid
        repo_grid = RepositoryListGrid()
    %>
    ${self.make_grid( grid, repo_grid )}
</%def>

<%def name="center_panel()">
    <div style="overflow: auto; height: 100%">
        <div class="page-container" style="padding: 10px;">
            ${self.grid_body( grid )}
        </div>
    </div>
</%def>
