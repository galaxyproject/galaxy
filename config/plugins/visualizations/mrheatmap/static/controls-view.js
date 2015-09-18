define([ 'plugin/controls', 'mvc/ui/ui-color-picker' ], function( Controls, ColorPicker ){
	var ChromosomeView = Backbone.View.extend({
		tagName : 'option',
		className : 'chrom_option',

		render : function() {
			this.el.innerHTML = this.model.get( 'label' );
			this.el.value = this.model.get( 'value' );
			return this;
		},
	});

	var ChromosomeMenuView = Backbone.View.extend({
		events: {
			'change' : 'updateSelected',
		},

		initialize : function( options ) {
			this.parent = options.parent;
			this.side = options.side;
			this.el = options.el;
			this.collection = new Controls.Chromosomes( null, { view: this } );
			this.selected = null;
			this.chromViews = [];
		},

		populateChromMenu : function( chromosomes ) {
			var self = this,
				model;
			_.each( chromosomes, function( chrom ) {
				self.collection.add( new Controls.Chromosome( { value: chrom, label: 'chr' + chrom } ) );
			});
			self.chromViews = [];
			_.each( self.collection.models, function( chrom ) {
				self.chromViews.push( new ChromosomeView( { model: chrom } ) );
			});
			self.render();
			self.selected = self.collection.at( 0 ).get( 'value' );
			self.parent.set( 'chrom' + self.side, self.selected );
			self.parent.checkHeader();
		},

		render : function() {
			var self = this;
			$( self.el ).empty();
			_.each( self.chromViews, function( cv ) {
				self.$el.append( cv.render().el );
			});
			return this;
		},

		updateSelected : function() {
			this.selected = event.target.value;
			this.parent.set( 'chrom' + this.side, this.selected );
		},
	});

	var SettingsView = Backbone.View.extend({
		el : $( "#mrh-settings" ),
		model : Controls.Generic,

		initialize : function( options ) {
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
			this.minColor = options.mincolor;
			this.midColor = options.midcolor;
			this.maxColor = options.maxcolor;
			this.minScore = -10.0;
			this.midScore = 0.0;
			this.maxScore = 10.0;
			this.addScoreFields();
			this.addOpenButton();
			this.addCloseButton();
			this.changed = false;
		},

		addOpenButton : function(){
			this.openView = new SettingsOpenView( { parent: this.parent, settings: this } );
		},

		addCloseButton : function(){
			this.closeView = new SettingsCloseView( { parent: this.parent, settings: this } );
		},

		addScoreFields : function(){
			this.minScoreView = new ScoreView( { name : "mrh-mincolor-score", scoreName : "minScore",
				parent : this.parent, settings : this } );
			this.maxScoreView = new ScoreView( { name : "mrh-maxcolor-score", scoreName : "maxScore",
				parent : this.parent, settings : this } );
			var temp = $( "#mrh-mincolor-box" );
			this.minColorView = new ColorPicker({
				id: "mrh-mincolor-boxp",
				value: this.minColor,
				onchange: function(){}
			});
			temp[0].insertBefore( this.minColorView.el, temp[0].firstChild );
			this.minColorView.$( ".ui-color-picker-label" )[0].innerHTML = '';
			this.minColorView.$( ".ui-color-picker-view" )
				.css( 'background-color', '#FFF' )
				.css( 'left', '16px' )
				.css( 'position', 'relative' );
			temp = $( "#mrh-midcolor-box" );
			this.midColorView = new ColorPicker({
				id: "mrh-midcolor-boxp",
				value: this.midColor,
				onchange: function(){}
			});
			temp[0].appendChild( this.midColorView.el );
			this.midColorView.$( ".ui-color-picker-label" )[0].innerHTML = '';
			this.midColorView.$( ".ui-color-picker-view" )
				.css( 'background-color', '#FFF' )
				.css( 'left', '16px' )
				.css( 'position', 'relative' );
			temp = $( "#mrh-maxcolor-box" );
			this.maxColorView = new ColorPicker({
				id: "mrh-maxcolor-boxp",
				value: this.maxColor,
				onchange: function(){}
			});
			temp[0].appendChild( this.maxColorView.el );
			this.maxColorView.$( ".ui-color-picker-label" )[0].innerHTML = '';
			this.maxColorView.$( ".ui-color-picker-view" )
				.css( 'background-color', '#FFF' )
				.css( 'left', '16px' )
				.css( 'position', 'relative' );
		},
	});

	var SettingsOpenView = Backbone.View.extend({
		el : $( "#mrh-settings-open" ),
		model : Controls.Generic,
		events : {
			"click" : "openSettingsPanel"
		},

		initialize : function( options ) {
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
			this.settings = options.settings;
		},

		openSettingsPanel : function(){
			$( "#mrh-mask" ).css( "visibility", "visible" );
			$( "#mrh-settings" ).css( "visibility", "visible" );
			this.changed = false;
		},
	});
	
	var SettingsCloseView = Backbone.View.extend({
		el : $( "#mrh-settings-close" ),
		model : Controls.Generic,
		events : {
			"click" : "closeSettingsPanel"
		},

		initialize : function( options ) {
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
			this.settings = options.settings;
		},

		closeSettingsPanel : function(){
			var color;
			$( "#mrh-mask" ).css( "visibility", "hidden" )
			$( "#mrh-settings" ).css( "visibility", "hidden" )
			if( 	this.settings.minScore != this.parent.header.minscore ||
					this.settings.maxScore != this.parent.header.maxscore ||
					this.settings.minColorView.value() != this.settings.minColor ||
					this.settings.midColorView.value() != this.settings.midColor ||
					this.settings.maxColorView.value() != this.settings.maxColor ){
				this.parent.header.minscore = this.settings.minScore;
				this.parent.header.midscore = ( this.settings.minScore +
					this.settings.maxScore ) / 2.0;
				this.parent.header.maxscore = this.settings.maxScore;
				this.parent.header.scorespan = this.parent.header.maxscore - this.parent.header.minscore;
				this.settings.minColor = this.settings.minColorView.value();
				this.parent.header.mincolor = this.parent._hexToList( this.settings.minColorView.value() );
				this.settings.midColor = this.settings.midColorView.value();
				this.parent.header.midcolor = this.parent._hexToList( this.settings.midColorView.value() );
				this.settings.maxColor = this.settings.maxColorView.value();
				this.parent.header.maxcolor = this.parent._hexToList( this.settings.maxColorView.value() );
				this.parent.heatmapView.model.resetCanvases();
				this.parent.loadInitialHeatmap();
				this.parent.heatmapView.updateCanvas();
			};
		},
	});

	var ScoreView = Backbone.View.extend({
		model : Controls.Generic,

		initialize : function( options ){
			this.name = options.name;
			this.scoreName = options.scoreName;
			this.el = $( "#" + this.name );
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
			this.settings = options.settings;
			var self = this;
	        document.getElementById( this.name ).onclick = function(){ self.editField(); };
		    $(document).on('blur','#' + self.name, function(){
		    	self.finishField();
			});
		},

		editField : function(){
			var value = this.settings[ this.scoreName ],
				self = this;
			this.el[0].innerHTML = '';
    		$('<input class="mrh-score-text-editable" unselectable="off"></input>')
        		.attr({
		            'type': 'text',
		            'name': 'scorefield',
		            'id': 'txt_scorefield',
		            'value': value,
		        })
		        .appendTo( this.el[0] );
		    this.el.css( 'bottom', "0px" );
		    this.el[0].firstChild.focus();
		    document.getElementById( this.name ).onclick = null;
		},

		finishField : function(){
			var self = this,
				value = this.el[0].firstChild.value;
			try{
				value = Number( value );
			}
			catch( err ){
				value = this.settings[ this.scoreName ];
			}
			if( isNaN(value) == true ){
				value = this.settings[ this.scoreName ];
			};
			this.settings[ this.scoreName ] = value;
			this.el[0].innerHTML = value.toFixed(2);
		    this.el[0].style.bottom = "-2px";
	        document.getElementById( this.name ).onclick = function(){ self.editField(); };
	        value = ( this.settings.minScore + this.settings.maxScore ) / 2.0;
	        $( "#mrh-midcolor-score" )[0].innerHTML = value.toFixed(2)
	        this.settings.midScore = value;
		},
	});

	var ScoreColorView = Backbone.View.extend({
		model : Controls.Generic,

		initialize : function( options ) {
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
			this.name = options.name;
			this.scoreName = options.scoreName;
			this.el = $( "#" + this.name );
			this.color = this.parent._rgbToHex( $( "#mrh-" + this.scoreName + "-box" ).css('background-color') );
			this.addColorPicker();
		},

		addColorPicker : function(){
            var container_div = $("<div/>").appendTo( $( "#" + this.name )[0] ),
            	id = this.scoreName + 'ColorPicker',
            	value = this.color,
            	self = this,
                picker = new ColorPicker({
                	id:id,
                	value:value,
                	onchange:function( newcolor ){
	                	self.color = newcolor;
	                },
	            });
        }, 
	});

	var ZoomInView = Backbone.View.extend({
		el : $( "#zoom-in" ),
		model : Controls.Generic,
		events : {
			"click" : "updateCoordinates"
		},

		initialize : function( options ) {
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
		},

		updateCoordinates : function(){
			this.parent.updateZoomIn();
		},
	});

	var ZoomOutView = Backbone.View.extend({
		el : $( "#zoom-out" ),
		model : Controls.Generic,
		events : {
			"click" : "updateCoordinates"
		},

		initialize : function( options ) {
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
		},

		updateCoordinates : function(){
			this.parent.updateZoomOut();
		},
	});

	var CoordinateRangeView = Backbone.View.extend({
		model : Controls.Generic,

		initialize : function( options ){
			this.name = options.name;
			this.axis = options.axis;
			this.otherAxis = options.otherAxis;
			this.el = $( "#" + this.name );
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
			var self = this;
	        document.getElementById( this.name ).onclick = function(){ self.editField(); };
		    $(document).on('blur','#' + self.name, function(){
		    	self.finishField();
			});
		},

		editField : function(){
			var value = this.parent.get( 'start' + this.axis ) + ' - ' + this.parent.get( 'stop' + this.axis ),
				self = this;
			this.el[0].innerHTML = '';
    		$('<input class="mrh-position-text-editable" unselectable="off"></input>')
        		.attr({
		            'type': 'text',
		            'name': 'coordrange',
		            'id': 'txt_coordrange',
		            'value': value,
		        })
		        .appendTo( this.el[0] );
		    this.el.css( 'bottom', "0px" );
		    this.el[0].firstChild.focus();
		    document.getElementById( this.name ).onclick = null;
		},

		finishField : function(){
			var self = this,
				value = this.el[0].firstChild.value,
				values = value.split(' - '),
				changed = false;
			try{
				values[0] = parseInt( Number( values[0] ) );
				values[1] = parseInt( Number( values[1] ) );
			}
			catch( err ){
				values[0] = this.parent.get( 'start' + this.axis );
				values[1] = this.parent.get( 'stop' + this.axis );
			}
			if( isNaN( values[0] ) == true || isNaN( values[1] ) == true || values[1] <= values[0] ){
				values[0] = this.parent.get( 'start' + this.axis );
				values[1] = this.parent.get( 'stop' + this.axis );
			};
		    this.el[0].style.bottom = "-2px";
	        document.getElementById( this.name ).onclick = function(){ self.editField(); };
	        this.updateDisplay()
			if( values[0] != this.parent.get( 'start' + this.axis ) ||
				values[1] != this.parent.get( 'stop' + this.axis ) ){
				if( this.axis == '1' ){
					values[0] = Math.max( this.parent.minX, values[0] );
					values[1] = Math.min( this.parent.maxX, values[1] );
				} else {
					values[0] = Math.max( this.parent.minY, values[0] );
					values[1] = Math.min( this.parent.maxY, values[1] );
				};
				if( values[0] < values[1] ){
					var span = (values[1] - values[0]) / 2,
						mid = (this.parent.get( 'start' + this.otherAxis ) +
							   this.parent.get( 'stop' + this.otherAxis) ) / 2,
						start = mid - span,
						stop = mid + span;
					if( this.axis == '1' ){
						start = Math.max( this.parent.minY, start );
						stop = Math.min( this.parent.maxY, start + span * 2 );
						start = stop - span * 2;
					} else {
						start = Math.max( this.parent.minX, start );
						stop = Math.min( this.parent.maxX, start + span * 2 );
						start = stop - span * 2;
					};
					this.parent.set( 'start' + this.otherAxis, start );
					this.parent.set( 'stop' + this.otherAxis, stop );
					this.parent.set( 'start' + this.axis, values[0] );
					this.parent.set( 'stop' + this.axis, values[1] );
					this.parent.update();
				};
			};
		},

		updateDisplay : function(){
			var value0 = parseInt(this.parent.get( 'start' + this.axis )).toString(),
				value1 = parseInt(this.parent.get( 'stop' + this.axis )).toString();
			this.el[0].innerHTML = value0 + ' - ' + value1;
		},
	});

	var CoordinateDisplayView = Backbone.View.extend({
		model : Controls.Generic,

		initialize : function( options ){
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
			this.el = options.el;
		},

		updateCursor : function( chrom, mid ){
			this.$el.html( 'chr' + chrom + ':' + Math.round(mid) );
			this.render();
		},

		clearCursor : function(){
			this.$el.html( '' );
			this.render();
		},
	});

	var HScrollView = Backbone.View.extend({
		el : $( "#Hscroll-box"),
		model : Controls.Generic,
		events : {
			'mousedown' : 'mouseDown',
		},

		initialize : function( options ){
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
			this.viewerSize = options.viewerSize;
			this.offset = parseInt( this.el.style.left );
			this.maxWidth = parseInt( this.el.style.width );
			this.width = this.maxWidth
			this.minWidth = 3.0;
			this.mid = this.maxWidth / 2.0;
			this.dragging = false;
			this.box = false;
			this.mouseOffset = parseInt( $( "#mrh-display-left" ).width() );
			var self = this;
	        document.getElementById( "Hscroll-box" ).onmouseover = function(){ self.box = true; };
	        document.getElementById( "Hscroll-box" ).onmouseout = function(){ self.box = false; };
	        document.getElementById( "Hscroll-box" ).onmousedown = function(){ self.mouseDown( event ) };
	        document.getElementById( "Hscroll" ).onclick = function(){ self.mouseClick( event ) };
		},

		updateHandle : function(){
			this.width = Math.max( this.minWidth, ( this.maxWidth * this.parent.span ) /this.parent.totalSpan );
			if( this.parent.span != this.parent.totalSpan ){
				this.mid = ( ( this.parent.get( 'start1' ) - this.parent.minX ) /
					( this.parent.totalSpan - this.parent.span ) * ( this.maxWidth - this.width ) + this.width / 2.0 );
			} else {
				this.mid = this.maxWidth / 2.0;
			};
			this.el.style.left = ( this.mid - this.width / 2.0 + this.offset ).toString() + 'px';
			this.el.style.width = this.width.toString() + 'px';
			this.render();
		},

		mouseDown : function( e ){
			this.dragging = true;
			this.mouseStart = e.pageX;
			this.startingMid = this.mid;
			this.parent.dragX();
		},

		mouseClick : function( e ){
			if( this.box == false ){
				if( e.pageX - this.mouseOffset < this.mid ){
					var mid = Math.max( this.width / 2.0, this.mid - this.width );
				} else {
					var mid = Math.min( this.maxWidth - this.width / 2.0, this.mid + this.width );
				};
				var start = ( ( mid - this.width / 2.0 ) / ( this.maxWidth - this.width ) *
					( this.parent.totalSpan - this.parent.span ) + this.parent.minX );
				this.parent.set( 'start1', Math.round( start ) );
				this.parent.set( 'stop1', Math.round( start + this.parent.span ) );
				this.mid = mid;
				this.parent.trigger( 'updateViewer' );
			};
		},

		drag : function(e){
			if( this.dragging ){
				var X = e.pageX;
				if ( X ){
					var mid = Math.max( Math.min( this.maxWidth - this.width / 2.0,
						X - this.mouseStart + this.startingMid ),
						this.width / 2.0 );
					if( mid != this.mid ){
						var start = ( ( mid - this.width / 2.0 ) / ( this.maxWidth - this.width ) *
							( this.parent.totalSpan - this.parent.span ) + this.parent.minX );
						this.parent.set( 'start1', Math.round( start ) );
						this.parent.set( 'stop1', Math.round( start + this.parent.span ) );
						this.mid = mid;
						this.parent.trigger( 'updateViewer' );
					};
				};
			};
		},
	});

	var VScrollView = Backbone.View.extend({
		el : $( "#Vscroll-box"),
		model : Controls.Generic,

		initialize : function( options ){
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
			this.viewerSize = options.viewerSize;
			this.offset = parseInt( this.el.style.top );
			this.maxHeight = parseInt( this.el.style.height );
			this.height = this.maxHeight;
			this.minHeight = 3.0;
			this.mid = this.maxHeight / 2.0;
			this.dragging = false;
			this.box = false;
			this.mouseOffset = parseInt( $( "#mrh-top" ).css( "height" ) ) + 2;
			var self = this;
	        document.getElementById( "Vscroll-box" ).onmouseover = function(){ self.box = true; };
	        document.getElementById( "Vscroll-box" ).onmouseout = function(){ self.box = false; };
	        document.getElementById( "Vscroll-box" ).onmousedown = function(){ self.mouseDown( event ) };
	        document.getElementById( "Vscroll" ).onclick = function(){ self.mouseClick( event ) };
		},

		updateHandle : function(){
			this.height = Math.max( this.minHeight, ( this.maxHeight * this.parent.span ) / this.parent.totalSpan );
			if( this.parent.span != this.parent.totalSpan ){
				this.mid = ( ( this.parent.get( 'start2' ) - this.parent.minY ) /
					( this.parent.totalSpan - this.parent.span ) *
					( this.maxHeight - this.height ) + this.height / 2.0 );
			} else {
				this.mid = this.maxHeight / 2.0;
			};
			this.el.style.top = ( this.mid - this.height / 2.0 + this.offset ).toString() + 'px';
			this.el.style.height = this.height.toString() + 'px';
			this.render();
		},

		mouseDown : function( e ){
			this.dragging = true;
			this.mouseStart = e.pageY;
			this.startingMid = this.mid;
			this.parent.dragY();
		},

		mouseClick : function( e ){
			if( this.box == false ){
				if( e.pageY - this.mouseOffset < this.mid ){
					var mid = Math.max( this.height / 2.0, this.mid - this.height );
				} else {
					var mid = Math.min( this.maxHeight - this.height / 2.0, this.mid + this.height );
				};
				var start = ( ( mid - this.height / 2.0 ) / ( this.maxHeight - this.height ) *
					( this.parent.totalSpan - this.parent.span ) + this.parent.minY );
				this.parent.set( 'start2', Math.round( start ) );
				this.parent.set( 'stop2', Math.round( start + this.parent.span ) );
				this.mid = mid;
				this.parent.trigger( 'updateViewer' );
			};
		},

		drag : function(e){
			if( this.dragging ){
				var Y = e.pageY;
				if ( Y ){
					var mid = Math.max( Math.min( this.maxHeight - this.height / 2.0,
						Y - this.mouseStart + this.startingMid ),
						this.height / 2.0 );
					if( mid != this.mid ){
						var start = ( ( mid - this.height / 2.0 ) / ( this.maxHeight - this.height ) *
							( this.parent.totalSpan - this.parent.span ) + this.parent.minY );
						this.parent.set( 'start2', Math.round( start ) );
						this.parent.set( 'stop2', Math.round( start + this.parent.span ) );
						this.mid = mid;
						this.parent.trigger( 'updateViewer' );
					};
				};
			};
		},
	});

	return {
		Chromosome        : ChromosomeView,
		ChromosomeMenu    : ChromosomeMenuView,
		Settings          : SettingsView,
		ZoomIn            : ZoomInView,
		ZoomOut           : ZoomOutView,
		CoordinateRange : CoordinateRangeView,
		CoordinateDisplay : CoordinateDisplayView,
		HScroll           : HScrollView,
		VScroll           : VScrollView,
	}
});