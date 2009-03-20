<% _=n_ %>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

<html>

<head>
<title>Galaxy</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<link href="${h.url_for('/static/style/masthead.css')}" rel="stylesheet" type="text/css" />
</head>

<body class="mastheadPage">
<table width="100%" cellspacing="0" border="0">
<tr valign="middle"><td width="26px"><a target="_blank" href="${wiki_url}">
<img border="0" src="${h.url_for('/static/images/galaxyIcon_noText.png')}"></a></td>
<td align="left" valign="middle"><div class="pageTitle">Galaxy${brand}</div></td>
<td align="right" valign="middle">

    ${_('Info: ')}<a href="${bugs_email}">${_('report bugs')}</a>
    | <a target="_blank" href="${wiki_url}">${_('wiki')}</a>                  
    | <a target="_blank" href="${screencasts_url}">${_('screencasts')}</a>
    | <a target="_blank" href="${blog_url}">${_('blog')}</a>
    <!-- | <a target="mainframe" href="/static/index_frame_tools.html">tools</a>
    | <a target="mainframe" href="/static/index_frame_history.html">history</a> -->
    &nbsp;&nbsp;&nbsp;
    %if app.config.use_remote_user:
        Logged in as ${t.user.email}
    %else:
        %if t.user:
            ${_('Logged in as %s: ') % t.user.email}<a target="galaxy_main" href="${h.url_for( controller='user', action='index' )}">${_('manage')}</a>
            | <a target="galaxy_main" href="${h.url_for( controller='user', action='logout' )}">${_('logout')}</a>
        %else:
            ${_('Account: ')}<a target="galaxy_main" href="${h.url_for( controller='user', action='create' )}">${_('create')}</a>
            | <a target="galaxy_main" href="${h.url_for( controller='user', action='login' )}">${_('login')}</a>
        %endif
    %endif
    &nbsp;
</td>
</tr>
</table>
</body>

</html>
