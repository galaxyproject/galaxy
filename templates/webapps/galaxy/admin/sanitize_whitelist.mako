<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<form name="sanitize_whitelist" action="${h.url_for( controller='admin', action='sanitize_whitelist' )}">
<div class="toolForm">
    <div class="toolFormTitle">Tool Sanitization Whitelist</div>
    <div class="toolFormBody">
        <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
            <tr>
                <th bgcolor="#D8D8D8">Whitelist</th>
                <th bgcolor="#D8D8D8">Name</th>
                <th bgcolor="#D8D8D8">ID</th>
            </tr>
            <% ctr = 0 %>
            %for tool in tools.values():
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td>
                        %if tool.id in trans.app.config.sanitize_whitelist:
                            <input type="checkbox" name="tools_to_whitelist" value="${tool.id}" checked="checked"/>
                        %else:
                            <input type="checkbox" name="tools_to_whitelist" value="${tool.id}"/>
                        %endif
                    </td>
                    <td>${ tool.name | h }</td>
                    <td>${ tool.id | h }</td>
                </tr>
                <% ctr += 1 %>
            %endfor
        </table>
    </div>
</div>
<input type="submit" name="submit_whitelist" value="Submit new whitelist"/>
</form>
