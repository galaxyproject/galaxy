## This needs to be on the first line, otherwise IE6 goes into quirks mode
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

## Default title
<%def name="title()">Galaxy Reports</%def>

## Default stylesheets
<%def name="stylesheets()">
</%def>

## Default javascripts
<%def name="javascripts()">
  <!--[if lt IE 7]>
  <script type='text/javascript' src="/static/scripts/IE7.js"> </script>
  <script type='text/javascript' src="/static/scripts/ie7-recalc.js"> </script>
  <![endif]-->
</%def>

## Default late-load javascripts
<%def name="late_javascripts()">
</%def>
    
## Masthead
<%def name="masthead()">
  <iframe name="galaxy_masthead" src="${h.url_for( 'masthead' )}" width="38" height="100%" frameborder="0" scroll="no" style="margin: 0; border: 0 none; width: 100%; height: 38px; overflow: hidden;"> </iframe>
</%def>

## Document
<html lang="en">
  <head>
    <title>${self.title()}</title>
    ${self.javascripts()}
    ${self.stylesheets()}
  </head>
  <body scroll="no">
    ## Background displays first
    <div id="background"></div>
    ## Layer iframes over backgrounds
    <div id="masthead">
      ${self.masthead()}
    </div>
    <div id="center">
      ${self.center_panel()}
    </div>
    ## Allow other body level elements
    ${next.body()}
  </body>
  ## Scripts can be loaded later since they progressively add features to
  ## the panels, but do not change layout
  ${self.late_javascripts()}
</html>
