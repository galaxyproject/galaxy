<% _=n_ %>
<!DOCTYPE HTML>
<html>
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
</%def>

## Additional metas can be defined by templates inheriting from this one.
<%def name="metas()"></%def>
