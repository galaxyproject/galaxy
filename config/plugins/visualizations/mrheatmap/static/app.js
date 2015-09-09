define([ 'plugin/controls-view', 'plugin/heatmap-view' ], function( ControlsView, HeatmapView ){
    return Backbone.Model.extend({

        jsonableAttributes : [
            'chrom1', 'start1', 'stop1', 'chrom2', 'start2', 'stop2', 'minresolution', 'maxresolution', 'eff_maxres'
        ],

        initialize : function( attributes ){
            this.set( 'viewerSize', parseInt( $( "#mrh-display-viewer" ).css( 'width' ) ) );
            attributes.viewerSize = this.get( 'viewerSize' );
            this.set( 'chrom1', null );
            this.set( 'chrom2', null );
            this.loadingHeader = false;
            this.on( 'header_loaded', this.setInitialValues, this );
            this.on( 'change:chrom1 change:chrom2', this.checkHeader, this );
            this.on( 'updateViewer', this.update, this );
            this.heatmapView = new HeatmapView( _.extend( attributes, { parent: this } ) );
            this.fetchChromosomes();
            this.controls = {};
            this.addCoordinateDisplays();
            this.addZoomIn();
            this.addZoomOut();
            this.addCursor();
            this.addSettings();
            this.addScrolls();
        },

        update : function(){
            this.span = this.get( 'stop1' ) - this.get( 'start1' )
            this.midX = ( this.get( 'stop1' ) + this.get( 'start1' ) ) / 2;
            this.midY = ( this.get( 'stop2' ) + this.get( 'start2' ) ) / 2;
            this.bpp = this.span / this.get( 'viewerSize' ); // bases per pixel
            this.set( 'maxresolution', Math.max( this.maxresolution, this.bpp ) );
            this.set( 'eff_maxres', this._findEffMaxRes() );
            this.updateDisplay( '1' );
            this.updateDisplay( '2' );
            this.controls.hScroll.updateHandle();
            this.controls.vScroll.updateHandle();
            this.heatmapView.updateCanvas();
        },

        toJSON : function(){
            var json = Backbone.Model.prototype.toJSON.call( this );
            return _.pick( json, this.jsonableAttributes );
        },

        /** create a menu for the specified chromosome (1st or 2nd) of interaction pairing */
        addChromMenu : function(){
            this.createChromMenu( '1' );
            if( this.get( 'includes_trans' ) == true ){
                this.createChromMenu( '2' );
            } else {
                // create placeholder that updates when menu1 updates, since there are no trans interactions
                this.createDummyChromMenu();
            };
        },

        /** create view for zoom-in button */
        addZoomIn : function(){
            this.controls.zoomIn = new ControlsView.ZoomIn( { parent : this } );
        },

        /** create view for zoom-out button */
        addZoomOut : function(){
            this.controls.zoomOut = new ControlsView.ZoomOut( { parent : this } );
        },

        /** create two views to diplay X and Y coordinates of cursor position */
        addCursor : function(){
            this.controls.cursorX = new ControlsView.CoordinateDisplay( {
                parent: this,
                el: $( "#mrh-cursor-X" ),
            });
            this.controls.cursorY = new ControlsView.CoordinateDisplay( {
                parent: this,
                el: $( "#mrh-cursor-Y" ),
            });
        },

        /** create view for settings panel */
        addSettings : function(){
            this.controls.settings = new ControlsView.Settings({
                parent: this,
                mincolor: this.get( 'mincolor' ),
                midcolor: this.get( 'midcolor' ),
                maxcolor: this.get( 'maxcolor' ),
            });
        },

        /** add views for horizontal and vertical scroll bars */
        addScrolls : function(){
            this.controls.hScroll = new ControlsView.HScroll( {
                parent : this,
                viewerSize : this.get( 'viewerSize' ),
            });
            this.controls.vScroll = new ControlsView.VScroll( {
                parent : this,
                viewerSize : this.get( 'viewerSize' ),
            });
        },

        /** create select element for menu and call function to fill it with options */
        createChromMenu : function( side ){
            var menuName = 'chromMenu' + side,
                el = $( '#menu' + side + '-container' ),
                element = document.createElement( "select" );
            element.id = "chrom-menu" + side;
            el[0].appendChild( element );
            this.controls[ menuName ] = new ControlsView.ChromosomeMenu( {
                parent: this,
                el: element,
                side: side,
            });
            this.controls[menuName].populateChromMenu( this.get( 'chromosomes' ) );
        },

        /** create span for holding 2nd chromosome text when only cis interactions are available */
        createDummyChromMenu : function(){
            var menuName = 'chromMenu2',
                el = $( '#menu2-container' ),
                element = document.createElement( "span" );
            element.id = "chrom-display2";
            el[0].appendChild( element );
            $( '#chrom-display2' )[0].innerHTML = 'chr' + this.get( 'chrom1' );
            this.on( 'change:chrom1', function(){
                $( '#chrom-display2' )[0].innerHTML = 'chr' + this.get( 'chrom1' );
            }, this );
        },

        /** determine if both chromosomes are valid values and if so, get updated header data */
        checkHeader : function(){
            if( this.loadingHeader == false ){
                var chrom1 = this.get( 'chrom1' ),
                    chrom2 = this.get( 'chrom2' ),
                    chromosomes = this.get( 'chromosomes' );
                if( chromosomes.indexOf( chrom1 ) > -1 && chromosomes.indexOf( chrom2 ) > -1 ){
                    this.loadingHeader = true;
                    this.fetchHeader( chrom1, chrom2 );
                };
            };
        },

        /** create views for displaying coordinates */
        addCoordinateDisplays : function(){
            this.controls.chromDisplay1 = new ControlsView.CoordinateRange( {
                parent: this,
                name: "position-display1",
                axis: "1",
                otherAxis: "2",
            });
            this.controls.chromDisplay2 = new ControlsView.CoordinateRange( {
                parent: this,
                name: "position-display2",
                axis: "2",
                otherAxis: "1",
            });
        },

        /** update the coordinates in the coordinate display view */
        updateDisplay : function( side ){
            this.controls[ 'chromDisplay' + side ].updateDisplay();
        },

        /** update the coordinates in the cursor display view */
        updateCursor : function( e ){
            if( this.heatmapView.dragging == false ){
                var chr = this.get( 'chrom1' ),
                    mid = this.get( 'start1' ) + ( e.pageX - this.controls.hScroll.mouseOffset + 0.5 ) * this.bpp;
                this.controls.cursorX.updateCursor( chr, mid );
                chr = this.get( 'chrom2' ),
                mid = this.get( 'start2' ) + ( e.pageY - this.controls.vScroll.mouseOffset + 0.5 ) * this.bpp;
                this.controls.cursorY.updateCursor( chr, mid );
            };
        },

        /** clear coordinates in the cursor display view */
        clearCursor : function(){
            this.controls.cursorX.clearCursor();
            this.controls.cursorY.clearCursor();
        },

        /** using header values, set limits, initial coordinates, resolutions */
        setInitialValues : function( header ){
            this.minresolution = this.header.lres;
            this.maxresolution = this.header.hres;
            if( this.get( 'chrom1' ) == this.get( 'chrom2') ){
                this.minX = this.header.start;
                this.maxX = this.header.stop;
                this.midX = ( this.minX + this.maxX ) / 2;
                this.minY = this.header.start;
                this.maxY = this.header.stop;
                this.midY = ( this.minY + this.maxY ) / 2;
            } else {
                this.minX = this.header.start1;
                this.maxX = this.header.stop1;
                this.midX = ( this.minX + this.maxX ) / 2;
                this.minY = this.header.start2;
                this.maxY = this.header.stop2;
                this.midY = ( this.minY + this.maxY ) / 2;
                if( ( this.maxY - this.minY ) < ( this.maxX - this.minX ) ){
                    var span = ( this.maxX - this.minX ) / 2;
                    this.minY = this.midY - span;
                    this.maxY = this.midY + span;
                } else {
                    var span = ( this.maxY - this.minY ) / 2;
                    this.minX = this.midX - span;
                    this.maxX = this.midX + span;
                };
            };
            this.span = this.maxX - this.minX;
            this.heatmapView.model.resetCanvases();
            this.numLevels = 0;
            var i = this.minresolution;
            while( i >= this.maxresolution ){
                this.numLevels += 1;
                i /= 2;
            };
            this.totalSpan = this.maxX - this.minX
            this.set( 'start1', this.minX );
            this.set( 'stop1', this.maxX );
            this.set( 'start2', this.minY );
            this.set( 'stop2', this.maxY );
            this.set( 'minresolution', this.minresolution );
            this.bpp = this.span / this.get( 'viewerSize' ); // bases per pixel
            this.set( 'maxresolution', Math.max( this.maxresolution, this.bpp ) );
            this.set( 'eff_maxres', this._findEffMaxRes() );
            var element = $( "#mrh-mincolor-score" ),
                score = this.header.minscore;
            this.controls.settings.minScore = score;
            element[0].innerHTML = score.toFixed( 2 );
            this.header.mincolor = this._hexToList( this.controls.settings.minColor );
            element = $( "#mrh-midcolor-score" );
            score = ( this.header.minscore + this.header.maxscore ) / 2.0;
            this.controls.settings.midScore = score;
            this.header.midscore = score;
            this.header.scorespan = this.header.maxscore - this.header.minscore;
            element[0].innerHTML = score.toFixed( 2 );
            this.header.midcolor = this._hexToList( this.controls.settings.midColor );
            element = $( "#mrh-maxcolor-score" );
            score = this.header.maxscore;
            this.controls.settings.maxScore = score;
            element[0].innerHTML = score.toFixed( 2 );
            this.header.maxcolor = this._hexToList( this.controls.settings.maxColor );
            this.minCanvasRes = this.get( 'eff_maxres' );
            this.loadInitialHeatmap();
            this.trigger( 'updateViewer' );
        },

        loadInitialHeatmap : function(){
            var JSON = this.toJSON();
            JSON.maxresolution = this.minresolution;
            JSON.eff_maxres = this.minresolution;
            this.heatmapView.model.loadNewCanvases( {}, JSON );
        },

        _rgbToList : function( color ){
            var values = [],
                temp = color.split(','),
                value;
            value = temp[0].replace( 'rgb(', '' );
            values.push( parseInt( value ) );
            value = temp[1];
            values.push( parseInt( value ) );
            value = temp[2];
            values.push( parseInt( value ) );
            return values;
        },

        _rgbToHex : function( color ){
            var values = '#',
                temp = color.split(','),
                value;
            value = temp[0].replace( 'rgb(', '' );
            values += this._padString( parseInt( value ).toString( 16 ) );
            value = temp[1];
            values += this._padString( parseInt( value ).toString( 16 ) );
            value = temp[2];
            values += this._padString( parseInt( value ).toString( 16 ) );
            return values;
        },

        _hexToList : function( color ){
            var values = [];
            if( color.length == 4 ){
                values[0] = parseInt( '0x' + color.substring( 1, 2 ) + color.substring( 1, 2 ) );
                values[1] = parseInt( '0x' + color.substring( 2, 3 ) + color.substring( 2, 3 ) );
                values[2] = parseInt( '0x' + color.substring( 3, 4 ) + color.substring( 3, 4 ) );
            } else {
                values[0] = parseInt( '0x' + color.substring( 1, 3 ) );
                values[1] = parseInt( '0x' + color.substring( 3, 5 ) );
                values[2] = parseInt( '0x' + color.substring( 5, 7 ) );
            };
            return values;
        },

        _listToHex : function( values ){
            var color = '#';
            _.each( values, value, function(){
                color += this._padString( value.toString( 16 ) );
            });
            return color;
        },

        _findEffMaxRes : function(){
            var eff_maxres = this.get( 'minresolution' );
            while( eff_maxres / 2 > this.get( 'maxresolution' ) ){
                eff_maxres /= 2;
            };
            return eff_maxres;
        },

        _padString : function( string ){
            if( string.length == 1 ){
                string = '0' + string;
            };
            return string;
        },

        /** if possible, zoom in view */
        updateZoomIn : function(){
            if( this.span >= this.maxresolution * 2.0 ){
                var qspan = this.span / 4.0;
                this.set( 'start1', this.midX - qspan );
                this.set( 'stop1', this.midX + qspan );
                this.set( 'start2', this.midY - qspan );
                this.set( 'stop2', this.midY + qspan );
                this.trigger( 'updateViewer' );
            };
        },

        /** if possible, zoom out view */
        updateZoomOut : function(){
            if( this.span <= this.totalSpan ){
                var newSpan = Math.min(this.totalSpan / 2, this.span),
                    start = this.midX - newSpan,
                    stop = this.midX + newSpan;
                if( start < this.minX ){
                    start = this.minX;
                    stop = start + newSpan * 2;
                }
                if( stop > this.maxX ){
                    stop = this.maxX;
                    start = stop - newSpan * 2;
                }
                this.set( 'start1', start );
                this.set( 'stop1', stop );
                start = this.midY - newSpan,
                stop = this.midY + newSpan;
                if( start < this.minY ){
                    start = this.minY;
                    stop = start + newSpan * 2;
                }
                if( stop > this.maxY ){
                    stop = this.maxY;
                    start = stop - newSpan * 2;
                }
                this.set( 'start2', start );
                this.set( 'stop2', stop );
                this.trigger( 'updateViewer' );
            };
        },

        /** when horizontal drag bar is clicked, run this */
        dragX : function() {
            self = this;
            document.body.onmousemove = function( ){
                self.controls.hScroll.drag( event );
            };
            document.body.onmouseup = function(){
                self.controls.hScroll.dragging = false;
                document.body.onmousemove = null;
            };
        },

        /** when vertical drag bar is clicked, run this */
        dragY : function() {
            self = this;
            document.body.onmousemove = function( ){
                self.controls.vScroll.drag( event );
            };
            document.body.onmouseup = function(){
                self.controls.vScroll.dragging = false;
                document.body.onmousemove = null;
            };
        },

        /** when hetamap is clicked, run this */
        dragHeatmap : function() {
            self = this;
            document.body.onmousemove = function( ){
                self.heatmapView.drag( event );
            };
            document.body.onmouseup = function(){
                self.heatmapView.dragging = false;
                document.body.onmousemove = null;
                if( self.heatmapView.waiting == false ){
                    self.heatmapView.el.style.cursor = '-webkit-grab';
                };
            };
        },

        /** Get chromosome data from the server using the dataset id */
        fetchChromosomes : function(){
            var model = this,
                root = ( window.Galaxy? Galaxy.options.root : '/' ),
                url = root + 'api/datasets/' + this.get( 'dataset_id' ),
                params = { data_type : 'raw_data', provider : 'json', chromosomes : true },
                xhr = jQuery.ajax( url, { data : params } );
            return xhr
                .done( function( response ){
                    _.each( response.data[0], function(x, y){
                        model.set(y, x);
                    });
                    model.addChromMenu();
                })
                .fail( function(){
                    model.trigger( 'error', arguments );
                });
        },

        /** Get header data for a specific chromosome(s) from the server */
        fetchHeader : function( chrom1, chrom2 ){
            var model = this,
                root = ( window.Galaxy? Galaxy.options.root : '/' ),
                url = root + 'api/datasets/' + this.get( 'dataset_id' ),
                params = { data_type : 'raw_data', provider : 'json', header : true,
                    'chrom1' : chrom1, 'chrom2' : chrom2 },
                xhr = jQuery.ajax( url, { data : params });
            return xhr
                .done( function( response ){
                    model.header = response.data[0];
                    model.trigger( 'header_loaded' );
                    model.loadingHeader = false;
                })
                .fail( function(){
                    model.trigger( 'error', arguments );
                });
        },
    });
});