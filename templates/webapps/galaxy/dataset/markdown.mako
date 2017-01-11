<%inherit file="/base.mako"/>

<div id="raw_content" style="display: none">${ data | h}</div>
<div id="html_content"></div>

<script type="text/javascript">
    require(['libs/showdown'], function(showdown) {
        var converter = new showdown.Converter(),
            text = $("#raw_content").html(),
            html = converter.makeHtml(text);

        $("#html_content").html(html);
    });

</script>
