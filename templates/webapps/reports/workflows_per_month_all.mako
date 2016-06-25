<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />
<%namespace file="/spark_base.mako" import="make_sparkline, make_spark_settings" />
<%namespace file="/page_base.mako" import="get_pages, get_entry_selector" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<%
    page = page_specs.page
    offset = page_specs.offset
    entries = page_specs.entries
%>

${get_css()}

<div class="report">
    <div class="reportBody">
        <table id="formHeader">
            <tr>
                <td>
                    ${get_pages(sort_id, order, page_specs, 'workflows', 'per_month_all')}
                </td>
                <td>
                    <h3 align="center">Workflows Per Month</h3>
                </td>
                <td align="right">
                    ${get_entry_selector("workflows", "per_month_all", page_specs.entries, sort_id, order)}
                </td>
            </tr>
        </table>

        <table align="center" width="60%" class="colored">
            %if len( workflows ) == 0:
                <tr><td colspan="4">There are no workflows</td></tr>
            %else:
                <tr class="header">
                    <td class="half_width">
                        ${get_sort_url(sort_id, order, 'date', 'workflows', 'per_month_all', 'Month', page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    <td class="half_width">
                        ${get_sort_url(sort_id, order, 'total_workflows', 'workflows', 'per_month_all', 'Total', page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow total_workflows'>${arrow}</span>
                    </td>
                    <td></td>
                </tr>
                <%
                    ctr = 0
                    entries = 1
                %>
                %for workflow in workflows:
                    <% key = str(workflow[2]) + str(workflow[3]) %>

                    %if entries > page_specs.entries:
                        <%break%>
                    %endif

                    <%
                        month = workflow[0]
                        total = workflow[1]
                    %>

                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif

                        <td>${month}</td>
                        <td>${total}</td>
                        %try:
                            ${make_sparkline(key, trends[key], "bar", "/ day")}
                        %except KeyError:
                        %endtry
                        <td id=${key}></td>
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
