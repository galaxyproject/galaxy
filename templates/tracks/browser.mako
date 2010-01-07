<%inherit file="/base.mako"/>

<%def name="stylesheets()">
${parent.stylesheets()}
<link rel="stylesheet" type="text/css" href="/static/trackster.css" />
</%def>

<%def name="javascripts()">
${parent.javascripts()}
${h.js( "jquery", "jquery.event.drag", "jquery.mousewheel", "trackster" )}

<script type="text/javascript">

    var data_url = "${h.url_for( action='data' )}";
    var view = new View( "${chrom}", ${LEN} );
    
    $(function() {
        
        view.add_track( new LabelTrack( $("#top-labeltrack" ) ) );
        view.add_track( new LabelTrack( $("#nav-labeltrack" ) ) );
   
        %for track in tracks:
            view.add_track( new ${track["type"]}( "${track['name']}", ${track['dataset_id']}, "${track['indexer']}" ) );
        %endfor
        
        $(document).bind( "redraw", function( e ) {
            view.redraw();
        });
        
        $(document).bind("mousewheel", function( e, delta ) {
            if (delta > 0) {
                view.zoom_in(e.pageX);
            } else {
                view.zoom_out();
            }
            e.preventDefault();
        });
        
        $(document).bind("dblclick", function( e ) {
            view.zoom_in(e.pageX);
        });
        
        // To let the overview box be draggable
        $("#overview-box").bind("dragstart", function( e ) {
            this.current_x = e.offsetX;
        }).bind("drag", function( e ) {
            var delta = e.offsetX - this.current_x;
            this.current_x = e.offsetX;
            
            var delta_chrom = Math.round(delta / $(document).width() * view.span);
            view.center += delta_chrom;
            view.redraw();
        });

        // To adjust the size of the viewport to fit the fixed-height footer
        $(window).resize( function( e ) {
            $("#content").height( $(window).height() - $("#nav-container").height() );
            $("#viewport-container").height( $("#content").height() - $("#top-labeltrack").height() - $("#nav-labeltrack").height() );
            view.redraw();
        });
        
        $(window).resize();

        $("#viewport").bind( "dragstart", function( e ) {
            this.original_low = view.low;
            this.current_height = e.clientY;
            this.current_x = e.offsetX;
        }).bind( "drag", function( e ) {
            var container = $(this).parent();
            var delta = e.offsetX - this.current_x;
            var new_scroll = container.scrollTop() - (e.clientY - this.current_height);
            if ( new_scroll < container.get(0).scrollHeight - container.height() ) {
                container.scrollTop(new_scroll);
                
            }
            this.current_height = e.clientY;
            this.current_x = e.offsetX;

            var delta_chrom = Math.round(delta / $(document).width() * (view.high - view.low));
            view.center -= delta_chrom;
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
        $(window).trigger("resize");
    });

</script>
</%def>

<div id="content">
    <div id="top-labeltrack"></div>
    <div id="viewport-container" style="overflow-x: hidden; overflow-y: auto;">
        <div id="viewport"></div>
    </div>
    <div id="nav-labeltrack"></div>
</div>
<div id="nav-container">
    ## <div style="height: 5px; border-top: solid #ccc 1px"></div>
    <div id="nav">
        <div id="overview">
            <div id="overview-viewport">
                <div id="overview-box"></div>
            </div>
        </div>
        <div id="nav-controls">
            <form name="chr" id="chr" method="get">
                <select id="chrom" name="chrom" style="width: 15em;">
                    <option value="">Loading</option>
                </select>
            <input id="low" size="12" />:<input id="high" size="12" />
                ## <input type="hidden" name="dataset_ids" value="${dataset_ids}" />
            <input type="hidden" name="id" value="${id}" />
                <a href="#" onclick="javascript:view.zoom_in();view.redraw();">+</a>
                <a href="#" onclick="javascript:view.zoom_out();view.redraw();">-</a>
            </form>
            <div id="debug" style="float: right"></div>
        </div>
    </div>
</div>
