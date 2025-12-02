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

        <script type="text/javascript">
            const session_csrf_token = "${ trans.session_csrf_token }";
        </script>
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

        %if app.config.ga_code:
            ${ config_google_analytics(app.config.ga_code) }
        %endif
        %if app.config.plausible_server and app.config.plausible_domain:
            ${ config_plausible_analytics(app.config.plausible_server, app.config.plausible_domain) }
        %endif
        %if app.config.matomo_server and app.config.matomo_site_id:
            ${ config_matomo_analytics(app.config.matomo_server, app.config.matomo_site_id) }
        %endif
    </body>
</html>

<%def name="config_google_analytics(ga_code)">
    <script>
        console.log("config_google_analytics ga_code:", '${ga_code}');
        %if ga_code:
            (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
            (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
            m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
            })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
            ga('create', '${ga_code}', 'auto');
            ga('send', 'pageview');
        %else:
            console.warn("Missing google analytics code");
        %endif
    </script>
</%def>

<%def name="config_plausible_analytics(plausible_server, plausible_domain)">
    %if plausible_server and plausible_domain:
        <script async defer data-domain="${plausible_domain}" src="${plausible_server}/js/script.js"></script>
        <script>window.plausible = window.plausible || function() { (window.plausible.q = window.plausible.q || []).push(arguments) }</script>
    %else:
        <script>
            console.warn("Missing plausible server or plausible domain");
        </script>
    %endif
</%def>

<%def name="config_matomo_analytics(matomo_server, matomo_site_id)">
    <script type="text/javascript">
        console.log("config_matomo_analytics matomo_server:", '${matomo_server}');
        console.log("config_matomo_analytics matomo_site_id:", '${matomo_site_id}')
        %if matomo_server and matomo_site_id:
            var _paq = window._paq = window._paq || [];
            /* tracker methods like "setCustomDimension" should be called before "trackPageView" */
            _paq.push(['trackPageView']);
            _paq.push(['enableLinkTracking']);
            (function () {
                var u = "${matomo_server}/";
                _paq.push(['setTrackerUrl', u + 'matomo.php']);
                _paq.push(['setSiteId', '${matomo_site_id}']);
                var d = document;
                var g = d.createElement('script');
                var s = d.getElementsByTagName('script')[0];
                g.type = 'text/javascript';
                g.async = true;
                g.src = u + 'matomo.js';
                s.parentNode.insertBefore(g, s);
            })();
        %else:
            console.warn("Missing matomo server or matomo site id");
        %endif
    </script>
</%def>
