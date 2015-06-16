<%def name="jqs_style()">
    <style>
    .jqstooltip {
        -webkit-box-sizing: content-box;
        -moz-box-sizing: content-box;
        box-sizing: content-box;
    }
    </style>
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