<html>
    <head>
        <meta http-equiv="refresh" content="1;url=${redirect_url}">
    </head>
    <body>
        %if trans.app.sequencer_actions_registry.browser_login:
            <iframe name="login" id="login" frameborder="0" style="position: absolute; width: 0%; height: 0%;" src="${h.url_for( controller="common", action="login" )}"></iframe>
        %endif
    </body>
</html>
