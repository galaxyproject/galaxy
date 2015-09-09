define([ 'plugin/heatmap' ], function( Heatmap ){
	return Backbone.View.extend({
		el : $( '#mrh-display-viewer' ),
		model : Heatmap,
		events: {
			'dblclick'  : 'doubleClick',
			'mousedown' : 'mouseDown',
			'mouseover' : 'turnOnCursor',
			'mouseout'  : 'turnOffCursor',
		},

		initialize : function( options ){
			this.parent = options.parent;
			this.dragging = false;
			this.waiting = true;
			this.viewerSize = options.viewerSize;
			this.canvasSize = options.canvasSize;
			this.el.width = this.viewerSize;
			this.el.height = this.viewerSize;
			this.model = new Heatmap( _.extend( options, { view : this } ) );
			this.context = this.el.getContext( '2d' );
			this.context.alpha = false;
			this.el.style.cursor = 'progress';
			this.context.fillStyle = "rgb(0, 0, 0)";
			this.model.on( 'renderQueueUpdated', this.updateCanvas, this );
			this.model.on( 'fetchQueueUpdated', this.fetchInteractions, this );
		},

		fetchInteractions : function(){
			this.model.fetchInteractions();
		},

		renderFromQueue : function(){
			var self = this,
				queue = this.model.get( 'renderQueue' ),
				canvas, size, parameters;
			while( queue.length > 0 ){
				parameters = queue.pop();
				if( parameters.eff_maxres == self.parent.get( 'eff_maxres' ) &&
					parameters.start1 < this.parent.get( 'stop1' ) &&
					parameters.stop1 > this.parent.get( 'start1' ) &&
					parameters.start2 < this.parent.get( 'stop2' ) &&
					parameters.stop2 > this.parent.get( 'start2' ) ){
					canvas = self.model.canvases[ parameters.eff_maxres ][ parameters.name ];
					size = self.model.spans[ parameters.eff_maxres ] / self.parent.bpp;
					self.addCanvas( canvas, parameters.name, self.parent.get( 'start1' ),
						self.parent.get( 'start2' ), size );
				} else {
					this.updateCanvas();
				};
			};
		},

		turnOnCursor : function(){
			var self = this;
	        this.el.onmousemove = function(){ self.parent.updateCursor( event ); };
		},

		turnOffCursor : function(){
			this.parent.clearCursor();
	        this.el.onmousemove = null;
		},

		updateCanvas : function(){
			this.context.clearRect( 0, 0, this.viewerSize, this.viewerSize );
			var self = this,
				JSON = this.parent.toJSON(),
				canvases = {},
				temp, X, Y, ctx, res, size, count;
			canvases[ JSON.eff_maxres ] = {};
			canvases = this.model.loadCachedCanvases( canvases, JSON );
			count = 0;
			_.each( _.values( canvases ), function( value ){
				count += _.keys( value ).length;
			});
			if( count == 0 ){
				this.el.style.cursor = 'progress';
				this.waiting = true;
			} else {
				this.waiting = false;
			};
			res = this.parent.minresolution;
			while( res >= JSON.eff_maxres ){
				size = this.model.spans[ res ] / this.parent.bpp;
				_.each( canvases[ res ], function( canvas, name ){
					self.addCanvas( canvas, name, JSON.start1, JSON.start2, size );
				});
				res /= 2;
			};
			this.model.loadNewCanvases( canvases[ JSON.eff_maxres ], JSON );
		},

		addCanvas : function( canvas, name, start1, start2, size ){
			if( canvas == null){
				return;
			};
			var temp = name.split('_'),
				canvasX = parseInt(temp[0]),
				canvasY = parseInt(temp[1]),
				X = ( canvasX - start1 ) / this.parent.bpp,
				Y = ( canvasY - start2 ) / this.parent.bpp;
			this.context.drawImage( canvas, X, Y, size, size );
			this.render();
			this.waiting = false;
			if( this.dragging == true ){
				this.el.style.cursor = '-webkit-grabbing';
			} else {
				this.el.style.cursor = '-webkit-grab';
			};
		},

		doubleClick : function( e ){
			var X = e.pageX,
				Y = e.pageY,
				span = this.parent.span,
				qspan = span / 4.0,
				totalSpan = this.parent.totalSpan;
			this.parent.midX = Math.max( this.parent.minX + qspan, Math.min( this.parent.minX + totalSpan - qspan,
				(X - this.parent.controls.hScroll.mouseOffset ) / this.viewerSize * span +
				this.parent.get( 'start1' ) ) );
			this.parent.midY = Math.max( this.parent.minY + qspan, Math.min( this.parent.minY + totalSpan - qspan,
				(Y - this.parent.controls.vScroll.mouseOffset ) / this.viewerSize * span +
				this.parent.get( 'start2' ) ) );
			this.parent.updateZoomIn();
		},

		mouseDown : function( e ){
			this.startMouseX = e.pageX;
			this.startMouseY = e.pageY;
			this.startX = this.parent.midX;
			this.startY = this.parent.midY;
			this.dragging = true;
			if( this.waiting == false ){
				this.el.style.cursor = '-webkit-grabbing';
			};
			this.parent.dragHeatmap();
		},

		drag : function( e ){
			if( this.waiting == false ){
				this.el.style.cursor = '-webkit-grabbing';
			};
			var span = this.parent.span,
				hspan = span / 2.0,
				bpp = this.parent.bpp,
				changed = false,
				offset, mid;
			offset = this.startMouseX - e.pageX;
			if( offset != 0 ){
				mid = Math.max( hspan + this.parent.minX, Math.min( this.parent.maxX - hspan,
					offset * bpp + this.startX ) );
				this.parent.set( 'start1', mid - hspan );
				this.parent.set( 'stop1', mid + hspan );
				changed = true;
			};
			offset = this.startMouseY - e.pageY;
			if( offset != 0 ){
				mid = Math.max( hspan + this.parent.minY, Math.min( this.parent.maxY - hspan,
					offset * bpp + this.startY ) );
				this.parent.set( 'start2', mid - hspan );
				this.parent.set( 'stop2', mid + hspan );
				changed = true;
			};
			if( changed == true ){
				this.parent.trigger( 'updateViewer' );
			};
		},

	});
});