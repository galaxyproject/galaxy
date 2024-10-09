<!DOCTYPE HTML>
<%
    import os

    root = h.url_for('', qualified=True)

    hdadict = trans.security.encode_dict_ids( hda.to_dict() )
    file_url = os.path.join(root, 'datasets', hdadict['id'], "display?to_ext="+hda.ext)

    app_root = root + '/static/plugins/visualizations/fits_graph_viewer/static/'
%>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FITS Graph Viewer</title>
</head>
<body>

    <main>
        <section>
            <div id="astrovisdiv"></div>
        </section>
    </main>

    <script>
        let file_url = '${file_url}';
    </script>
    <script src="dist/bundle.js"></script>

    ${h.javascript_link( app_root + 'fits_graph_viewer.js' )}

</body>
</html>
