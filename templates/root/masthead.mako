<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

<html>

<head>
<title>Galaxy</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<link href="${h.url_for('/static/style/masthead.css')}" rel="stylesheet" type="text/css" />
</head>

<body class="mastheadPage" scroll="no">
<div id="tab-bar-bottom"></div>
<table width="100%" cellspacing="0" border="0">
<tr valign="middle"><td width="26px"><a target="_blank" href="${wiki_url}">
<img border="0" src="${h.url_for('/static/images/galaxyIcon_noText.png')}"></a></td>
<td align="left" valign="middle"><div class="pageTitle">Galaxy${brand}</div></td>
<td align="right" valign="middle">
    %if not app.config.require_login or ( app.config.require_login and trans.user):
        View: <span class="link-group">
            <span
                %if active_view == "analysis":
                    class="active-link"
                %endif
            ><a target="_parent" href="${h.url_for( controller='root', action='index' )}">analysis</a></span>
            | <span
                %if active_view == "workflow":
                    class="active-link"
                %endif
            ><a target="_parent" href="${h.url_for( controller='workflow', action='index' )}">workflow</a></span>
            %if admin_user == "true":
            | <span
                %if active_view == "admin":
                    class="active-link"
                %endif
            ><a target="_parent" href="${h.url_for( controller='admin', action='index' )}">admin</a></span>
            %endif
            
        </span>
        &nbsp;&nbsp;&nbsp;
    %endif
    <span class="link-group">
    Info: <span><a href="${bugs_email}">report bugs</a></span>
    | <span><a target="_blank" href="${wiki_url}">wiki</a></span>             
    | <span><a target="_blank" href="${screencasts_url}">screencasts</a></span>
    </span>
    <!-- | <a target="mainframe" href="/static/index_frame_tools.html">tools</a>
    | <a target="mainframe" href="/static/index_frame_history.html">history</a> -->
    &nbsp;&nbsp;&nbsp;
    <span class="link-group">
    %if app.config.use_remote_user:
        Logged in as ${t.user.email}
    %else:
        %if t.user:
            Logged in as ${t.user.email}: <span><a target="galaxy_main" href="${h.url_for( controller='user', action='index' )}">manage</a></span>
            %if app.config.require_login:
                | <span><a target="_parent" href="${h.url_for( controller='root', action='index', m_c='user', m_a='logout' )}">logout</a></span>
            %else:
                | <span><a target="galaxy_main" href="${h.url_for( controller='user', action='logout' )}">logout</a></span>
            %endif
        %else:
            Account:
            %if app.config.allow_user_creation:
                <span><a target="galaxy_main" href="${h.url_for( controller='user', action='create' )}">create</a></span> |
            %endif
            <span><a target="galaxy_main" href="${h.url_for( controller='user', action='login' )}">login</a></span>
        %endif
    %endif
    &nbsp;
    </span>
</td>
</tr>
</table>
</body>

</html>
