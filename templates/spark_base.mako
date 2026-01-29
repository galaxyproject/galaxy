<%def name="make_spark_settings( controller, action, limit, sort_id, order, time_period, **kwargs )">
    <div id="spark_time_select">
        <form method="post" controller=${controller} action=${action}>
            <input type="hidden" value=${sort_id} name="sort_id">
            <input type="hidden" value=${order} name="order">
            %try:
                <input type="hidden" value=${kwargs['entries']} name="entries">
            %except KeyError:
            %endtry

            %try:
                <input type="hidden" value=${kwargs['page']} name="page">
            %except KeyError:
            %endtry

            %try:
                <input type="hidden" value=${kwargs['offset']} name="offset">
            %except KeyError:
            %endtry

            ${limit}
            <select name="spark_time">
                %if time_period == "days":
                    <option value="days" selected="selected">Days</option>
                %else:
                    <option value="days">Days</option>
                %endif
                
                %if time_period == "weeks":
                    <option value="weeks" selected="selected">Weeks</option>
                %else:
                    <option value="weeks">Weeks</option>
                %endif
                
                %if time_period == "months":
                    <option value="months" selected="selected">Months</option>
                %else:
                    <option value="months">Months</option>
                %endif
                
                %if time_period == "years":
                    <option value="years" selected="selected">Years</option>
                %else:
                    <option value="years">Years</option>
                %endif
            </select>
            <button id="spark_select">Go</button>
        </form>
    </div>
</%def>

<%def name="make_sparkline(id, data, sparktype, length)">
    <%
        color = '<span style="color: {{color}}">&#9679;</span>'
        if sparktype == "bar":
            tooltip = color + '{{value}} ' + length + '</span>'
        else:
            tooltip = color + '{{prefix}}{{y}} ' + length + '{{suffix}}</span>'
    %>
    <script>
        $(document).ready(function(e) {
            $("#${id}").sparkline(${data}, {
                type: '${sparktype}',
                tooltipFormat: '${tooltip}'
            }).css("width", "1%");
        })
    </script>
</%def>