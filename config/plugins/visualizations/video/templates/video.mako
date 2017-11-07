<%
    default_title = "Playing '" + hda.name + "'"

    # Use root for resource loading.
    root = h.url_for( '/' )
    static = h.url_for(root + 'plugins/visualizations/video/static/')

    # TODO: allow other filetypes
    dataset_location = h.url_for( root + 'datasets/') + trans.security.encode_id( hda.id ) + "/display/?preview=True&f=.mp4"


    video_x = hda.metadata.resolution_x
    video_y = hda.metadata.resolution_y

    min_width = 600

    # If the video is skinnier than min_width px, bump to a minimum of min_width and
    # then scale y appropriately to retain aspect ratio
    # If we do not do this, controls will be hidden on small videos
    if int(hda.metadata.resolution_x) < int(min_width):
        video_x = 600
        video_y = (float(min_width)/float(hda.metadata.resolution_x)) * float(hda.metadata.resolution_y)
%>
<!DOCTYPE HTML>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>${title or default_title} | ${visualization_display_name}</title>

${h.stylesheet_link( root + 'plugins/visualizations/video/static/video-js.css' )}
${h.js( 'libs/jquery/jquery' )}
${h.javascript_link( root + 'plugins/visualizations/video/static/video.js' )}

<script>
    videojs.options.flash.swf = "${h.url_for(static + 'video-js.swf')}"
</script>
<script src="${h.url_for(static + 'video-speed.js')}"></script>
<script src="${h.url_for(static + 'video-framebyframe.js')}"></script>
</head>
<body>

    <video id="vid" class="video-js vjs-default-skin" controls preload="none" width="${ video_x }" height="${ video_y }" data-setup="{}">
        <source src="${dataset_location}" type='video/mp4' />
        <p class="vjs-no-js">To view this video please enable JavaScript, and consider upgrading to a web browser that <a href="http://videojs.com/html5-video-support/" target="_blank">supports HTML5 video</a></p>
  </video>

  <script type='text/javascript'>
    var video = videojs("vid", {
      controls: true,
      autoplay: false,
      preload: 'auto',
      plugins: {
        speed: [
          { text: '.25x', rate: 0.25 },
          { text: '.5x', rate: 0.5 },
          { text: '1x', rate: 1, selected: true },
          { text: '2x', rate: 2 },
        ],
        framebyframe: {
          fps: ${ hda.metadata.fps },
          steps: [
            { text: '-5', step: -5 },
            { text: '-1', step: -1 },
            { text: '+1', step: 1 },
            { text: '+5', step: 5 },
          ]
        }
      }
    });
  </script>

</body>
