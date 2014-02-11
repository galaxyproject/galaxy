<%
    scripts = [	'jquery/jquery.js',
    			'bootstrap.js',
    			'require.js',
    			'underscore.js',
    			'backbone/backbone.js',
                'd3.js']
%>


<!DOCTYPE HTML>
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>${hda.name} | ${visualization_name}</title>

		%for v in scripts:
	        <script type="text/javascript" charset="utf-8" src="/static/scripts/libs/${v}" ></script>
	    %endfor

        ## css
        <link type="text/css" rel="Stylesheet" media="screen" href="/static/style/base.css">
        
        ## install nv.d3 module
        <script type="text/javascript" charset="utf-8" src="/plugins/visualizations/charts/static/plugins/nv.d3.js" ></script>
        <link type="text/css" rel="Stylesheet" media="screen" href="/plugins/visualizations/charts/static/plugins/nv.d3.css">

    </head>

    <body>
        <script type="text/javascript">

            // get configuration
            var config = {
                root : '/'
            };
            
            // console protection
            window.console = window.console || {
                log     : function(){},
                debug   : function(){},
                info    : function(){},
                warn    : function(){},
                error   : function(){},
                assert  : function(){}
            };

            // configure require
            require.config({
                baseUrl: config.root + "plugins/visualizations/charts/static/",
                shim: {
                    "libs/underscore": { exports: "_" },
                    "libs/backbone/backbone": { exports: "Backbone" }
                }
            });

            // application
            var app = null;
            $(function() {   
                // request application script
                require(['app'], function(App) {
                    // load options
                    var options = {
                        config  : ${h.to_json_string( config )},
                        dataset : ${h.to_json_string( trans.security.encode_dict_ids( hda.to_dict() ) )}
                    }

                    // create application
                    app = new App(options);
                    
                    // add to body
                    $('body').append(app.$el);
                });
            });

        </script>
    </body>
</html>
