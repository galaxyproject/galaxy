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
        <link rel="index" href="${ h.url_for( '/' ) }"/>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ${self.stylesheets()}
        ${self.javascripts()}
    </head>
    <style>
        body {
            margin: 0;
            overflow: hidden;
        }
    </style>
    <body>
        ${self.get_body()}
    </body>
</html>
</%def>

## Default title
<%def name="title()">${ visualization_display_name + ' | Galaxy' }</%def>

## Default javascripts
<%def name="javascripts()">
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

## Default stylesheets
<%def name="stylesheets()"></%def>

## Default body
<%def name="get_body()"></%def>
