define([], function(){
	return Backbone.Model.extend({
		
		initialize : function( options ){
			this.data = {};
			this.parent = options.parent;
			this.view = options.view;
			this.viewerSize = options.viewerSize;
			this.canvasSize = options.canvasSize;
			this.dataset_id = options.dataset_id;
            this.outstandingRequests = 0;
			this.set( 'renderQueue', [] );
			this.set( 'fetchQueue', [] );
		},

		resetCanvases : function(){
			this.canvases = {};
			this.plotQueue = {};
            this.set( 'renderQueue', [] );
            this.set( 'fetchQueue', [] );
			this.spans = {};
			var res = this.parent.minresolution,
				span = this.parent.span * this.canvasSize / this.viewerSize;
			while( res >= this.parent.maxresolution ){
				this.canvases[ res ] = {};
				this.plotQueue[ res ] = {};
				this.spans[ res ] = res * this.canvasSize;
				res /= 2;
				span /= 2;
			};
		},

		loadCachedCanvases : function( canvases, parameters ){
			if( _.has( this.canvases, parameters.eff_maxres ) == false ){
				return canvases
			};
			var stepSize = parameters.eff_maxres * this.canvasSize,
				xstart = ( Math.floor( ( parameters.start1 - this.parent.minX ) / stepSize ) *
					stepSize + this.parent.minX ),
				xstop  = ( Math.floor( ( parameters.stop1 - this.parent.minX - 1.0 ) / stepSize + 1 ) *
					stepSize + this.parent.minX ),
				ystart = ( Math.floor( ( parameters.start2 - this.parent.minY ) / stepSize ) *
					stepSize + this.parent.minY ),
				ystop  = ( Math.floor( ( parameters.stop2 - this.parent.minY - 1.0 ) / stepSize + 1 ) *
					stepSize + this.parent.minY ),
				X = xstart,
				Y, name, revname, added;
			if( _.has( canvases, parameters.eff_maxres ) == false ){
				canvases[ parameters.eff_maxres ] = {}
			};
			if( parameters.chrom1 == parameters.chrom2 ){
				while( X < xstop ){
					Y = ystart;
					while( Y < ystop ){
						added = false;
						name = X.toString() + '_' + Y.toString();
						if( _.has( canvases[ parameters.eff_maxres ], name ) == true ){
							added = true;
						};
						if( added == false &&
							_.has( this.canvases[ parameters.eff_maxres ], name ) == true &&
							this.canvases[ parameters.eff_maxres ][name] != null ){
							canvases[ parameters.eff_maxres ][ name ] = this.canvases[ parameters.eff_maxres ][ name ];
							added = true;
						};
						if( added == false ){
							canvases = this.loadCachedCanvases( canvases, {
								start1: X,
								stop1: X + stepSize,
								start2: Y,
								stop2: Y + stepSize,
								chrom1: parameters.chrom1,
								chrom2: parameters.chrom2,
								minresolution: parameters.minresolution,
								maxresolution: parameters.maxresolution * 2,
								eff_maxres: parameters.eff_maxres * 2
							});
						};
						Y += stepSize;
					};
					X += stepSize;
				};
			} else {
				while( X < xstop ){
					Y = ystart;
					while( Y < ystop ){
						added = false;
						name = X.toString() + '_' + Y.toString();
						if( _.has( canvases[ parameters.eff_maxres ], name ) == true ){
							added = true;
						};
						if( added == false &&
							_.has( this.canvases[ parameters.eff_maxres ], name ) == true &&
							this.canvases[ parameters.eff_maxres ][name] != null ){
							canvases[ parameters.eff_maxres ][ name ] = this.canvases[ parameters.eff_maxres ][ name ];
							added = true;
						};
						if( added == false ){
							canvases = this.loadCachedCanvases( canvases, {
								start1: X,
								stop1: X + stepSize,
								start2: Y,
								stop2: Y + stepSize,
								chrom1: parameters.chrom1,
								chrom2: parameters.chrom2,
								eff_maxres: parameters.eff_maxres * 2
							});
						};
						Y += stepSize;
					};
					X += stepSize;
				};
			};
			return canvases;
		},

		loadNewCanvases : function( canvases, parameters ){
			var stepSize = parameters.eff_maxres * this.canvasSize,
				xstart = ( Math.floor( ( parameters.start1 - this.parent.minX ) / stepSize ) *
					stepSize + this.parent.minX ),
				xstop  = ( Math.floor( ( parameters.stop1 - this.parent.minX - 1 ) / stepSize + 1 ) *
					stepSize + this.parent.minX ),
				ystart = ( Math.floor( ( parameters.start2 - this.parent.minY ) / stepSize ) *
					stepSize + this.parent.minY ),
				ystop  = ( Math.floor( ( parameters.stop2 - this.parent.minY - 1 ) / stepSize + 1 ) *
					stepSize + this.parent.minY ),
				X = xstart,
				name = '',
				newCanvas = null;
			while( X < xstop ){
				Y = ystart;
				while( Y < ystop ){
					name = X.toString() + '_' + Y.toString();
					if( _.has( canvases, name ) == false &&
						_.has( this.canvases[ parameters.eff_maxres ], name ) == false ){
						newCanvas = this.plotCanvas( {
							start1        : X,
							stop1         : X + stepSize,
							start2        : Y,
							stop2         : Y + stepSize,
							chrom1        : parameters.chrom1,
							chrom2        : parameters.chrom2,
							minresolution : parameters.minresolution,
							maxresolution : parameters.maxresolution,
							eff_maxres    : parameters.eff_maxres,
						}, name );
						this.canvases[ parameters.eff_maxres ][ name ] = null;
						this.plotQueue[ parameters.eff_maxres ][ name ] = newCanvas;
						if( parameters.chrom1 == parameters.chrom2 && X != Y ){
							var name2 = Y.toString() + '_' + X.toString();
							this.canvases[ parameters.eff_maxres ][ name2 ] = null;
						};
					};
					Y += stepSize;
				};
				X += stepSize;
			};
		},

		plotCanvas : function( parameters, name ){
			var canvas = document.createElement( 'canvas' ),
				context = canvas.getContext( '2d' ),
				queue = this.get( 'fetchQueue' );
			canvas.width = this.canvasSize;
			canvas.height = this.canvasSize;
            context.imageSmoothingEnabled = false;
            context.alpha = false;
			queue.push( { parameters: parameters, context: context, name: name } );
			this.trigger( 'fetchQueueUpdated' );
			return canvas;
		},

		fillCanvas : function( parameters, context, name, squares, canvases ){
            // stop rendering from previous selection if still in process when new selection is made
            if( parameters.chrom1 != this.parent.get( 'chrom1' ) ||
                parameters.chrom2 != this.parent.get( 'chrom2' ) ) { return null; };
			var x, xspan, y, yspan, color,
				span = parameters.stop1 - parameters.start1,
				self = this,
				queue = this.get( 'renderQueue' );
            // draw previously cached lower resolution values
            _.each( _.keys( canvases ), function( res ){
                _.each( _.keys( canvases[ res ] ), function( key ){
                    var temp = key.split('_'),
                        canvasX = parseInt(temp[0]),
                        canvasY = parseInt(temp[1]),
                        X = ( canvasX - parameters.start1 ) / parameters.eff_maxres,
                        Y = ( canvasY - parameters.start2 ) / parameters.eff_maxres;
                        size = res / parameters.eff_maxres * this.canvasSize;
                    context.drawImage( canvases[ res ][ key ], X, Y, size, size );
                });
            });
            // draw newly-loaded data, starting from the largest to smallest size squares, by color
			_.each( squares, function( level ){
                _.each( _.keys( level ), function( color ){
                    context.fillStyle = color;
                    _.each( level[ color ], function( square ){
        				x = ( square[0] - parameters.start1 ) / parameters.eff_maxres;
        				xspan = square[1] / parameters.eff_maxres;
        				y = ( square[2] - parameters.start2 ) / parameters.eff_maxres;
        				yspan = square[3] / parameters.eff_maxres;
        				context.fillRect( x, y, xspan, yspan );
                    });
                });
			});
			this.canvases[ parameters.eff_maxres ][ name ] = this.plotQueue[ parameters.eff_maxres ][ name ];
			queue.push( _.extend( parameters, { name: name } ) );
			this.trigger( 'renderQueueUpdated' );
			if( parameters.chrom1 == parameters.chrom2 && parameters.start1 != parameters.start2 ){
				var newCanvas = document.createElement( 'canvas' ),
					newContext = newCanvas.getContext( '2d' ),
					temp = name.split( '_' ),
					newName = temp[1] + '_' + temp[0];
				newCanvas.width = this.canvasSize;
				newCanvas.height = this.canvasSize;
				newContext.scale( 1, -1 );
				newContext.rotate( -Math.PI / 2.0 );
				newContext.drawImage( this.canvases[ parameters.eff_maxres ][ name ], 0, 0 );
				this.canvases[ parameters.eff_maxres ][ newName ] = newCanvas;
				queue.push( _.extend( parameters, { name: newName } ) );
				this.trigger( 'renderQueueUpdated' );
			};
		},

		getColor : function( value ){
			var scaled = Math.max( -1, Math.min( 1, ( ( value - this.parent.header.minscore ) /
				( this.parent.header.scorespan ) * 2.0 - 1.0 ) ) ),
                inv_scaled, R, G, B;
			if( scaled > 0 ){
                inv_scaled = 1.0 - scaled;
                R = Math.round( this.parent.header.maxcolor[0] * scaled +
                        this.parent.header.midcolor[0] * inv_scaled );
                G = Math.round( this.parent.header.maxcolor[1] * scaled +
                        this.parent.header.midcolor[1] * inv_scaled );
                B = Math.round( this.parent.header.maxcolor[2] * scaled +
                        this.parent.header.midcolor[2] * inv_scaled );
			} else {
                scaled = -scaled;
                inv_scaled = 1.0 - scaled;
                R = Math.round( this.parent.header.mincolor[0] * scaled +
                        this.parent.header.midcolor[0] * inv_scaled );
                G = Math.round( this.parent.header.mincolor[1] * scaled +
                        this.parent.header.midcolor[1] * inv_scaled );
                B = Math.round( this.parent.header.mincolor[2] * scaled +
                        this.parent.header.midcolor[2] * inv_scaled );
			};
            return 'rgb(' + R.toString() + ',' + G.toString() + ',' + B.toString() + ')';
		},

	    /** Get interaction data for a specific chromosome(s), coordinates, and resolutions from the server */
	    fetchInteractions : function(){
	        var self = this,
	    	    queue = self.get( 'fetchQueue' ),
	            root = ( window.Galaxy? Galaxy.options.root : '/' ),
	            url = root + 'api/datasets/' + this.dataset_id,
	            params = { data_type : 'raw_data', provider : 'json' },
                item, xhr, squares, color, i, canvases, res;
            if( this.outstandingRequests < 1 && queue.length > 0 ){
                item = queue.pop();
        		if( _.has( this.canvases[ item.parameters.eff_maxres ], item.name ) == false ||
                    this.canvases[ item.parameters.eff_maxres ][ item.name ] == null ){
                    this.outstandingRequests += 1
                    canvases = {};
                    this.loadCachedCanvases( canvases, item.parameters );
                    i = item.parameters.minresolution;
                    while( i > item.parameters.maxresolution ){
                        if( _.has( canvases, i ) == true && _.keys( canvases[ i ] ).length > 0 ){
                            item.parameters.minresolution = i / 2;
                        };
                        i /= 2;
                    };
    		        xhr = jQuery.ajax( { url: url, data : _.extend( params, item.parameters ) } );
    		        return xhr
    		            .done( function( response ){
                            self.outstandingRequests -= 1;
                            self.trigger( 'fetchQueueUpdated' );
                            squares = [];
                            i = 0;
                            while( i < self.parent.numLevels ){
                                squares[ i ] = {};
                                i += 1;
                            };
    		                _.each( response.data, function( x ){
                                color = self.getColor( x[ 4 ] );
                                if( _.has( squares[ x[ 5 ] ], color ) == false ){
                                    squares[ x[ 5 ] ][ color ] = [];
                                }
    		                    squares[ x[ 5 ] ][ color ].push( x );
    		                });
    		                self.fillCanvas( item.parameters, item.context, item.name, squares, canvases );
    		            })
    		            .fail( function(){
    		                self.trigger( 'error', arguments );
    		            });
    	        };
            };
	    },
	});
});