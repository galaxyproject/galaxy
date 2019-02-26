<%
    app_root = h.url_for("/static/plugins/visualizations/audio_player/static/")
%>

<!DOCTYPE html>
<html>
<head lang="en">
    <meta name="viewport" content="width=device-width,initial-scale=1,minimum-scale=1,maximum-scale=1"/>
    <title>Audio player</title>
    ${h.stylesheet_link(app_root + 'plyr.css' )}
</head>
<body class="body-ap">
    <div class="main-container">
    </div>
    ${h.javascript_link( app_root +  "plyr.js" )}
    <script>
        $(document).ready(function () {
            console.log('${hda}');
        });
    </script>	
    <audio id="main-container" controls>
        <source src="${hda.name}" type="audio/wav" />
    </audio>

</body>
</html>

