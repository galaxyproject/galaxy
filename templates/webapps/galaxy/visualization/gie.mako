<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="visualization"
    self.message_box_visible=False
%>
</%def>

<%def name="center_panel()">

    ## ${h.js('libs/jquery/select2')}

    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
            <div class="col-md-8 col-md-offset 2 col-xs-12">
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
                    <form id='launcher' action="NONE" method="GET">

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
                                <td>Datasets: </td>
                                <td>
                                    <span id="additional_datasets" style="width:400px"></span>
                                    <input id="dataset_id" name="dataset_id" type="hidden">
                                    <input id="additional_dataset_ids" name="additional_dataset_ids" type="hidden">
                                </td>
                            </tr>
                        </table>
                        <input type="submit" class="button" value="Launch" disabled="">
                    </form>
                </div>
            </div>


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
                    extra: "${image['description'].replace('\n', ' ')}",
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
        % for hda in history.visible_datasets[::-1]:
            { id: "${ trans.security.encode_id(hda.id) }", text: "${ hda.hid } : ${ hda.name }" },
        % endfor
    ]

    $("#additional_datasets").select2({
        multiple: true,
        data: datasets
    }).on('change', function(e){
        ds_ids = $("#additional_datasets").val().split(',');
        if(ds_ids.length < 1){
            $('input[type="submit"]').attr('disabled', '');
        } else {
            $("#dataset_id").val(ds_ids[0])

            // In a perfect world the controller would just support a single
            // parameter passing a list of dataset IDs.
            //
            // We aren't in that world (yet).
            if(ds_ids.length > 1){
                $("#additional_dataset_ids").val(ds_ids.slice(1).join(","))
            }else{
                $("#additional_dataset_ids").val("")
            }
            $('input[type="submit"]').removeAttr('disabled');
        }
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
        $("#launcher").attr("action", "../plugins/interactive_environments/" + e.val + "/show")
        // Update the hidden input
        $("#image_name_hidden").val(e.val)
        // Set disabled if they switch image family without updating image.
        $('input[type="submit"]').attr('disabled', '');

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
            if($("additional_datasets").length > 0){
                $('input[type="submit"]').removeAttr('disabled');
            }
        })
    })
})
</script>
</%def>
