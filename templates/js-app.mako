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

        <!-- Set relative href for site root -->
        <link rel="index" href="${ h.url_for( '/' ) }"/>

        <!-- Load stylesheets -->
        ${ h.dist_css('base')}
        ${ h.css('jquery-ui/smoothness/jquery-ui')}
    </head>

    <body scroll="no" class="full-content">
        <!-- Provide mount point for application -->
        <main>
            <div id="app"></div>
        </main>
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

        <!-- Load application -->
        ${ h.dist_js('libs.bundled', '%s.bundled' % js_app_name )}
    </body>
</html>
