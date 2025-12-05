<%namespace name="galaxy_client" file="/galaxy_client_app.mako" />
<% self.js_app = None %>

<% _=n_ %>
<!DOCTYPE HTML>
<html>
    <!--base.mako-->
    ${self.init()}
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />

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
</%def>

## Default javascripts
<%def name="javascripts()">
    ${self.javascript_entry()}
</%def>

<%def name="javascript_entry()">
    ${h.dist_js('toolshed.bundled')}
</%def>

<%def name="javascript_app()">

    ${ galaxy_client.load( app=self.js_app ) }

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
