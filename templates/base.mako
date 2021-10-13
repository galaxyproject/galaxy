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

        <title>
            Galaxy
            %if app.config.brand:
            | ${app.config.brand}
            %endif
            | ${self.title()}
        </title>

        ## relative href for site root
        ## TODO: try <base> tag?
        <link rel="index" href="${ h.url_for( '/' ) }"/>

        ${self.metas()}
        ${self.stylesheets()}
        ${self.javascripts()}
        ${self.javascript_app()}
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
    ${h.dist_css('base')}
</%def>

## Default javascripts
<%def name="javascripts()">
    ## TODO: remove when all libs are required directly in modules
    ${h.dist_js(
        'libs.bundled',
        'generic.bundled'
    )}
</%def>

<%def name="javascript_app()">

    ${ galaxy_client.load( app=self.js_app ) }
    ${ galaxy_client.config_sentry( app=self.js_app ) }
    %if self.js_app and self.js_app.config and self.js_app.config.ga_code:
        ${ galaxy_client.config_google_analytics(self.js_app.config.ga_code) }
    %endif
    %if self.js_app and self.js_app.config and self.js_app.config.plausible_server and self.js_app.config.plausible_domain:
        ${ galaxy_client.config_plausible_analytics(self.js_app.config.plausible_server, self.js_app.config.plausible_domain) }
    %endif
    %if self.js_app and self.js_app.config and self.js_app.config.matomo_server and self.js_app.config.matomo_site_id:
        ${ galaxy_client.config_matomo_analytics(self.js_app.config.matomo_server, self.js_app.config.matomo_site_id) }
    %endif

    %if not form_input_auto_focus is UNDEFINED and form_input_auto_focus:
        <script type="text/javascript">
            // Auto Focus on first item on form
            config.addInitialization(function() {
                console.log("base.mako", "auto focus on first item on form");
                if ( $("*:focus").html() == null ) {
                    $(":input:not([type=hidden]):visible:enabled:first").focus();
                }
            });
        </script>
    %endif

</%def>

## Additional metas can be defined by templates inheriting from this one.
<%def name="metas()"></%def>
