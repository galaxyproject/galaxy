<%inherit file="/base.mako"/>
<%def name="title()">Galaxy Reports Main</%def>

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">
<html>
  <head>
    <title>Galaxy Reports Main</title>
    <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
  </head>
  <frameset rows="36,*" border="0" framespacing="0" frameborder="0">
    <frame name="masthead" src="${h.url_for('masthead')}" frameborder="0" border="0" framespacing="0">
    <frame name="main_frame" src="${h.url_for('main_frame')}" border="3" framespacing="3" frameborder="1">
  </frameset>
</html>
