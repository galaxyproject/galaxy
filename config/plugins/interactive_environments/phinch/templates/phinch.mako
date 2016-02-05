<%namespace name="ie" file="ie.mako" />
<%

import os

# Sets ID and sets up a lot of other variables
ie_request.load_deploy_config()


# Launch the IE. This builds and runs the docker command in the background.
ie_request.launch(env_override={
    'dataset_hid': hda.hid,
    'dataset_filename': hda.file_name
})

# Only once the container is launched can we template our URLs. The ie_request
# doesn't have all of the information needed until the container is running.
url = ie_request.url_template('${PROXY_URL}/phinch/')


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

// Keep container running
requirejs(['interactive_environments', 'plugin/phinch'], function(){
    keep_alive(url);
});

// Load notebook
requirejs(['interactive_environments', 'plugin/phinch'], function(){
    load_notebook(url);
});

</script>
<div id="main" style="width: 100%; height: 100%; overflow:hidden;">
</div>
</body>
</html>
