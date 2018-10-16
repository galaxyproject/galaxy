<%
    app_root = h.url_for("/static/plugins/visualizations/annotate_image/static/")
%>

<!DOCTYPE html>
<html>
<head lang="en">
    <meta name="viewport" content="width=device-width,initial-scale=1,minimum-scale=1,maximum-scale=1"/>
    <title>Annotate image</title>
    ${h.javascript_link( app_root +  "js/jquery-1.9.1.min.js" )}
    ${h.javascript_link( app_root +  "js/paper-full.min.js" )}
    ${h.stylesheet_link(app_root + 'css/image-markup.css' )}
    ${h.stylesheet_link(app_root + 'css/jquery.contextMenu.css' )}

</head>
<body class="body-annotate-image">
    <div>
        <div class="img-container"><img id='image-annotate' src="" /></div>
    </div>
    ${h.javascript_link( app_root +  "js/CommandManager.js" )}
    ${h.javascript_link( app_root +  "js/jquery.contextMenu.js" )}
    ${h.javascript_link( app_root +  "js/jquery.ui.position.js" )}
    ${h.javascript_link( app_root +  "js/image-markup.js" )}
    <script>
        $(document).ready(function () {
            var datasetId = '${trans.security.encode_id(hda.id)}',
                url = '/api/datasets/' + datasetId,
                image = $('.img-container img');
            $.get(url, function(response) {
                image.attr('src', response.download_url);
                image.on('load', function(){
                    image.imageMarkup({ color: 'red', width: 4, opacity: 0.5, img_width: $(this).width(), img_height: $(this).height()  });
                });
                
            });
        });
    </script>
    
                
</body>
</html>

