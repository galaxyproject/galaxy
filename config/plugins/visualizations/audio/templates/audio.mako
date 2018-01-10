<%
    default_title = "Playing '" + wavfile.name + "'"

    # Use root for resource loading.
    root = h.url_for( '/' )
    static = h.url_for(root + 'plugins/visualizations/video/static/')

    # TODO: allow other filetypes
    dataset_location = h.url_for( root + 'datasets/') + trans.security.encode_id( wavfile.id ) + "/display/?preview=True"

%>
<!DOCTYPE HTML>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>${title or default_title} | ${visualization_display_name}</title>
</head>
<body>
    <h1>${wavfile.name}</h1>

    <div>
    <audio controls='controls'>
        Your browser does not support the <code>audio</code> element.
        <source src="${dataset_location}" type="audio/wav" />
    </audio>
    </div>

</body>
