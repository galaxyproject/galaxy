<%
    import pprint
    print js_app_name
    print js_app_entry_fn
    printable = dict( options[ 'config' ] )
    printable.pop( 'toolbox', None )
    printable.pop( 'toolbox_in_panel', None )
    pprint.pprint( printable )
    ## pprint.pprint( bootstrapped )
%>

<!DOCTYPE HTML>
<html>
    <!--js-app.mako-->
    <head>
        <title>Galaxy</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ## For mobile browsers, don't scale up
        <meta name="viewport" content="maximum-scale=1.0">
        ## Force IE to standards mode, and prefer Google Chrome Frame if the user has already installed it
        <meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1">
        ## TODO: use loaders to move everything but the essentials below the fold
        ${ h.css(
            'base',
            'jquery.rating'
            'jquery-ui/smoothness/jquery-ui'
        )}
        ${ page_setup() }
    </head>

    <body>
        <script type="text/javascript" src="/static/scripts/bundled/common.js"></script>
        ## TODO: remove when all libs are required directly in modules
        <script type="text/javascript" src="/static/scripts/bundled/libs.bundled.js"></script>
        <script type="text/javascript" src="/static/scripts/bundled/galaxy.bundled.js"></script>
        <script type="text/javascript">
            window.Galaxy = new GalaxyApp(
                ${ h.dumps( options ) },
                ${ h.dumps( bootstrapped ) }
            );
            // TODO: find and replace with Galaxy.root
            window.galaxy_config = { root: Galaxy.options.root };
        </script>
        <script type="text/javascript" src="/static/scripts/bundled/${js_app_name}.bundled.js"></script>
        <script type="text/javascript">
            // TODO: should *inherit* from GalaxyApp - then remove above and galaxy.bundled.js
            ${js_app_entry_fn}(
                ${ h.dumps( options ) },
                ${ h.dumps( bootstrapped ) }
            );
        </script>
    </body>
</html>

## ============================================================================
<%def name="page_setup()">
    ## Send errors to Sntry server if configured
    %if app.config.sentry_dsn:
    ${h.js( "libs/tracekit", "libs/raven" )}
    <script>
        Raven.config('${app.config.sentry_dsn_public}').install();
        %if trans.user:
            Raven.setUser( { email: "${trans.user.email|h}" } );
        %endif
    </script>
    %endif

    <script type="text/javascript">
        ## console protection
        window.console = window.console || {
            log     : function(){},
            debug   : function(){},
            info    : function(){},
            warn    : function(){},
            error   : function(){},
            assert  : function(){}
        };
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

    %if app.config.ga_code:
    <script type="text/javascript">
        (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
        (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
        m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
        })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
        ga('create', '${app.config.ga_code}', 'auto');
        ga('send', 'pageview');
    </script>
    %endif
</%def>
