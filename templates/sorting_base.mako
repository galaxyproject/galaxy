<%def name="get_sort_url( sort_id, order, test_id, *args, **kwargs )">
    <%
        if sort_id == test_id:
            if order == "asc":
                tool_order = "desc"
            else:
                tool_order = "asc"
        else:
            tool_order = "default"
    %>
    %if "tool_id" in kwargs.keys():
        <a href="${h.url_for( controller='jobs', action=args[0], sort_id=test_id, order=tool_order, tool_id=kwargs.get('tool_id') )}">${" ".join(args[1:])}</a>
    %elif "email" in kwargs.keys():
        <a href="${h.url_for( controller='jobs', action=args[0], sort_id=test_id, order=tool_order, email=kwargs.get('email') )}">${" ".join(args[1:])}</a>
    %else:
        <a href="${h.url_for( controller='jobs', action=args[0], sort_id=test_id, order=tool_order )}">${" ".join(args[1:])}</a>
    %endif
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