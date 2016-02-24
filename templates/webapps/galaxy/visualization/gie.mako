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

    ${h.js('libs/jquery/select2')}

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
        % for dataset in history.datasets:
            { id: "${ trans.security.encode_id(dataset.dataset_id) }", text: "${ dataset.id } : ${ dataset.name }" },
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
        $("#launcher").attr("action", e.val)
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
</%def>
