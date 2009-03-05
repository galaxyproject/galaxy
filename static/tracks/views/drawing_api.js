var Renderer = function (canvas, config) {
  this.ctx = canvas.getContext("2d");
  this.canvas = canvas;
  this.updateSize();

  this.start = config.start || 0;
  this.end = config.end || 0;
  this.yMin = config.yMin || 0;
  this.yMax = config.yMax || this._height;
  this.scaleX = this._width / (this.end - this.start);
  this.scaleY = this._height /(this.yMax - this.yMin);
  this.xGridLines = config.xGridLines || 100000;
  this.xGridOffset = config.xGridOffset || 0;
};

$.extend( Renderer.prototype, {
  tX: function (x) {
    return ( x - this.start ) * this.scaleX;
  },
  tY: function (y) {
    return ( y - this.yMin ) * this.scaleY;
  },
  drawGridLines: function() {
    var lastX = this.end - (this.end % this.xGridLines) + this.xGridOffset;
    this.ctx.beginPath();
    this.ctx.setLineWidth(0.1);
    for(i=lastX; i>this.start; i-= this.xGridLines ) {
      this.ctx.moveTo( this.tX(i), 0);
      this.ctx.lineTo( this.tX(i), this._height );
    }
    this.ctx.closePath();
    this.ctx.stroke();
    return true;
  },
  updateSize: function() {
    this._width = this.ctx.canvas.width = $(this.canvas).width();
    this._height = this.ctx.canvas.height = $(this.canvas).height();
    this.scaleX =  this._width / (this.end - this.start);
    this.scaleY = this._height /(this.yMax - this.yMin);
  },
  clear: function() {
    this.ctx.clearRect(0,0,this.ctx.canvas.width, this.ctx.canvas.height);
  }
});

var PositionRenderer = function(canvas, config) {
  Renderer.call( this, canvas, config );
};

var FeatureRenderer = function(canvas, config) {
  Renderer.call( this, canvas, config );
  this.lanes = [];
  this.featureHeight = 8;
  this.featurePadding = 2;
};

$.extend( FeatureRenderer.prototype, Renderer.prototype, {
  drawRect: function(x1,y1,x2,y2) {
    x1 = (x1 - this.start) * this.scaleX; //this.tX(x1);
    x2 = (x2 - this.start) * this.scaleX; //this.tX(x2);
    this.ctx.fillRect( x1, y1, Math.max(1,x2-x1), y2-y1 );
  },
  plot: function(features) {
    var laneHeight = this.featureHeight + this.featurePadding;
    this.ctx.setFillColor("#000000");
    for( idx in features ) {
      var feature = features[idx];
      var lane = 0;
      while( feature[0] < this.lanes[lane] && this.lanes[lane] != undefined ){
	if( this.lanes && feature[0] < this.lanes[lane] )
	  lane++;
      }
      this.lanes[lane] = feature[1];
      var yOffset = laneHeight * lane;
      this.drawRect( feature[0], yOffset, feature[1], yOffset+this.featureHeight );
    }
    this.lanes = [];
  }
});