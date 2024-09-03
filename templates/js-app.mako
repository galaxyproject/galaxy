<%namespace name="galaxy_client" file="/galaxy_client_app.mako" />
<!DOCTYPE HTML>
<html lang="en">
    <!--js-app.mako-->
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />

        <!-- Set meta description -->
        <%
            if request.path.startswith('/login'):
                meta_description = "Log in to Galaxy to get access to more tools and resources. Register now for a free account."
            elif request.path.startswith('/workflows'):
                meta_description = "Galaxy Workflows facilitate rigorous, reproducible analysis pipelines that can be shared with the community."
            else:
                meta_description = "Galaxy is a community-driven web-based analysis platform for life science research."
        %>
        <meta name="description" content="${meta_description}" />

        <title>
            Galaxy
            %if app.config.brand:
            | ${app.config.brand}
            %endif
        </title>

        ## relative href for site root
        <link rel="index" href="${ h.url_for( '/' ) }"/>

        ## TODO: use loaders to move everything but the essentials below the fold
        ${ h.dist_css(
            'base',
        )}
        ${ h.css(
            'jquery-ui/smoothness/jquery-ui',
        )}
    </head>

    <body scroll="no" class="full-content">
        <!-- Provide mount point for application -->
        <main>
            <div id="app"></div>
        </main>

        ${ js_disabled_warning() }
        ${ javascripts() }
        ${ javascript_app() }
    </body>
</html>

<%def name="javascripts()">
    ${ h.dist_js(
        'libs.bundled',
        '%s.bundled' % js_app_name
    )}
</%def>

<%def name="javascript_app()">

    <script type="text/javascript">
        console.debug("Initializing javascript application:", "${js_app_entry_fn}");

        // js-app.mako
        var options = ${ h.dumps( options ) };
        var bootstrapped = ${ h.dumps( bootstrapped ) };

        config.set({
            options: options,
            bootstrapped: bootstrapped,
            form_input_auto_focus: ${h.to_js_bool(form_input_auto_focus)}
        });
    </script>

    %if not form_input_auto_focus is UNDEFINED and form_input_auto_focus:
    <script type="text/javascript">
        $(document).ready( function() {
            // Auto Focus on first item on form
            if ( $("*:focus").html() == null ) {
                $(":input:not([type=hidden]):visible:enabled:first").focus();
            }
        });
    </script>
    %endif

    ${ galaxy_client.config_sentry(app) }
    %if app.config.ga_code:
        ${ galaxy_client.config_google_analytics(app.config.ga_code) }
    %endif
    %if app.config.plausible_server and app.config.plausible_domain:
        ${ galaxy_client.config_plausible_analytics(app.config.plausible_server, app.config.plausible_domain) }
    %endif
    %if app.config.matomo_server and app.config.matomo_site_id:
        ${ galaxy_client.config_matomo_analytics(app.config.matomo_server, app.config.matomo_site_id) }
    %endif
</%def>

<%def name="js_disabled_warning()">
    <noscript>
        <div class="overlay overlay-background noscript-overlay">
            <div>
                <h3 class="title">Javascript Required for Galaxy</h3>
                <div>
                    The Galaxy analysis interface requires a browser with Javascript enabled.<br>
                    Please enable Javascript and refresh this page.
                </div>
            </div>
        </div>
    </noscript>
</%def>
