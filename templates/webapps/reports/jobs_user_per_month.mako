<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="make_sparkline" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

<%
   from galaxy import util
%>

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}

<%
   _email = util.restore_text( email )
%>

<!--jobs_user_per_month.mako-->
<div class="report">
    <div class="reportBody">
        <h3 align="center">Jobs per month for user "${_email}"</h3>
        <h4 align="center">
            <p>Click Total Jobs to see the user's jobs for that month</p>
            <p>Graph goes from first of the month to the last</p>
        </h4>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr>
                    <td colspan="2">
                        There are no jobs for user "${ _email }"
                    </td>
                </tr>
            %else:
                <tr class="header">
                    <td class="third_width">
                        ${get_sort_url(sort_id, order, 'date', 'jobs', 'user_per_month', 'Month', email=email)}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    <td class="third_width">
                        ${get_sort_url( sort_id, order, 'total_jobs', 'jobs', 'user_per_month', 'Total Jobs', email=email)}
                        <span class='dir_arrow total_jobs'>${arrow}</span>
                    </td>
                    <td></td>
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    <% key = job[2] + job[3] %>
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td>${job[2]}&nbsp;${job[3]}</td>
                        <td>
                            <a href="${h.url_for( controller='jobs', action='specified_date_handler', operation='user_for_month', email=email, specified_date=job[0], sort_id='default', order='default')}">
                                ${job[1]}
                            </a>
                        </td>
                        ${make_sparkline(key, trends[key], "bar", "/ day")}
                        <td id="${key}"></td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
<!--End jobs_user_per_month.mako-->
