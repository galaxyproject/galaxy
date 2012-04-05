<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    %if invalid_tools_dict:
        <div class="toolFormTitle">Invalid tools<i> - click the tool config file name to see why the tool is invalid</i></div>
            <div class="form-row">
                <table class="grid">
                    <tr>
                        <th>Tool config</th>
                        <th>Repository name</th>
                        <th>Changeset revision</th>
                    </tr>
                    %for invalid_tool_config, repository_tup in invalid_tools_dict.items():
                        <% repository_id, repository_name, changeset_revision = repository_tup %>
                        <tr>
                            <td>
                                <a class="view-info" href="${h.url_for( controller='repository', action='load_invalid_tool', repository_id=trans.security.encode_id( repository_id ), tool_config=invalid_tool_config, changeset_revision=changeset_revision, webapp=webapp )}">
                                    ${invalid_tool_config}
                                </a>
                            </td>
                            <td>${repository_name}</td>
                            <td>${changeset_revision}</td>
                        </tr>
                    %endfor
                </table>
            </div>
        </div>
    %else:
        <div class="form-row">
            %if cntrller == 'admin' and trans.user_is_admin():
                No repositories in this tool shed contain invalid tools.
            %else:
                None of your repositories contain invalid tools.
            %endif
        </div>
    %endif
</div>
