<%
    default_title = "JS Editor"

    # Use root for resource loading.
    root = h.url_for( '/static/' )
    app_root    = root + "plugins/visualizations/editor/static/"
%>
## ----------------------------------------------------------------------------

<!DOCTYPE HTML>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <title> ${visualization_name}</title>
    ${h.javascript_link( app_root + "script.js" )}
    ${h.stylesheet_link( app_root + "main.css" )}
</head>

<body>
<div id="editor">
</div>
<button onclick="exportData()" class="transparent_btn blue" id="export-btn">export</button>
<script>
    function httpGet(theUrl) {
        var xmlHttp = new XMLHttpRequest();
        xmlHttp.open("GET", theUrl, false);
        xmlHttp.send(null);
        return xmlHttp.responseText;
    }

    function exportData() {
        ## Prepare data for export
        const upload_data = {
            tool_id: "upload1",
            history_id: "${trans.security.encode_id(hda.history_id)}",
            inputs: {
                "file_count": 1,
                "file_type": "auto",
                "files_0|file_type": "auto",
                "files_0|url_paste": editor.getValue(),
                "files_0|NAME": "${ hda.name } (modified)"
            }
        };
        ## upload data
        const request = new XMLHttpRequest();
        request.open("POST", "/api/tools");
        request.setRequestHeader("Content-Type", "application/json");
        request.send(JSON.stringify(upload_data));
        request.onreadystatechange = function () {
            if (request.readyState === XMLHttpRequest.DONE) {
                var status = request.status;
                if (status === 0 || (200 >= status && status < 400)) {
                    top.location = "/"
                } else {
                    alert("something went wrong, please contact us!");
                }
            }
        };
    }

    const hda_id = '${ trans.security.encode_id( hda.id ) }';

    const ajax_url = "${h.url_for( controller='/datasets', action='index')}/" + hda_id + "/display";
    const data = httpGet(ajax_url);
    document.getElementById("editor").innerHTML = data;
    var editor = ace.edit("editor", {
        mode: "ace/mode/powershell",
        theme: "ace/theme/textmate"
    });
</script>
</body>
</html>
