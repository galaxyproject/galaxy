
<%
    dom_id = '-'.join([ visualization_name, query.get( 'dataset_id' ) ])
    root        = h.url_for( "/" )
    app_root    = root + "plugins/visualizations/mrheatmap/static/"
    canvasSize = 500
    viewerSize = 500
    mincolor = '#0000ff'
    midcolor = '#ffffff'
    maxcolor = '#ff0000'
%>

## ----------------------------------------------------------------------------
<!DOCTYPE HTML>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <title>${ visualization_display_name }</title>
    ${h.js(
        'libs/jquery/jquery',
        'libs/underscore',
        'libs/backbone/backbone',
        'libs/require',
        'libs/farbtastic',
    )}

    ${ h.css( 'base' ) }
    <link rel="stylesheet" type="text/css" href="/plugins/visualizations/mrheatmap/static/heatmap.css">
    ##<script type="text/javascript" src="https://rawgit.com/mongodb/js-bson/master/browser_build/bson.js"></script>
</head>


## ----------------------------------------------------------------------------
<body>

    <div id="mrheatmap" class="container" unselectable="on">
        <div id='mrh-mask' class='mrh-mask' unselectable="on"></div>
        <div id='mrh-settings' class='mrh-settings' unselectable='on'>
            <div id='mrh-settings-header'>
                <div id='mrh-settings-close'></div>
            </div>
            <div id='mrh-settings-body'>
                <div class='mrh-settings-label-box'>Minimum Score</div>
                <div class='mrh-color-spacer'></div>
                <div id='mrh-mincolor-score' class='mrh-score-box mrh-score-box-editable'>-10.0</div>
                <div class='mrh-settings-label-box'>Middle Score</div>
                <div class='mrh-color-spacer'></div>
                <div id='mrh-midcolor-score' class='mrh-score-box'>0.0</div>
                <div class='mrh-settings-label-box'>Maximum Score</div>
                <div class='mrh-color-spacer'></div>
                <div id='mrh-maxcolor-score' class='mrh-score-box mrh-score-box-editable'>10.0</div>
                <div id='mrh-mincolor-box' class='mrh-color-box'></div>
                <div id='mrh-midcolor-box' class='mrh-color-box'></div>
                <div id='mrh-maxcolor-box' class='mrh-color-box'></div>
            </div>
        </div>
        <div id="mrh-top" class="mrh-top" unselectable="on">
            <div id="mrh-label" class="mrh-label" unselectable="on">
                <h3>${ hda.name }</h3>
            </div>
            <div id="mrh-controls-container" class="mrh-controls-container" unselectable="on">
                <div id="menu1-container" class="chrom-menu-container menu1-container"></div>
                <span id="position-display1" class="position-display display1"></span>
                <h5>by</h5>
                <div id="menu2-container" class="chrom-menu-container menu2-container"></div>
                <span id="position-display2" class="position-display display2"></span>
                <div class="mrh-cursor-container">
                    <div class="mrh-cursor-container">Cursor Position: </div>
                    <div id="mrh-cursor-X" class="mrh-cursor-label"></div>
                    <div class="mrh-cursor-container"> by </div>
                    <div id="mrh-cursor-Y" class="mrh-cursor-label"></div>
                </div>
                <div id="mrh-button-container" class="container">
                    <div id="zoom-in" class="buttons"></div>
                    <div id="zoom-out" class="buttons"></div>
                    <div id="mrh-settings-open" class="buttons"></div>
                </div>
            </div>
        </div>
        <div id="mrh-display-container" class="mrh-display">
            <div id="mrh-display-left" class="mrh-display">
                <div id="Vscroll" class="scroll">
                    <div id="Vscroll-box" class="scroll-box"></div>
                </div>
            </div>
            <div id="mrh-display-right" class="mrh-display">
                <canvas id="mrh-display-viewer" class="mrh-display"></canvas>
                <div id="Hscroll" class="scroll">
                    <div id="Hscroll-box" class="scroll-box"></div>
                </div>
            </div>
            <div id="mrh-display-bottom" class="mrh-display"></div>
        </div>
    <script type="text/javascript">
        var canvasSize = ${ canvasSize };
        $( document ).ready( function() {
            var docWidth = $( document ).width() - 1,
                docHeight = $( document ).height(),
                viewerSize = docWidth - 15,
                scrollSize = viewerSize + 1,
                settingsLeft = docWidth / 2 - 75,
                maskHeight = docWidth + $( 'mrh-top' ).height(),
                element = document.getElementById( 'mrh-top' ),
                maskHeight = docWidth + $( '#mrh-top' ).height() + 3;
            element = document.getElementById( 'mrh-mask' ),
            element.style.width = docWidth.toString() + 'px';
            element.style.height = maskHeight.toString() + 'px';
            element = document.getElementById( 'mrh-settings' );
            element.style.left = settingsLeft.toString() + 'px';
            element = document.getElementById( 'mrh-display-container' );
            element.style.width = docWidth.toString() + 'px';
            element = document.getElementById( 'mrh-top' );
            element.style.width = docWidth.toString() + 'px';
            element = document.getElementById( 'mrh-display-left' );
            element.style.height = docWidth.toString() + 'px';
            element = document.getElementById( 'Vscroll' );
            element.style.height = scrollSize.toString() + 'px';
            element = document.getElementById( 'Vscroll-box' );
            element.style.height = viewerSize.toString() + 'px';
            element.style.top = '0px';
            element.style.background = 'url(../../../static/images/visualization/draggable_vertical.png) center center no-repeat';
            element = document.getElementById( 'mrh-display-right' );
            element.style.height = docWidth.toString() + 'px';
            element.style.width = viewerSize.toString() + 'px';
            element = document.getElementById( 'mrh-display-viewer' );
            element.style.height = viewerSize.toString() + 'px';
            element.style.width = viewerSize.toString() + 'px';
            element = document.getElementById( 'Hscroll' );
            element.style.width = scrollSize.toString() + 'px';
            element = document.getElementById( 'Hscroll-box' );
            element.style.width = viewerSize.toString() + 'px';
            element.style.left = '0px';
            element.style.background = 'url(../../../static/images/visualization/draggable_horizontal.png) center center no-repeat';
            element = document.getElementById( 'mrh-display-bottom' );
            element.style.width = docWidth.toString() + 'px';
            element = document.getElementById( 'zoom-in' );
            element.style.background = 'url(../../../static/images/fugue/magnifier-zoom.png) center center no-repeat';
            element = document.getElementById( 'zoom-out' );
            element.style.background = 'url(../../../static/images/fugue/magnifier-zoom-out.png) center center no-repeat';
            element = document.getElementById( 'mrh-settings-open' );
            element.style.background = 'url(../../../static/images/fugue/gear.png) center center no-repeat';
            element = document.getElementById( 'mrh-settings-close' );
            element.style.background = 'url(../../../static/images/fugue/cross-circle.png) center center no-repeat';
        });
        var config = {
            root     : '${root}',
            app_root : '${app_root}'
        };
        require.config({
            baseUrl: config.root + "static/scripts/",
            paths: {
                "plugin"        : "${app_root}",
            },
        });
        require( ['plugin/app-view'], function( AppView ) {
            window.view = new AppView({
                dataset_id      : "${ query.get( 'dataset_id' ) }",
                viewerSize     : ${ viewerSize },
                canvasSize     : ${ canvasSize },
                mincolor       : "${ mincolor }",
                midcolor       : "${ midcolor }",
                maxcolor       : "${ maxcolor }",
            });
        });
    </script>
</body>
</html>
