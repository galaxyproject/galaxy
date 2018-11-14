<%namespace name="ie" file="ie.mako" />
<%
    # Sets ID and sets up a lot of other variables
    ie_request.load_deploy_config()

    import os

    # Add all environment variables collected from Galaxy's IE infrastructure
    # Launch the IE.

    ie_request.launch(
       image = trans.request.params.get('image_tag', None),
       additional_ids = trans.request.params.get('additional_dataset_ids', None),
    )

    # Only once the container is launched can we template our URLs. The ie_request
    # doesn't have all of the information needed until the container is running.

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


    requirejs(['galaxy.interactive_environments', 'plugin/hicbrowser'], function (IES) {
        window.IES = IES;
        load_hicexplorer(url);
    });

</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
