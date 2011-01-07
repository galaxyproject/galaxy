<html>
    <body>
        <iframe name="trash" frameborder="0" style="position: absolute; width: 0%; height: 0%;" src="${h.url_for( controller="common", action="empty_page" )}"></iframe>
        <form id="logOnForm" name="logOnForm" method="post" action="${trans.app.sequencer_actions_registry.browser_login}" target="trash">
        </form>
        <script type="text/javascript">
            document.logOnForm.submit();
        </script>
    </body>
</html>
