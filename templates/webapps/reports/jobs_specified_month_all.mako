<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}

<!--jobs_specified_month_all.mako-->
<div class="toolForm">
    <div class="toolFormBody">
        <style>
            #back_button, #next_button, #curr_button, .page_button {
                display: inline-block
            }
            #page_selector {
                position: absolute;
                margin-left: 10px;
            }
        </style>
        <div id="page_selector">
            <div id="back_button">&#x21a4;</div>
            %for x in range(-2,3):
                <% 
                   page = int(page_specs.page) + x
                   pages_found = int(page_specs.pages_found)
                %>
                %if page > 0:
                    %if x == 0:
                        <div id="curr_button">${page}</div>
                    %elif page < page_specs.page + pages_found:
                        <%
                           entries = page_specs.entries
                           offset = page_specs.entries * (page - 1)
                        %>
                        <div class="page_button">${get_sort_url(sort_id, "default", sort_id, 'jobs', 'specified_month_all', str(page), page=page, entries=entries, offset=offset)}</div>
                    %endif
                %endif
            %endfor
            <div id="next_button">&#x21a6;</div>
        </div>
        <h4 align="center">Jobs for ${month_label}&nbsp;${year_label}</h4>
        <h5 align="center">Click job count to see the day's details</h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="5">There are no jobs for ${month_label}&nbsp;${year_label}</td></tr>
            %else:
                <tr class="header">
                    <td>Day</td>
                    <td>
                        ${get_sort_url(sort_id, order, 'date', 'jobs', 'specified_month_all', 'Date')}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    %if is_user_jobs_only:
    					<td>
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'specified_month_all', 'User Jobs')}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
					%else:
	                    <td>
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'specified_month_all', 'User and Monitor Jobs')}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
	                %endif
                </tr>
                <% 
                   ctr = 0
                   entries = 1
                %>
                %for job in jobs:
                    %if entries > page_specs.entries:
                        <%break%>
                    %endif
                    
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td>${job[0]}</td>
                        <td>${month_label}&nbsp;${job[1]},&nbsp;${year_label}</td>
                        <td><a href="${h.url_for( controller='jobs', action='specified_date_handler', specified_date=job[3], webapp='reports', sort_id='default', order='default' )}">${job[2]}</a></td>
                    </tr>
                    <% 
                       ctr += 1
                       entries += 1
                    %>
                %endfor
            %endif
        </table>
    </div>
</div>
<!--End jobs_specified_month_all.mako-->
