<%
import yaml
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
    if os.path.exists(gie_config_dir(gie, 'allowed_images.yml')):
        image_file = gie_config_dir(gie, 'allowed_images.yml')
    elif os.path.exists(gie_config_dir(gie, 'allowed_images.yml.sample')):
        image_file = gie_config_dir(gie, 'allowed_images.yml.sample')
    else:
        continue

    with open(image_file, 'r') as handle:
        gie_image_map[gie] = yaml.load(handle)

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
<div class="row" style="max-width: 100%">
    <div class="col-xs-3">
    </div>
    <div class="col-xs-6">
        <div class="row">
            <h1>Galaxy Interactive Environment Launcher</h1>
            <p>
                Galaxy Interactive Environments (GIEs) launch embedded,
                dockerized versions of popular data analysis suites such as
                Jupyter and RStudio, right from within Galaxy. They allow you
                to dynamically interact with your data, right on the server. No
                more uploading and downloading between various platforms just
                to get your work done!
                <br />
                <a href="https://docs.galaxyproject.org/en/master/admin/interactive_environments.html">Admin Docs</a>
            </p>
            <form id='launcher' action="NONE" method="POST">

                <table class="table table-striped">
                    <tr>
                        <td>GIE: </td>
                        <td>
                            <span id="image_name" style="width: 400px" />
                        </td>
                    </tr>
                    <tr>
                        <td>Image: </td>
                        <td>
                            <span id="image_tag" style="width:400px" />
                            <input id="image_tag_hidden" type="hidden" name="image_tag" value="NONE" />
                            <p id="image_desc">
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td>Additional Datasets: </td>
                        <td>
                            <span id="additional_datasets" style="width:400px"></span>
                            <input id="additional_dataset_ids" name="additional_dataset_ids" type="hidden">
                        </td>
                    </tr>
                </table>
                <input type="submit" class="button" value="Launch" disabled="">
            </form>
        </div>
    </div>
    <div class="col-xs-3">
    </div>
</div>
<script type="text/javascript">
$(document).ready(function(){
    var gie_image_map = {
        % for image_name in gie_image_map.keys():
            "${image_name}": [
                % for image in gie_image_map[image_name]:
                {
                    id: "${image['image']}",
                    text: "${image['image']}",
                    extra: "${image['description']}",
                },
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

    var datasets = [
        % for dataset in hda.history.datasets:
            % if not dataset.deleted and dataset.dataset_id !=  hda.dataset_id:
            { id: "${ trans.security.encode_id(dataset.dataset_id) }", text: "${ dataset.id } : ${ dataset.name }" },
            % endif
        % endfor
    ]

    $("#additional_datasets").select2({
        multiple: true,
        data: datasets
    }).on('change', function(e){
        $("#additional_dataset_ids").val($("#additional_datasets").val())
    })

    function formatter(v){
        if(!v.id) return v.text;
        return "<b>" + v.id + "</b><p>" + v.extra + "</p>"
    }

    $('#image_name').select2({
        placeholder: "Select Image",
        data: images
    }).on('change', function(e){
        // Get the versions for this image name
        image_versions = gie_image_map[e.val]
        // Update the action
        $("#launcher").attr("action", e.val + '?dataset_id=${ trans.security.encode_id(hda.dataset_id) }')
        // Update the hidden input
        $("#image_name_hidden").val(e.val)

        // Create our select2 appropriately
        image_tags = $("#image_tag").select2({
            placholder: "Image Version",
            formatResult: formatter,
            formatSelection: formatter,
            escapeMarkup: function(m) { return m; },
            data: image_versions
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
