<!DOCTYPE HTML>
<%
    import os

    root = h.url_for('', qualified=True)

    hdadict = trans.security.encode_dict_ids( hda.to_dict() )
    file_url = os.path.join(root, 'datasets', hdadict['id'], "display?to_ext="+hda.ext)

    app_root = root + '/static/plugins/visualizations/fits_image_viewer/static/'
%>

<html>
    <head>
        ${h.stylesheet_link( app_root + 'style.css' )}
    </head>
    <body>
        <div id="div_title"><span id="span_plugin_name">FITS aladin viewer</span> : <span id="span_file_name">${hda.name | h}</span></div>
        <div id="aladin-lite-div"></div>

        <script>
            const fileUrl = '${file_url}';
            const appRoot = '${app_root}'
            const aladinLiteCDNUrl = "https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js"
            const aladinLiteScriptLocation = "dist/aladin-lite-galaxy/aladin.js"
            const aladinLiteScriptAlternativeLocation = "dist/aladin.js"
        </script>

        ${h.javascript_link( app_root + 'script.js' )}
    </body>
</html>
