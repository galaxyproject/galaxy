<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

<html>

<head>
<title>Galaxy</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<link href="${h.url_for('/static/style/masthead.css')}" rel="stylesheet" type="text/css" />
</head>

<body class="mastheadPage">
<table width="100%" cellspacing="0" border="0">
<tr valign="middle"><td width="26px"><a target="_blank" href="${wiki_url}">
<img border="0" src="${h.url_for('/static/images/galaxyIcon_noText.png')}"></a></td>
<td align="left" valign="middle"><div class="pageTitle">Galaxy${brand}</div></td>
<td align="right" valign="middle">

    Info: <a href="${bugs_email}">report bugs</a>
    | <a target="_blank" href="${wiki_url}">wiki</a>                  
    | <a target="_blank" href="${screencasts_url}">screencasts</a>
    | <a target="_blank" href="${blog_url}">blog</a>
    %if admin_user == "true":
        | <a target="galaxy_main" href="${h.url_for( controller='admin', action='index' )}">admin</a>
    %endif
    <!-- | <a target="mainframe" href="/static/index_frame_tools.html">tools</a>
    | <a target="mainframe" href="/static/index_frame_history.html">history</a> -->
    &nbsp;&nbsp;&nbsp;
    %if app.config.use_remote_user:
        Logged in as ${t.user.email}
    %else:
        %if t.user:
            Logged in as ${t.user.email}: <a target="galaxy_main" href="${h.url_for( controller='user', action='index' )}">manage</a>
            | <a target="galaxy_main" href="${h.url_for( controller='user', action='logout' )}">logout</a>
        %else:
            Account: <a target="galaxy_main" href="${h.url_for( controller='user', action='create' )}">create</a>
            | <a target="galaxy_main" href="${h.url_for( controller='user', action='login' )}">login</a>
        %endif
    %endif
    &nbsp;
</td>
</tr>
</table>
</body>

</html>
