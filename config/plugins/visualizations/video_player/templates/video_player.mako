<%
    app_root = h.url_for("/static/plugins/visualizations/video_player/static/")
%>

<!DOCTYPE html>
<html>
<head lang="en">
    <meta name="viewport" content="width=device-width,initial-scale=1,minimum-scale=1,maximum-scale=1"/>
    <title>Video player</title>
    ${h.stylesheet_link(app_root + 'css/plyr.css')}
    ${h.stylesheet_link(app_root + 'css/video_player.css')}
</head>
<body class="body-video-player">
    ${h.javascript_link( app_root + "js/plyr.js")}
    <video id="video-container" playsinline controls>
        <source src="${h.url_for( controller='/datasets', action='index')}/${hda.id}/display" type='video/mp4' />
        <source src="${h.url_for( controller='/datasets', action='index')}/${hda.id}/display" type='video/mkv' />
    </video>
</body>
</html>

