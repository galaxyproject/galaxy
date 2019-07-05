<%namespace name="ie" file="ie.mako" />
<%
import random
import string
# Sets ID and sets up a lot of other variables
ie_request.load_deploy_config()

# get an API key for AskOmics
askomics_api_key = ie_request.notebook_pw

# Get ids of selected datasets
additional_ids = trans.request.params.get('additional_dataset_ids', None)
if not additional_ids:
    additional_ids = str(trans.security.encode_id( hda.id ) )
else:
    additional_ids += "," + trans.security.encode_id( hda.id )

# Launch the IE. This builds and runs the docker command in the background.
ie_request.launch(
    additional_ids=additional_ids if ie_request.use_volumes else None,
    env_override={
        'ASKO_load_url': 'http://localhost:6543',
        'ASKOMICS_API_KEY': askomics_api_key,
        'ASKO_files_dir': '/tmp/askomics-ie',
        'VIRT_Parameters_NumberOfBuffers': 10000,  # see https://github.com/xgaia/askomics-docker-compose/tree/master/virtuoso#virtuoso for this values
        'VIRT_Parameters_MaxDirtyBuffers': 6000
    }
)

# Only once the container is launched can we template our URLs. The ie_request
# doesn't have all of the information needed until the container is running.
url = ie_request.url_template('${PROXY_URL}/login_api_gie?key=' + askomics_api_key)
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
requirejs(['galaxy.interactive_environments', 'plugin/askomics'], function(IES){
    window.IES = IES;
    load_askomics(url);
});
</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
