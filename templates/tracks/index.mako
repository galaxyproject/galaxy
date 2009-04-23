<%inherit file="/base_panels.mako"/>

<%def name="init()">
<%
    self.active_view="tracks"
    self.has_left_panel=False
    self.has_right_panel=False
%>
</%def>

<%def name="stylesheets()">
${parent.stylesheets()}
<link rel="stylesheet" type="text/css" href="/static/trackster.css" />
</%def>

<%def name="late_javascripts()">
${parent.late_javascripts()}
<script type="text/javascript" src="/static/scripts/jquery.event.drag.js"></script>
<script type="text/javascript" src="/static/scripts/trackster.js"></script>
<script type="text/javascript">

    var view = new View( "${chrom}", ${LEN}, 0, ${max(LEN,1)} );
    var tracks = new TrackLayout( view );
    var dbkey = "${dbkey}";
    
    $(function() {
        
        tracks.add( new LabelTrack( view, $("#viewport" ) ) );
    %for track in tracks:
        tracks.add( new ${track["type"]}( "${track["name"]}", view, $("#viewport" ), ${track["id"]} ) );
    %endfor
        
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
        load_chroms();
    });

    var load_chroms = function () {
      var fetcher = function (ref) {
	return function () {
	  $.getJSON( "chroms", { dbkey: dbkey }, function ( data ) {
	    // Hacky - check length of "object"
	    var chrom_length = 0;
	    for (key in data) chrom_length++;
	    if( chrom_length == 0 ) {
	      setTimeout( fetcher, 5000 );
	    } else {
	      var chrom_options = '';
	      for (key in data) {
                if( key == view.chr ) {
                  chrom_options += '<option value="' + key + '" selected="true">' + key + '</option>';                  
                } else {
                  chrom_options += '<option value="' + key + '">' + key + '</option>';
                }
	      }
	      $("#chrom").html(chrom_options);
              $("#chrom").bind( "change", function ( e ) {
		$("#chr").submit();
	      });
              if( view.chr == "" ) {
	       $("#chrom option:first").attr("selected", true);
	       $("#chrom").trigger( "change" );
              }
	    }
	  });
	};
      }(this);
      fetcher();
    };

</script>
</%def>

<%def name="center_panel()">
<div id="content">

    <div id="overview">
       <div id="overview-viewport">
           <div id="overview-box"></div>
       </div>
    </div>


    <div id="viewport">
    </div>

</div>
    <div id="nav">

        <div id="nav-controls">
	<form name="chr" id="chr" method="GET">
        <a href="#" onclick="javascript:view.left(5);tracks.redraw();">&lt;&lt;</a>
        <a href="#" onclick="javascript:view.left(2);tracks.redraw();">&lt;</a>
	  <span style="display: inline-block; width: 30em; text-align: center;">Viewing
	    <select id="chrom" name="chrom">
	      <option value="">loading</option>
	    </select>
	    <span id="low">0</span>-<span id="high">180857866</span></span>
        <span style="display: inline-block; width: 10em;">
        <a href="#" onclick="javascript:view.zoom_in(2);tracks.redraw();">+</a>
        <a href="#" onclick="javascript:view.zoom_out(2);tracks.redraw();">-</a>
        </span>

        <a href="#" onclick="javascript:view.right(2);tracks.redraw();">&gt;</a>
        <a href="#" onclick="javascript:view.right(5);tracks.redraw();">&gt;&gt;</a>
	</form>
        </div>
        
    </div>
</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            <div style="float: right">
                <a class='panel-header-button' href="${h.url_for( controller='root', action='history_options' )}" target="galaxy_main"><span>Options</span></a>
            </div>
            <div class="panel-header-text">History</div>
        </div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_history" width="100%" height="100%" frameborder="0" style="position: absolute; margin: 0; border: 0 none; height: 100%;" src="${h.url_for( controller='root', action='history' )}"></iframe>
    </div>
</%def>
