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
</%def>

<%def name="javascript_app()">
    <script type="text/javascript">
        var options = {
            root: '${h.url_for( "/" )}',
            session_csrf_token: '${ trans.session_csrf_token }'
        };
    </script>
</%def>

## Additional metas can be defined by templates inheriting from this one.
<%def name="metas()"></%def>
