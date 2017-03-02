<%namespace name="ie" file="ie.mako" />
<%
# Sets ID and sets up a lot of other variables
ie_request.load_deploy_config()

# Define a volume that will be mounted into the container.
# This is a useful way to provide access to large files in the container,
# if the user knows ahead of time that they will need it.
#user_file = ie_request.volume(
#    hda.file_name, '/import/file.dat', how='ro')

# Launch the IE. This builds and runs the docker command in the background.
ie_request.launch(
    env_override={
        'dataset_hid': hda.hid
    }
)

# Only once the container is launched can we template our URLs. The ie_request
# doesn't have all of the information needed until the container is running.
url = ie_request.url_template('${PROXY_URL}/ethercalc/')
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
requirejs(['interactive_environments', 'plugin/ethercalc'], function(){
    keep_alive(url);
});

requirejs(['interactive_environments', 'plugin/ethercalc'], function(){
    load_notebook(url);
});
</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
