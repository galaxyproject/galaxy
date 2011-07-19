<% _=n_ %>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
    <head>
        <title>${self.title()}</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ${self.metas()}
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
    ${h.css('base')}
</%def>

## Default javascripts
<%def name="javascripts()">
  ## <!--[if lt IE 7]>
  ## <script type='text/javascript' src="/static/scripts/IE7.js"> </script>
  ## <![endif]-->
  ${h.js( "jquery", "galaxy.base" )}
</%def>

## Additional metas can be defined by templates inheriting from this one.
<%def name="metas()"></%def>
