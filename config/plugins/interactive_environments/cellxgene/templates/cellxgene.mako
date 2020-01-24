<%namespace name="ie" file="ie.mako" />
<%
    ie_request.load_deploy_config()

    ie_request.launch(
        image = trans.request.params.get('image_tag', None),
        env_override={
            'dataset_hid': hda.hid
        }
    )

    url = ie_request.url_template('${PROXY_URL}')
%>
<html>
<head>
    ${ ie.load_default_js() }
</head>
<body>
<script type="text/javascript">

    ${ ie.default_javascript_variables() }
    var url = '${ url }';

    $( document ).ready(function() {
        IES.keepAlive(url);
        IES.test_ie_availability(url, function() {
            IES.append_notebook(url);
        });
    });

</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
