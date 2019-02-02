<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="make_sparkline, make_spark_settings" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />
<%namespace file="/page_base.mako" import="get_pages, get_entry_selector" />
<%!
    import re
%>

%if message:
    ${render_msg( message, 'done' )}
%endif

<%
    page = page_specs.page
    offset = page_specs.offset
    entries = page_specs.entries
%>

${get_css()}

<!--jobs_per_tool.mako-->
<div class="report">
    <div class="reportBody">
        <table id="formHeader">
            <tr>
                <td>
                    ${get_pages(sort_id, order, page_specs, 'workflows', 'per_workflow', spark_time=time_period)}
                </td>
                <td>
                    <h4 align="center">Runs per Workflow</h4>
                    <h5 align="center">
                        Graph goes from present to past
                        ${make_spark_settings('workflows', 'per_workflow', spark_limit, sort_id, order, time_period, page=page, offset=offset, entries=entries)}
                    </h5>
                </td>
                <td align="right">
                    ${get_entry_selector("workflows", "per_workflow", page_specs.entries, sort_id, order)}
                </td>
            </tr>
        </table>

        <table align="center" width="60%" class="colored">
            %if len( runs ) == 0:
                <tr><td colspan="2">There are no runs.</td></tr>
            %else:
                <tr class="header">
                    <td class="quarter_width">
                        ${get_sort_url(sort_id, order, 'workflow_id', 'workflows', 'per_workflow', 'Workflow ID', spark_time=time_period, page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow workflow_id'>${arrow}</span>
                    </td>
                    <td class="quarter_width">
                        ${get_sort_url(sort_id, order, 'workflow_name', 'workflows', 'per_workflow', 'Workflow Name', spark_time=time_period, page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow workflow_name'>${arrow}</span>
                    </td>
                    <td class="quarter_width">
                        ${get_sort_url(sort_id, order, 'total_runs', 'workflows', 'per_workflow', 'Workflow Runs', spark_time=time_period, page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow total_runs'>${arrow}</span>
                    </td>
                    <td></td>
                </tr>
                <%
                   ctr = 0
                   entries = 1
                %>
                %for run in runs:
                    <% key = re.sub(r'\W+', '', str(run[2])) %>

                    %if entries > page_specs.entries:
                        <%break%>
                    %endif

                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif

                        <td>${run[2]}</td>
                        <td>${run[0]}</td>
                        <td>${run[1]}</td>
                        %try:
                            ${make_sparkline(key, trends[key], "bar", "/ " + time_period[:-1])}
                        %except KeyError:
                        %endtry
                        <td id="${key}"></td>
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
<!--End jobs_per_tool.mako-->
