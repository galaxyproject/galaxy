<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

%if not sanitize_all:
    <div><p>You currently have <strong>sanitize_all_html</strong> set to False
    in your galaxy configuration file.  This prevents Galaxy from sanitizing
    tool outputs, which is an important security feature.  For improved
    security, we recommend you disable the old-style blanket sanitization and
    manage it via this whitelist instead.</p></div>
%else:
    <div><p>This interface will allow you to mark particular tools as 'trusted'
    after which Galaxy will no longer attempt to sanitize any HTML contents of
    datasets created by these tools upon display.  Please be aware of the
    potential security implications of doing this -- bypassing sanitization
    using this whitelist disables Galaxy's security feature (for the indicated
    tools) that prevents Galaxy from displaying potentially malicious
    Javascript.<br/>
    Note that datasets originating from an archive import are still sanitized
    even when their creating tool is whitelisted since it isn't possible to
    validate the information supplied in the archive.</p></div>
    <form name="sanitize_whitelist" method="post" action="${h.url_for( controller='admin', action='sanitize_whitelist' )}">
    <div class="card mb-3">
        <div class="card-header">Tool Sanitization Whitelist</div>
        <div class="card-body overflow-auto">
            <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                <tr>
                    <th>Whitelist</th>
                    <th>Name</th>
                    <th>ID</th>
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
%endif
