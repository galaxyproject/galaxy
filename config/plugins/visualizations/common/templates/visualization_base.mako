# -*- coding: utf-8 -*-
<% _=n_ %>

%if embedded:
    ${self.as_embedded()}
%else:
    ${self.as_page()}
%endif

## render this inside another page or via ajax
<%def name="as_embedded()">
    ${self.stylesheets()}
    ${self.javascripts()}
    ${self.get_body()}
</%def>

## render this as its own page
<%def name="as_page()">
<!DOCTYPE HTML>
<html>
    <head>
        <title>${self.title()}</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ${self.metas()}
        ${self.stylesheets()}
        ${self.javascripts()}
    </head>
    <body>
        ${self.get_body()}
    </body>
</html>
</%def>
##TODO: late_javascripts

## Default body
<%def name="get_body()"></%def>

## Default title
<%def name="title()">${visualization_name}</%def>

## Additional metas can be defined by templates inheriting from this one.
<%def name="metas()"></%def>

## Default stylesheets
<%def name="stylesheets()">
${h.css('base')}
</%def>

## Default javascripts
<%def name="javascripts()">
${h.js(
    "libs/jquery/jquery",
    "libs/jquery/jquery.migrate"
)}

<script type="text/javascript">
    // console protection
    window.console = window.console || {
        log     : function(){},
        debug   : function(){},
        info    : function(){},
        warn    : function(){},
        error   : function(){},
        assert  : function(){}
    };
</script>
</%def>
