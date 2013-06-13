<% _=n_ %>
<!DOCTYPE HTML>
<html>
    <!--base.mako-->
    <head>
        <title>${self.title()}</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ${self.metas()}
        ${self.stylesheets()}
        ${self.javascripts()}
    </head>
    <body>
        ${next.body()}
    </body>
</html>

## Default title
<%def name="title()"></%def>

## Default stylesheets
<%def name="stylesheets()">
    ${h.css('base')}
</%def>

## Default javascripts
<%def name="javascripts()">
    
    ## Send errors to Sntry server if configured
    %if app.config.sentry_dsn:
        ${h.js( "libs/tracekit", "libs/raven" )}
        <script>
            Raven.config('${app.config.sentry_dsn_public}').install();
            %if trans.user:
                Raven.setUser( { email: "${trans.user.email}" } );
            %endif
        </script>
    %endif

    ${h.js(
        "libs/jquery/jquery",
        "libs/jquery/select2",
        "libs/json2",
        "libs/bootstrap",
        "libs/underscore",
        "libs/backbone/backbone",
        "libs/backbone/backbone-relational",
        "libs/handlebars.runtime",
        "galaxy.base"
    )}

    ${h.templates(
        "template-popupmenu-menu"
    )}

    ${h.js(
        "mvc/ui"
    )}

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

        // Set up needed paths.
        var galaxy_paths = new GalaxyPaths({
            root_path: '${h.url_for( "/" )}',
            image_path: '${h.url_for( "/static/images" )}'
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

</%def>

## Additional metas can be defined by templates inheriting from this one.
<%def name="metas()"></%def>
