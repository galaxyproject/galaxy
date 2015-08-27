define([ 'static/controls' ], function( Controls ){
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
			this.addScoreFields();
			this.addOpenButton();
			this.addCloseButton();
			this.changed = false;
			this.minScoreView.on( 'click', function(){console.log('clicked2!');}, this );
		},

		addOpenButton : function(){
			this.openView = new SettingsOpenView( { parent: this.parent, settings: this } );
		},

		addCloseButton : function(){
			this.closeView = new SettingsCloseView( { parent: this.parent, settings: this } );
		},

		addScoreFields : function(){
			this.minScoreView = new ScoreView( { name : "mrh-mincolor-score", scoreName : "minscore",
				parent : this.parent, settings : this } );
			this.maxScoreView = new ScoreView( { name : "mrh-maxcolor-score", scoreName : "maxscore",
				parent : this.parent, settings : this } );
			this.minColorView = new ScoreColorView( { name : "mrh-mincolor-box", scoreName : "mincolor",
				parent : this.parent, settings : this } );
			this.midColorView = new ScoreColorView( { name : "mrh-midcolor-box", scoreName : "midcolor",
				parent : this.parent, settings : this } );
			this.maxColorView = new ScoreColorView( { name : "mrh-maxcolor-box", scoreName : "maxcolor",
				parent : this.parent, settings : this } );
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
			var element = $( "#mrh-mask" )[0];
			element.style[ 'z-index' ] = '1';
			element = $( "#mrh-settings" )[0];
			element.style[ 'z-index' ] = '1';
			this.changed = false;
			this.settings.minScoreView.value = this.parent.header.minscore;
			this.settings.maxScoreView.value = this.parent.header.maxscore;
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
			var element = $( "#mrh-mask" )[0],
				color;
			element.style[ 'z-index' ] = '-1';
			element = $( "#mrh-settings" )[0];
			element.style[ 'z-index' ] = '-1';
			if( this.settings.minScoreView.value != this.parent.header.minscore ||
					this.settings.maxScoreView.value != this.parent.header.maxscore ||
					this.settings.minColorView.color != this.parent._rgbToHex(
						$( "#" + this.settings.minColorView.scoreName + 'ColorPicker' ).css('background-color') ) ||
					this.settings.midColorView.color != this.parent._rgbToHex(
						$( "#" + this.settings.midColorView.scoreName + 'ColorPicker' ).css('background-color') ) ||
					this.settings.maxColorView.color != this.parent._rgbToHex(
						$( "#" + this.settings.maxColorView.scoreName + 'ColorPicker' ).css('background-color') ) ){
				this.parent.header.minscore = this.settings.minScoreView.value;
				this.parent.header.midscore = ( this.settings.minScoreView.value +
					this.settings.maxScoreView.value ) / 2.0;
				this.parent.header.maxscore = this.settings.maxScoreView.value;
				this.parent.header.scorespan = this.parent.header.maxscore - this.parent.header.minscore;
				color = $( "#" + this.settings.minColorView.scoreName + 'ColorPicker' ).css('background-color');
				$( "#mrh-" + this.settings.minColorView.scoreName + "-box" ).css('background-color', color );
				this.settings.minColorView.color = this.parent._rgbToHex( color );
				this.parent.header.mincolor = this.parent._rgbToList( color );
				color = $( "#" + this.settings.midColorView.scoreName + 'ColorPicker' ).css('background-color');
				$( "#mrh-" + this.settings.midColorView.scoreName + "-box" ).css('background-color', color );
				this.settings.midColorView.color = this.parent._rgbToHex( color );
				this.parent.header.midcolor = this.parent._rgbToList( color );
				color = $( "#" + this.settings.maxColorView.scoreName + 'ColorPicker' ).css('background-color');
				$( "#mrh-" + this.settings.maxColorView.scoreName + "-box" ).css('background-color', color );
				this.settings.maxColorView.color = this.parent._rgbToHex( color );
				this.parent.header.maxcolor = this.parent._rgbToList( color );
				this.parent.heatmapView.model.resetCanvases();
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
		},

		editField : function(){
			var value = this.el[0].firstChild.textContent,
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
		    this.el[0].style.bottom = "0px";
		    this.el[0].firstChild.focus();
		    document.getElementById( this.name ).onclick = null;
		    $(document).on('blur','#' + self.name, function(){
		    	self.finishField();
			});
		},

		finishField : function(){
			var self = this,
				value = parseFloat( this.el[0].firstChild.value );
			this.value = value
			this.el[0].innerHTML = value.toFixed(2);
		    this.el[0].style.bottom = "-2px";
	        document.getElementById( this.name ).onclick = function(){ self.editField(); };
	        value = ( this.settings.minScoreView.value + this.settings.maxScoreView.value ) / 2.0;
	        $( "#mrh-midcolor-score" )[0].innerHTML = value.toFixed(2)
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
			//var self = this;
	        //document.getElementById( this.name ).onclick = function(){ self.openColorPicker(); };
		},

		addColorPicker : function(){
            var container_div = $("<div/>").appendTo( $( "#" + this.name )[0] ),
            	id = this.scoreName + 'ColorPicker',
            	value = this.color,
                input = $('<input />').attr("id", id ).attr("name", id ).css("position", "relative")
                	.css( "width", "60px" ).css( "top", "-3px" ).css( "left", "-1px" )
                    .appendTo(container_div).click(function(e) {
                    // Show input's color picker.
                    var tip = $(this).siblings(".tooltip").addClass( "in" );
                    tip.css( { 
                        left: $(this).position().left + $(this).width() + 5,
                        top: $(this).position().top - ( $(tip).height() / 2 ) + ( $(this).height() / 2 )
                        } ).show();
                    // Keep showing tip if clicking in tip.
                    tip.click(function(e) {
                        e.stopPropagation();
                    });
                    // Hide tip if clicking outside of tip.
                    $(document).bind( "click.color-picker", function() {
                        tip.hide();
                        $(document).unbind( "click.color-picker" );
                    });
                    // No propagation to avoid triggering document click (and tip hiding) above.
                    e.stopPropagation();
                }),
                // Color picker in tool tip style.
                tip = $( "<div class='tooltip right' style='position: absolute;' />" ).appendTo(container_div).hide(),
                // Inner div for padding purposes
                tip_inner = $("<div class='tooltip-inner' style='text-align: inherit'></div>").appendTo(tip),
                tip_arrow = $("<div class='tooltip-arrow'></div>").appendTo(tip),
                farb_obj = $.farbtastic(tip_inner, { width: 100, height: 100, callback: input, color: value });
            // Clear floating.
            container_div.append( $("<div/>").css("clear", "both"));
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

	var CoordinateDisplayView = Backbone.View.extend({
		model : Controls.Generic,

		initialize : function( options ){
			this.model = new Controls.Generic( { view: this } );
			this.parent = options.parent;
			this.el = options.el;
		},

		updateDisplay : function( start, stop ){
			this.$el.html( start + ' - ' + stop );
			this.render();
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
		CoordinateDisplay : CoordinateDisplayView,
		HScroll           : HScrollView,
		VScroll           : VScrollView,
	}
});