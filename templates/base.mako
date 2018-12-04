<%namespace name="galaxy_client" file="/galaxy_client_app.mako" />
<% self.js_app = None %>

<% _=n_ %>
<!DOCTYPE HTML>
<html>
    <!--base.mako-->
    ${self.init()}
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ## For mobile browsers, don't scale up
        <meta name = "viewport" content = "maximum-scale=1.0">
        ## Force IE to standards mode, and prefer Google Chrome Frame if the user has already installed it
        <meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1">
        ${self.metas()}

        <title>
            Galaxy
            %if app.config.brand:
            | ${app.config.brand}
            %endif
            | ${self.title()}
        </title>

        ## relative href for site root
        ## TODO: This is what the <base> tag is for
        <link rel="index" href="${ h.url_for( '/' ) }"/>

        ${stylesheets()}
        ${javascripts()}
        ${javascript_app()}
    </head>
    <body class="inbound">
        ${next.body()}
    </body>
</html>

## Default title
<%def name="title()"></%def>

## Default init
<%def name="init()"></%def>

## Default stylesheets
<%def name="stylesheets()">
    ${h.css('bootstrap-tour')}
    ${h.css('base')}
</%def>

## Default javascripts
<%def name="javascripts()">
    <!-- base.mako javascripts() -->
    ${h.js(
        ## TODO: remove when all libs are required directly in modules
        'bundled/libs.chunk',
        'bundled/base.chunk'
    )}
    ${ javascripts_entry()}
</%def>

<%def name="javascripts_entry()">
    <!-- base.mako javascripts_entry() -->
    ${ h.js('bundled/generic.bundled') }
</%def>

<%def name="javascript_app()">
    <!-- base.mako javascript_app() -->
    ${ galaxy_client.load( app=self.js_app ) }
</%def>

## Additional metas can be defined by templates inheriting from this one.
<%def name="metas()"></%def>
