<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    from galaxy.web.framework.helpers import time_ago
    from galaxy.webapps.galaxy.controllers.library_common import get_containing_library_from_library_dataset
%>

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <h3 align="center">Dataset Information</h3>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Date uploaded:</label>
            ${time_ago( dataset.create_time )}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Last updated:</label>
            ${time_ago( dataset.update_time )}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>File size:</label>
            ${dataset.get_size( nice_size=True )}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>State:</label>
            ${dataset.state}
            <div style="clear: both"></div>
        </div>
    </div>
</div>
%if associated_hdas:
    <p/>
    <b>Active (undeleted) history items that use this library dataset's disk file</b>
    <div class="toolForm">
        <table class="grid">
            <thead>
                <tr>
                    <th>History</th>
                    <th>History Item</th>
                    <th>Last Updated</th>
                    <th>User</th>
                </tr>
            </thead>
            %for hda in associated_hdas:
                <tr>
                    <td>
                        %if hda.history:
                            ${hda.history.get_display_name()}
                        %else:
                            no history
                        %endif
                    </td>
                    <td>${hda.get_display_name()}</td>
                    <td>${time_ago( hda.update_time )}</td>
                    <td>
                        %if hda.history and hda.history.user:
                            ${hda.history.user.email}
                        %else:
                            anonymous
                        %endif
                    </td>
                </tr>
            %endfor
        </table>
    </div>
    <p/>
%endif
%if associated_lddas:
    <p/>
    <b>Other active (undeleted) library datasets that use this library dataset's disk file</b>
    <div class="toolForm">
        <table class="grid">
            <thead>
                <tr>
                    <th>Library</th>
                    <th>Folder</th>
                    <th>Library Dataset</th>
                    <th>Last Updated</th>
                    <th>Uploaded By</th>
                </tr>
            </thead>
            %for ldda in associated_lddas:
                <% containing_library = get_containing_library_from_library_dataset( trans, ldda.library_dataset ) %>
                <tr>
                    <td>
                        <%
                            if containing_library:
                                library_display_name = containing_library.get_display_name()
                            else:
                                library_display_name = 'no library'
                        %>
                        ${library_display_name}
                    </td>
                    <td>
                        <%
                            library_dataset = ldda.library_dataset
                            folder = library_dataset.folder
                            folder_display_name = folder.get_display_name()
                            if folder_display_name == library_display_name:
                                folder_display_name = 'library root'
                        %>
                        ${folder_display_name}
                    </td>
                    <td>${ldda.get_display_name()}</td>
                    <td>${time_ago( ldda.update_time )}</td>
                    <td>
                        %if ldda.user:
                            ${ldda.user.email}
                        %else:
                            anonymous
                        %endif
                    </td>
                </tr>
            %endfor
        </table>
    </div>
    <p/>
%endif
