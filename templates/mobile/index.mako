<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Galaxy</title>
    
    <style>
    li > a > div {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    div.secondary {
        font-size: 13px;
        color: gray;
    }
    div.counts {
        padding-top: 1px;
        font-size: 13px;
        color: gray;
    }
    .logo {
        background: center left no-repeat url(${h.url_for('/static/images/galaxyIcon_noText.png')});
        padding-left: 30px;
    }
    </style>
    
    <style type="text/css" media="screen">@import "${h.url_for('/static/jqtouch/jqtouch.css')}";</style>
    <script type="text/javascript" src="${h.url_for('/static/scripts/jquery.js')}"></script>
    <script type="text/javascript" src="${h.url_for('/static/scripts/jqtouch.js')}"></script>
    <script type="text/javascript" charset="utf-8">
        $(document).jQTouch( {
            icon: "${h.url_for('static/images/galaxyIcon_noText.png')}",
            slideInSelector: 'ul li a, .row a, a.async'
        });
    </script>
</head>
<body>
    
    
    <div id="home" selected="true">
        <div class="toolbar">
            <h1><span class="logo">Galaxy</span></h1>
            <a class="button async" href="${h.url_for( action='settings' )}">Settings</a>
        </div>
        <ul class="edgetoedge">
            <li><a href="${h.url_for( action='history_list' )}">Histories</a></li>
        </ul>
    </div>

</body>
</html>