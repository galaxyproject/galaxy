<html>

<head>

<link rel="stylesheet" type="text/css" href="/s/css/trackster.css" />

<script type="text/javascript" src="/static/scripts/jquery.js"></script>
<script type="text/javascript" src="/static/scripts/jquery.event.drag.js"></script>
<script type="text/javascript" src="/static/scripts/trackster.js"></script>
<script>

    var view = new View( "chr5", 180857866, 0, 180857866 );
    var tracks = new TrackLayout( view );

    $(function() {
        
        tracks.add( new LabelTrack( view, $("#viewport" ) ) );
        tracks.add( new LineTrack( "phastCons44way", view, $("#viewport" ) ) );
        tracks.add( new FeatureTrack( "knownGene", view, $("#viewport" ) ) );

        $(document).bind( "redraw", function( e ) {
            tracks.redraw();
        });
    
        $(window).resize( function( e ) {
            tracks.redraw();
        });
        
        $("#viewport").bind( "dragstart", function ( e ) {
            this.original_low = view.low;
        }).bind( "drag", function( e ) {
            var move_amount = ( e.offsetX - this.offsetLeft ) / this.offsetWidth;
            var range = view.high - view.low;
            var move_bases = Math.round( range * move_amount );
            var new_low = this.original_low - move_bases;
            if ( new_low < 0 ) {
                new_low = 0;
            } 
            var new_high = new_low + range;
            if ( new_high > view.length ) {
                new_high = view.length;
                new_low = new_high - range;
            }
            view.low = new_low;
            view.high = new_high;
            tracks.redraw();
        });

        tracks.redraw();
    });
</script>
<body>

<div id="content">

    <div id="overview">
       <div id="overview-viewport">
           <div id="overview-box"></div>
       </div>
    </div>

    <div id="nav">

        <div id="nav-controls">
        <a href="#" onclick="javascript:view.left(5);tracks.redraw();">&lt;&lt;</a>
        <a href="#" onclick="javascript:view.left(2);tracks.redraw();">&lt;</a>
    
        <span style="display: inline-block; width: 30em; text-align: center;">Viewing chr5:<span id="low">0</span>-<span id="high">180857866</span></span>

        <span style="display: inline-block; width: 10em;">
        <a href="#" onclick="javascript:view.zoom_in(2);tracks.redraw();">+</a>
        <a href="#" onclick="javascript:view.zoom_out(2);tracks.redraw();">-</a>
        </span>

        <a href="#" onclick="javascript:view.right(2);tracks.redraw();">&gt;</a>
        <a href="#" onclick="javascript:view.right(5);tracks.redraw();">&gt;&gt;</a>
        </div>
        
    </div>

    <div id="viewport">
    </div>

</div>

</body>

</html>
