<%inherit file="/base.mako"/>

<%def name="stylesheets()">
${parent.stylesheets()}
<link rel="stylesheet" type="text/css" href="/static/trackster.css" />
</%def>

<%def name="javascripts()">
${parent.javascripts()}
${h.js( "jquery", "jquery.event.drag", "jquery.mousewheel", "lrucache", "trackster" )}

<script type="text/javascript">

    var data_url = "${h.url_for( action='data' )}";
    var view = new View( "${chrom}", ${LEN} );
    
    $(function() {
        
        view.add_track( new LabelTrack( $("#overview" ) ) );
        view.add_track( new LabelTrack( $("#nav-labeltrack" ) ) );
   
        %for track in tracks:
            view.add_track( new ${track["type"]}( "${track['name']}", ${track['dataset_id']} ) );
        %endfor
        
        $(document).bind( "redraw", function( e ) {
            view.redraw();
        });
        
        $(document).bind("mousewheel", function(e, delta) {
            if (delta > 0) {
                view.zoom_in(2, e.pageX);
                view.redraw();
            } else {
                view.zoom_out(2);
                view.redraw();
            }
        });
        
        $(document).bind("dblclick", function(e) {
            view.zoom_in(2, e.pageX);
            view.redraw();
        });
        
        $("#overview-box").bind("dragstart", function(e) {
            this.current_x = e.offsetX;
        }).bind("drag", function(e) {
            var delta = e.offsetX - this.current_x;
            this.current_x = e.offsetX;
            
            var delta_chrom = Math.round(delta / $(document).width() * (view.max_high - view.max_low));
            var view_range = view.high - view.low;
            
            var new_low = view.low += delta_chrom;
            var new_high = view.high += delta_chrom;
            if (new_low < view.max_low) {
                new_low = 0;
                new_high = view_range;
            } else if (new_high > view.max_high) {
                new_high = view.max_high;
                new_low = view.max_high - view_range;
            }
            view.low = new_low;
            view.high = new_high;
            view.redraw();
        });

        $(window).resize( function( e ) {
            $("#viewport").height( $(window).height() - 120 );
            view.redraw();
        });

        $("#viewport").bind( "dragstart", function ( e ) {
            this.original_low = view.low;
            this.current_height = e.clientY;
        }).bind( "drag", function( e ) {
            var move_amount = ( e.offsetX - this.offsetLeft ) / this.offsetWidth;
            var new_scroll = $(this).scrollTop() - (e.clientY - this.current_height);
            
            if ( new_scroll < $(this).get(0).scrollHeight - $(this).height() - 200) {
                $(this).scrollTop(new_scroll);
                
            }
            this.current_height = e.clientY;
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
            view.redraw();
        });
        (function () {
            $.getJSON( "${h.url_for( action='chroms' )}", { dbkey: "${dbkey}" }, function ( data ) {
                var chrom_options = '<option value="">Select Chrom/Contig</option>';
                for (i in data) {
                    chrom = data[i]['chrom']
                    if( chrom == view.chrom ) {
                        chrom_options += '<option value="' + chrom + '" selected="true">' + chrom + '</option>';                  
                    } else {
                        chrom_options += '<option value="' + chrom + '">' + chrom + '</option>';
                    }
                }
                $("#chrom").html(chrom_options);
                $("#chrom").bind( "change", function () {
                    $("#chr").submit();
                });
            });
        })();
        view.redraw();
        $(window).trigger("resize");
    });

</script>
</%def>

<div id="content">
    <div id="overview">
        <div id="overview-viewport">
            <div id="overview-box"></div>
        </div>
    </div>
    <div id="viewport"></div>
</div>
<div id="nav">
    <div id="nav-labeltrack"></div>
    <div id="nav-controls">
        <form name="chr" id="chr" method="get">
            <select id="chrom" name="chrom">
                <option value="">Loading</option>
            </select>
            <input type="hidden" name="dataset_ids" value="${dataset_ids}" />
            <a href="#" onclick="javascript:view.left(5);view.redraw();">&lt;&lt;</a>
            <a href="#" onclick="javascript:view.left(2);view.redraw();">&lt;</a>
            <span id="low">0</span>&mdash;<span id="high">${LEN}</span>
            <a href="#" onclick="javascript:view.zoom_in(2);view.redraw();">+</a>
            <a href="#" onclick="javascript:view.zoom_out(2);view.redraw();">-</a>
            <a href="#" onclick="javascript:view.right(2);view.redraw();">&gt;</a>
            <a href="#" onclick="javascript:view.right(5);view.redraw();">&gt;&gt;</a>
        </form>
    </div>
</div>
