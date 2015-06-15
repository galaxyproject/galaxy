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
    <script>
        $(document).ready(function(e) {
            $("#${id}").sparkline(${data}, {
                type: '${sparktype}',
                tooltipFormat: '<span style="color: {{color}}">&#9679;</span> {{value}} ${length}</span>'
            }).css("width", "1%");
        })
    </script>
</%def>