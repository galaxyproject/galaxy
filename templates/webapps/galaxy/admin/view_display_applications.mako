<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="card" id="display-applications-grid">
    <div class="card-header">There are currently ${len( display_applications )} <a class="icon-btn" href="${ h.url_for( controller='admin', action='reload_display_application' ) }" title="Reload all display applications" data-placement="bottom">
                        <span class="fa fa-refresh"></span>
                    </a> display applications loaded.</div>
    <div class="card-body" style="overflow: auto;">
        <table class="manage-table colored">
            <tr>
                <th>Reload</th>
                <th>Name</th>
                <th>ID</th>
                <th>Version</th>
                <th>Links</th>
                <th>Filename</th>
            </tr>
            <% ctr = 0 %>
            %for display_app in display_applications.values():
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td>
                        <a class="icon-btn" href="${ h.url_for( controller='admin', action='reload_display_application', id=display_app.id ) }" title="Reload ${ display_app.name | h } display application" data-placement="bottom">
                            <span class="fa fa-refresh"></span>
                        </a>
                    </td>
                    <td>${ display_app.name | h }</td>
                    <td>${ display_app.id | h }</td>
                    <td>${ display_app.version | h }</td>
                    <td><ul>
                        %for link in display_app.links.values():
                            <li>${  link.name | h }</li>
                        %endfor
                    </ul></td>
                    <td>${ display_app._filename | h }</td>
                </tr>
                <% ctr += 1 %>
            %endfor
        </table>
    </div>
</div>
