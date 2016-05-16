<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}

<!--users_user_disk_usage.mako-->
<div class="report">
    <h3 align="center">Per-user disk usage</h3>
    <h4 align="center">Listed in descending order by usage size</h4>
    <table class="colored diskUsageForm">
        <tr>
            <td>
                <form method="post"
                      controller="users"
                      action="user_disk_usage">
                    <p>
                        Top <input type="textfield"
                                   value="${user_cutoff}"
                                   size="3"
                                   name="user_cutoff">
                        shown (0 = all).&nbsp;
                        <button name="action" value="user_cutoff">
                            Go
                        </button>
                    </p>
                </form>
            </td>
        </tr>
    </table>
    <table class="colored diskUsageForm">
        %if users:
            <tr class="header">
                <td class="half_width">
                    ${get_sort_url(sort_id, order, 'email', 'users', 'user_disk_usage', 'Email')}
                    <span class='dir_arrow email'>${arrow}</span>
                </td>
                <td class="half_width">
                    ${get_sort_url(sort_id, order, 'disk_usage', 'users', 'user_disk_usage', 'Disk Usage')}
                    <span class='dir_arrow disk_usage'>${arrow}</span>
                </td>
            </tr>
            <% ctr = 0 %>
            %for user in users:
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td>${user.email}</td>
                    <td>${user.get_disk_usage( nice_size=True )}</td>
                </tr>
                <% ctr += 1 %>
            %endfor
        %endif
    </table>
</div>
<!--End users_user_disk_usage.mako-->
