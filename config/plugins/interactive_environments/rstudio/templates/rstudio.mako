<%namespace name="ie" file="ie.mako"/>

<%

# Sets ID and sets up a lot of other variables
ie_request.load_deploy_config()
ie_request.attr.docker_port = 80

additional_ids = trans.request.params.get('additional_dataset_ids', None)
if not additional_ids:
    additional_ids = str(trans.security.encode_id( hda.id ) )
else:
    additional_ids += "," + trans.security.encode_id( hda.id )

DATASET_HID = hda.hid

# Add all environment variables collected from Galaxy's IE infrastructure
ie_request.launch(
    image=trans.request.params.get('image_tag', None)
)

## General IE specific
# Access URLs for the notebook from within galaxy.
notebook_access_url = ie_request.url_template('${PROXY_URL}/rstudio/')

%>
<html>
<head>
${ ie.load_default_js() }
${ ie.load_default_app() }
</head>
<body style="margin: 0px">

<script type="text/javascript">
${ ie.default_javascript_variables() }
var notebook_access_url = '${ notebook_access_url }';
IES.load_when_ready(ie_readiness_url, function(){
    load_notebook(notebook_access_url);
});
</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
