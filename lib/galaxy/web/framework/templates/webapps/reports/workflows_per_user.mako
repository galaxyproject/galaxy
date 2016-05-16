<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="make_sparkline, make_spark_settings" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />
<%namespace file="/page_base.mako" import="get_pages, get_entry_selector" />

<%!
    import re
    from galaxy import util
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

<div class="report">
    <div class="reportBody">
        <table id="formHeader">
            <tr>
                <td>
                    ${get_pages(sort_id, order, page_specs, 'workflows', 'per_user', spark_time=time_period)}
                </td>
                <td>
                    <h3 align="center">Workflows Per User</h3>
                    <h5 align="center">
                        Graph goes from present to past
                        ${make_spark_settings("jobs", "per_user", spark_limit, sort_id, order, time_period, page=page, offset=offset, entries=entries)}
                    </h5>
                </td>
                <td align="right">
                    ${get_entry_selector("workflows", "per_user", page_specs.entries, sort_id, order)}
                </td>
            </tr>
        </table>

        <table align="center" width="60%" class="colored">
            %if len( workflows ) == 0:
                <tr><td colspan="2">There are no workflows</td></tr>
            %else:
                <tr class="header">
                    <td class="half_width">
                        ${get_sort_url(sort_id, order, 'user_email', 'workflows', 'per_user', 'User', spark_time=time_period, page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow user_email'>${arrow}</span>
                    </td>
                    <td class="third_width">
                        ${get_sort_url(sort_id, order, 'total_workflows', 'workflows', 'per_user', 'Total Workflows', spark_time=time_period, page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow total_workflows'>${arrow}</span>
                    </td>
                    <td></td>
                </tr>
                <%
                   ctr = 0
                   entries = 1
                %>
                %for workflow in workflows:
                    <%
                        email = workflow[0]
                        total = workflow[1]
                        user = trans.sa_session.query( trans.model.User ) \
                                               .filter_by( email=email ) \
                                               .one()
                        key = re.sub(r'\W+', '', workflow[0])
                    %>

                    %if entries > page_specs.entries:
                        <%break%>
                    %endif

                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif

                        <td>
                            <a href="${h.url_for( controller='workflows', action='user_per_month', id=trans.security.encode_id( user.id ), email=util.sanitize_text( user.email ), sort_id='default', order='default')}">
                                ${email}
                            </a>
                        </td>
                        <td>${total}</td>
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
