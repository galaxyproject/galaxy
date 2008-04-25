<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>

<head>
<title>${self.title()}</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
${self.stylesheets()}
${self.javascripts()}
</head>

<body>
  ${next.body()}
</body>
</html>

## Default title
<%def name="title()"></%def>

## Default stylesheets
<%def name="stylesheets()">
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
</%def>

## Default javascripts
<%def name="javascripts()">
  <script type="text/javascript" src="${h.url_for('/static/scripts/jquery.js')}"></script>
</%def>