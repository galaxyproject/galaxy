<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">Jobs In Error Per Month</h3>
        <h4 align="center">Click Month to view the number of jobs in error for each day of that month</h4>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="2">There are no jobs in the error state</td></tr>
            %else:
                <tr class="header">
                    <td>Month</td>
                    <td>Jobs In Error</td>
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td><a href="${h.url_for( controller='jobs', action='specified_month_in_error', specified_date=job[0]+'-01' )}">${job[2]}&nbsp;${job[3]}</a></td>
                        <td>${job[1]}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
