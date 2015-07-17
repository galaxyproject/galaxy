<!DOCTYPE HTML>
<html>
    <!--test.mako-->
    <head>
        <title>Test</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ## For mobile browsers, don't scale up
        <meta name="viewport" content="maximum-scale=1.0">
        ## Force IE to standards mode, and prefer Google Chrome Frame if the user has already installed it
        <meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1">
        ${h.css(
            'base',
            'jquery.rating'
        )}
        <script type="text/javascript">
            window.galaxy_config = {
                root: '${h.url_for( "/" )}'
            };
        </script>
        <script type="text/javascript" src="static/scripts/bundled/common.js"></script>
    </head>

    <body>
        <script type="text/javascript" src="static/scripts/bundled/${js_app_name}.bundled.js"></script>
        <script type="text/javascript">
            ${js_app_entry_fn}(
                ${ h.dumps( options ) },
                ${ h.dumps( bootstrapped ) }
            );
        </script>
    </body>
</html>
