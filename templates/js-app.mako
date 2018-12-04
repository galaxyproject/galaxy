<%namespace name="galaxy_client" file="/galaxy_client_app.mako" />
<!DOCTYPE HTML>
<html>
    <!--js-app.mako-->
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ## For mobile browsers, don't scale up
        <meta name="viewport" content="maximum-scale=1.0">
        ## Force IE to standards mode, and prefer Google Chrome Frame if the user has already installed it
        <meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1">

        <title>
            Galaxy
            %if app.config.brand:
            | ${app.config.brand}
            %endif
        </title>

        ## relative href for site root
        ## TODO: just use <base>, that's what it's for
        <link rel="index" href="${ h.url_for( '/' ) }"/>

        ${ stylesheets() }

    </head>
    <body scroll="no" class="full-content">

        <%block name="js_disabled_warning">
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
        </%block>

        ${ javascript() }

    </body>
</html>

## Default stylesheets
<%def name="stylesheets()">
    ${h.css(
        'jquery-ui/smoothness/jquery-ui',
        'bootstrap-tour',
        'base',
    )}
</%def>

<%def name="javascript()">
    <!-- js-app.mako javascript -->
    ${ h.js(
        'bundled/libs.chunk',
        'bundled/base.chunk'
    )}
    ${ self.javascript_entry() }
    ${ self.javascript_app() }
</%def>

<%def name="javascript_entry()">
    <!-- js-app.mako javascript_entry -->
    ${ h.js('bundled/' + js_app_name + '.bundled')}
</%def>

<%def name="javascript_app()">

    <!-- js-app.mako javascript_app -->
    <script type="text/javascript">

        // js-app.mako
        var options = ${ h.dumps( options ) };
        var bootstrapped = ${ h.dumps( bootstrapped ) };

        config.setConfig({
            options: options,
            bootstrapped: bootstrapped,
            form_input_auto_focus: ${h.to_js_bool(form_input_auto_focus)}
        });
        
    </script>

    ${ galaxy_client.config_sentry(app)}
    ${ galaxy_client.config_google_analytics(app)}
</%def>