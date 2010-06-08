<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">All Jobs for ${month_label}&nbsp;${year_label}</h3>
        <h4 align="center">Click Total Jobs to see jobs for that day</h4>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="5">There are no jobs for ${month_label}&nbsp;${year_label}</td></tr>
            %else:
                <tr class="header">
                    <td>Day</td>
                    <td>Date</td>
                    <td>User Jobs</td>
                    <td>Monitor Jobs</td>
                    <td>Total Jobs</td>
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td>${job[0]}</td>
                        <td>${month_label}&nbsp;${job[5]},&nbsp;${year_label}</td>
                        <td>${job[2]}</td>
                        <td>${job[3]}</td>
                        <td><a href="${h.url_for( controller='jobs', action='specified_date_handler', specified_date=job[1], webapp='reports' )}">${job[4]}</a></td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
