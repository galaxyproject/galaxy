<%namespace name="ie" file="ie.mako" />
<%
    ie_request.load_deploy_config()

    # Make the dataset available inside the container
    data_file = ie_request.volume('/input/file.' + hda.ext, hda.file_name, mode='ro')

    ie_request.launch(
       image = trans.request.params.get('image_tag', None),
       volumes = [data_file]
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
    ${ ie.plugin_require_config() }

    requirejs(['galaxy.interactive_environments'], function (IES) {
        $( document ).ready(function() {
            IES.test_ie_availability(url, function() {
                IES.append_notebook(url);
            });
        });
    });

</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
