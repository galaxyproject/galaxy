<%def name="get_sort_url( sort_id, order, test_id, *args )">
    <%
        if sort_id == test_id:
            if order == "asc":
                tool_order = "desc"
            else:
                tool_order = "asc"
        else:
            tool_order = "default"
    %>
    <a href="${h.url_for( controller='jobs', action='per_tool', sort_id=test_id, order=tool_order )}">${" ".join(args)}</a>
</%def>

<%def name="get_css()">
    <style>
    .dir_arrow {
        visibility: hidden
    }

    .${sort_id} {
        visibility: visible
    }
    </style>
</%def>