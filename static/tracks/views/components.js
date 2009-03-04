/*
 * Requires jQuery
 * testing a change for mercurial
 */

var Track = function (datasetId) {
  this.elem = $($j.v.Viewport.trackTemplate).clone();
  this.datasetId = datasetId;
  this.titleElem = this.elem.find(".track-title");
  this.titleElem.html($j.m.Data.datasets[datasetId]);
  this.canvasElem = this.elem.find(".track-canvas");
  console.log(this.canvasElem);
  this.renderer = new FeatureRenderer(this.canvasElem.get(0), $j.m.Viewport);

  // Bindings
  this.canvasElem.bind( "dragstart", function (l_track) {
    return function (e){
      this.original_low = $j.m.Viewport.start;
    };
  }(this));
  this.canvasElem.bind( "drag", function( l_track ) {
      return function(e) {
        var move_amount = ( e.offsetX - this.offsetLeft ) / this.offsetWidth;
        var range = $j.m.Viewport.end - $j.m.Viewport.start;
        var move_bases = Math.round( range * move_amount );
        var new_low = this.original_low - move_bases;
        /*if ( new_low < 0 ) {
          new_low = 0;
	}*/
	var new_high = new_low + range;
        /*if ( new_high > view.length ) {
          new_high = view.length;
          new_low = new_high - range;
        }*/
        $j.c.Viewport.panBy(new_low-$j.m.Viewport.start);
      };
  }(this));
  this.canvasElem.bind( "dblclick", function( l_track ) {
    return function(e) {
      $j.c.Viewport.zoomIn();
    };
  }(this));
};


$.extend( Track.prototype, {
  redraw: function () {
    this.renderer.start = $j.m.Viewport.start;
    this.renderer.end = $j.m.Viewport.end;
    this.renderer.clear();
    this.renderer.updateSize();
    // tickDistance = Math.floor( Math.pow( 10, Math.floor( Math.log( range ) / Math.log( 10 ) ) ) )
    this.renderer.xGridLines = Math.floor( Math.pow(10, Math.floor( Math.log( this.renderer.end - this.renderer.start ) / Math.log(10) ) ) );
    this.renderer.drawGridLines();
    this.renderer.plot( $j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms[chrom][this.datasetId] );
  }
});


var Axis = function() {
  this.canvasElem = $("#x-axis")[0];
  this.renderer = new Renderer( this.canvasElem, $j.m.Viewport );

  this.redraw = function () {
    this.renderer.start = $j.m.Viewport.start;
    this.renderer.end = $j.m.Viewport.end;
    this.renderer.clear();
    this.renderer.updateSize();
    this.renderer.xGridLines = Math.floor( Math.pow(10, Math.floor( Math.log( this.renderer.end - this.renderer.start ) / Math.log(10) ) ) );
    this.renderer.drawGridLines();
  };
};