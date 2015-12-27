<%
import os

def detect_gie_path(path):
    if ',' in path:
        # Then a GIE path is there. Otherwise just visualizations
        # This is ugly code due to the ugliness of the code in config.py
        viz_dir, gie_dir = path.split(',', 1)
        return gie_dir
    else:
        # No GIE path supplied (see config.py for why)
        # So we can basically quit here.
        return None


gie_dir = detect_gie_path(trans.app.config.visualization_plugins_directory)
if gie_dir is None:
    raise Exception("No Galaxy Interactive Environments configured (or configuration issue). Contact your Galaxy Admin")

def gie_config_dir(name, *args):
    nargs = [gie_dir, name, 'config']
    if len(args) > 0:
        nargs += args
    return os.path.join(*nargs)

gie_list = os.listdir(gie_dir)
gie_list.remove('interactive_environments.dtd')
gie_list.remove('common')

gie_image_map = {}

# TODO: memoize/calc once on startup
for gie in gie_list:
    if os.path.exists(gie_config_dir(gie, 'allowed_images.ini')):
        image_file = gie_config_dir(gie, 'allowed_images.ini')
    elif os.path.exists(gie_config_dir(gie, 'allowed_images.ini.sample')):
        image_file = gie_config_dir(gie, 'allowed_images.ini.sample')
    else:
        continue

    with open(image_file, 'r') as handle:
        gie_image_map[gie] = [image.strip() for image in handle.readlines() if not image.startswith('#')]

%>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, minimum-scale=1.0, maximum-scale=1.0">

    <title>Galaxy Interactive Environment Launcher</title>

    ## shared css
    ${h.css( 'base' )}

    ${h.js( 'libs/jquery/jquery',
            'libs/jquery/select2',
            'libs/bootstrap',
            'libs/underscore',
            'libs/backbone/backbone',
            'libs/d3',
            'libs/require')}
</head>
<body>
<div class="content">
    <h1>Galaxy Interactive Environment Launcher</h1>
    <form id='launcher' action="NONE" method="GET">
        <b>GIE: </b>
        <span id="image_name" style="min-width:200px">
        </span>
        <br/>
        <br/>
        <b>Image: </b>
        <span id="image_tag" style="min-width:400px">
        <input id="image_tag_hidden" type="hidden" name="image_tag" value="NONE" />
        </span>
        <br/>
        <br/>

        <b>Datasets<b>
        <br/>
        <input type="hidden" name="dataset_id" value="${ trans.security.encode_id(hda.dataset_id) }" />
        <br/>

    % for dataset in hda.history.datasets:
        % if not dataset.deleted:
        <label>
            <input
                type="checkbox"
                name="additional_dataset_ids"
                value="${ trans.security.encode_id(dataset.dataset_id) }"
                %if dataset.dataset_id == hda.dataset_id:
                disabled
                checked=true
                %endif
            >
            ${ dataset.id }: ${ dataset.name }
        </label><br/>
        % endif
    % endfor

        <br/>
        <br/>
        <input type="submit" class="button" value="Launch"  disabled>
    </form>


</div>
<script type="text/javascript">
    $(document).ready(function(){
    var gie_image_map = {
        % for image_name in gie_image_map.keys():
            "${image_name}": [
                % for image_tag in gie_image_map[image_name]:
                    "${image_tag}",
                % endfor
            ],
        % endfor
    }

    var images = [
        % for image_name in gie_image_map.keys():
        {
            id: "${image_name}",
            text: "${image_name}"
        },
        % endfor
    ]

    $('#image_name').select2({
        placeholder: "Select Image",
        data: images
    }).on('change', function(e){
        // Get the versions for this image name
        image_versions = gie_image_map[e.val]
        // Update the action
        $("#launcher").attr("action", e.val)
        // Update the hidden input
        $("#image_name_hidden").val(e.val)

        // Create our select2 appropriately
        image_tags = $("#image_tag").select2({
            placholder: "Image Version",
            data: $.map(image_versions, function(n){
                return {id: n, text: n};
            })
        }).on('change', function(e2){
            // Inner actions, update the hidden input
            $("#image_tag_hidden").val(e2.val)
            // Enable the button
            $('input[type="submit"]').removeAttr('disabled');

        })
    })


    })
</script>
</body>
</html>
