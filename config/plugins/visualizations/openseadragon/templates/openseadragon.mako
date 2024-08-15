<%
    default_title = "OpenSeadragon Viewer"

    # Use root for resource loading.
    root = h.url_for("/static/")
    app_root = root + "plugins/visualizations/openseadragon/static/"
%>

<!DOCTYPE HTML>
<html>
    <head>
        <!-- OpenSeadragon Viewer is a web-based viewer for high-resolution zoomable images. -->
        <title>${hda.name | h} | ${visualization_name}</title>

        ## external scripts
        ${h.javascript_link(app_root + "dist/openseadragon.min.js")}
    </head>
    <body>
        <!-- Div which will hold the Output -->
        <div id="seadragon-viewer" style="width: 800px; height: 600px;"></div>
        <script type="text/javascript">

            // Galaxy hda stuff.
            const hda_ext = "${hda.ext}";
            const hda_id = "${trans.security.encode_id(hda.id)}";
            // OpenSeadragon stuff.
            const dzi_image_url = "${h.url_for(controller='/datasets', action='index')}/" + hda_id + "/display/";
            const viewer_id = "seadragon-viewer";
            const prefixUrl = "//openseadragon.github.io/openseadragon/images/";
            const simple_image_url = "${h.url_for(controller='/datasets', action='index')}/" + hda_id + "/display";
            const xmlns = "http://schemas.microsoft.com/deepzoom/2008";
            const image_types = ["gif", "jpg", "png", "tiff"];

            if (image_types.includes(hda_ext)) {
                var viewer = OpenSeadragon({
                    id: viewer_id,
                    prefixUrl: prefixUrl,
                    tileSources: {
                        type: "image",
                        url:  simple_image_url
                    }
                });
            } else if (hda_ext == 'dzi') {
                var viewer = OpenSeadragon({
                    id: viewer_id,
                    prefixUrl: prefixUrl,
                    tileSources:   {
                        Image: {
                            xmlns:    xmlns,
                            Url:      dzi_image_url,
                            Format:   "${hda.metadata.format}",
                            Overlap:  "${hda.metadata.overlap}",
                            TileSize: "${hda.metadata.tile_size}",
                            Size: {
                                Height: "${hda.metadata.height}",
                                Width:  "${hda.metadata.width}"
                            }
                        }
                    }
                });
            }
        </script>
    </body>
</html>

