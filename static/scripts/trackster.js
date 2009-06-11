var DENSITY = 1000;

var View = function( chr, length, low, high ) {
    this.chr = chr;
    this.length = length;
    this.low = low;
    this.high = high;
};
$.extend( View.prototype, {
    move: function ( new_low, new_high ) {
        this.low = Math.max( 0, Math.floor( new_low ) );
        this.high = Math.min( this.length, Math.ceil( new_high ) );
    },
    zoom_in: function ( factor ) {
        var center = ( this.low + this.high ) / 2;
        var range = this.high - this.low;
        var diff = range / factor / 2;
        this.low = Math.floor( center - diff );
        this.high = Math.ceil( center + diff );
        if (this.high - this.low < 1 ) {
            this.high = this.low + 1;
        }
    },
    zoom_out: function ( factor ) {
        var center = ( this.low + this.high ) / 2;
        var range = this.high - this.low;
        var diff = range * factor / 2;
        this.low = Math.floor( Math.max( 0, center - diff ) );
        this.high = Math.ceil( Math.min( this.length, center + diff ) );
    },
    left: function( factor ) {
        var range = this.high - this.low;
        var diff = Math.floor( range / factor );
        if ( this.low - diff < 0 ) {
            this.low = 0;
            this.high = this.low + range;
        } else {
            this.low -= diff;
            this.high -= diff;
        }
    },
    right: function ( factor ) {
        var range = this.high - this.low;
        var diff = Math.floor( range / factor );
        if ( this.high + diff > this.length ) {
            this.high = this.length;
            this.low = this.high - range;
        } else {
            this.low += diff;
            this.high += diff;
        }
    }
});

var Track = function ( name, view, parent_element ) {
    this.name = name;
    this.view = view;
    this.parent_element = parent_element;
    this.make_container();
};
$.extend( Track.prototype, {
    make_container : function () {
        this.header_div = $("<div class='track-header'>");
        this.header_div.text( this.name );
        this.content_div = $("<div class='track-content'>");
        this.container_div = $("<div class='track'></div>");
        this.container_div.append( this.header_div );
        this.container_div.append( this.content_div );
        this.parent_element.append( this.container_div );
    }
});

var TiledTrack = function( name, view, parent_element ) {
    Track.call( this, name, view, parent_element );
    // For caching
    this.last_resolution = null;
    this.last_w_scale = null;
    this.tile_cache = {};
};
$.extend( TiledTrack.prototype, Track.prototype, {
    draw: function() {
        var low = this.view.low,
            high = this.view.high,
            range = high - low;

        var resolution = Math.pow( 10, Math.ceil( Math.log( range / DENSITY ) / Math.log( 10 ) ) );
        resolution = Math.max( resolution, 1 );
        resolution = Math.min( resolution, 100000 );

	var parent_element = $("<div style='position: relative;'></div>");
        this.content_div.children( ":first" ).remove();
        this.content_div.append( parent_element );

        var w = this.content_div.width(),
            h = this.content_div.height(),
	    w_scale = w / range,
	    old_tiles = {},
            new_tiles = {};

        // If resolution and scale are unchanged, try to reuse tiles
        if ( this.last_resolution == resolution && this.last_w_scale == w_scale ) {
            old_tiles = this.tile_cache;
        }

        var tile_element;
        // Index of first tile that overlaps visible region
        var tile_index = Math.floor( low / resolution / DENSITY );
        var max_height = 0;
        while ( ( tile_index * 1000 * resolution ) < high ) {
            // Check in cache
            if ( tile_index in old_tiles ) {
                // console.log( "tile from cache" );
                tile_element = old_tiles[tile_index];
                var tile_low = tile_index * DENSITY * resolution;
                tile_element.css( {
                    left: ( tile_low - this.view.low ) * w_scale
                });
                // Our responsibility to move the element to the new parent
                parent_element.append( tile_element );
            } else {
                // console.log( "new tile" );
                tile_element = this.draw_tile( resolution, tile_index, parent_element, w_scale, h );
            }
            if ( tile_element ) {
                new_tiles[tile_index] = tile_element;
                max_height = Math.max( max_height, tile_element.height() );
            }
            tile_index += 1;
        }

        parent_element.css( "height", max_height );

        this.last_resolution = resolution;
        this.last_w_scale = w_scale;
        this.tile_cache = new_tiles;
    }
});

var DataCache = function( type, track, view ) {
    this.type = type;
    this.track = track;
    this.view = view;
    this.cache = Object();
};
$.extend( DataCache.prototype, {
    get: function( resolution, position ) {
        var cache = this.cache;
        if ( ! ( cache[resolution] && cache[resolution][position] ) ) {
            if ( ! cache[resolution] ) {
                cache[resolution] = Object();
            }
            var low = position * DENSITY * resolution;
            var high = ( position + 1 ) * DENSITY * resolution;
            cache[resolution][position] = { state: "loading" };
	    // use closure to preserve this and parameters for getJSON
	    var fetcher = function (ref) {
	      return function () {
		$.getJSON( TRACKSTER_DATA_URL + ref.type, { chrom: ref.view.chr, low: low, high: high, dataset_id: ref.track.dataset_id }, function ( data ) {
		  if( data == "pending" ) {
		    setTimeout( fetcher, 5000 );
		  } else {
		    cache[resolution][position] = { state: "loaded", values: data };
		  }
		  $(document).trigger( "redraw" );
		});
	      };
	    }(this);
	    fetcher();
        }
	return cache[resolution][position];
    }
});

var LineTrack = function ( name, view, parent_element, dataset_id ) {
    Track.call( this, name, view, parent_element );
    this.container_div.addClass( "line-track" );
    this.dataset_id = dataset_id;
    this.cache = new DataCache( "", this, view );
};
$.extend( LineTrack.prototype, TiledTrack.prototype, {
    make_container: function () {
        Track.prototype.make_container.call( this );
        this.content_div.css( "height", 100 );
    },
    draw_tile: function( resolution, tile_index, parent_element, w_scale, h_scale ) {
        var tile_low = tile_index * DENSITY * resolution,
            tile_high = ( tile_index + 1 ) * DENSITY * resolution,
            tile_length = DENSITY * resolution;
        var chunk = this.cache.get( resolution, tile_index );
        var element;
        if ( chunk.state == "loading" ) {
            element = $("<div class='loading tile'></div>");
        } else {
            element = $("<canvas class='tile'></canvas>");
        }
        element.css( {
            position: "absolute",
            top: 0,
            left: ( tile_low - this.view.low ) * w_scale,
            width: Math.ceil( tile_length * w_scale ),
            height: 100
        });
        parent_element.append( element );
        // Chunk is still loading, do noting
        if ( chunk.state == "loading" ) {
            in_path = false;
            return null;
        }
        var canvas = element;
        canvas.get(0).width = canvas.width();
        canvas.get(0).height = canvas.height();
        var ctx = canvas.get(0).getContext("2d");
        var in_path = false;
        ctx.beginPath();
        var data = chunk.values;
        for ( var i = 0; i < data.length - 1; i++ ) {
            var x1 = data[i][0] - tile_low;
            var y1 = data[i][1];
            var x2 = data[i+1][0] - tile_low;
            var y2 = data[i+1][1];
	    console.log( x1, y1, x2, y2 );
            // Missing data causes us to stop drawing
            if ( isNaN( y1 ) || isNaN( y2 ) ) {
                in_path = false;
            } else {
                // Translate
                x1 = x1 * w_scale;
                x2 = x2 * w_scale;
                y1 = h_scale - y1 * ( h_scale );
                y2 = h_scale - y2 * ( h_scale );
                if ( in_path ) {
                    ctx.lineTo( x1, y1, x2, y2 );
                } else {
                    ctx.moveTo( x1, y1, x2, y2 );
                    in_path = true;
                }
           }
        }
        ctx.stroke();
        return element;
    }
});

var LabelTrack = function ( view, parent_element ) {
    Track.call( this, null, view, parent_element );
    this.container_div.addClass( "label-track" );
};
$.extend( LabelTrack.prototype, Track.prototype, {
    draw: function() {
        var view = this.view,
            range = view.high - view.low,
            tickDistance = Math.floor( Math.pow( 10, Math.floor( Math.log( range ) / Math.log( 10 ) ) ) ),
            position = Math.floor( view.low / tickDistance ) * tickDistance,
	    width = this.content_div.width(),
	    new_div = $("<div style='position: relative; height: 1.3em;'></div>");
        while ( position < view.high ) {
            var screenPosition = ( position - view.low ) / range * width;
            new_div.append( $("<div class='label'>" + position + "</div>").css( {
                position: "absolute",
                // Reduce by one to account for border
                left: screenPosition - 1
            }) );
            position += tickDistance;
        }
        this.content_div.children( ":first" ).remove();
        this.content_div.append( new_div );
    }
});

var itemHeight = 13,
    itemPad = 3,
    thinHeight = 7,
    thinOffset = 3;

var FeatureTrack = function ( name, view, parent_element,dataset_id ) {
    Track.call( this, name, view, parent_element );
    this.container_div.addClass( "feature-track" );
    this.dataset_id = dataset_id;
    this.cache = new DataCache( "", this, view );
};
$.extend( FeatureTrack.prototype, TiledTrack.prototype, {
    get_data_async: function() {
        var track = this;
        $.getJSON( "data", { chr: this.view.chr, dataset_id: this.dataset_id }, function ( data ) {
            track.values = data;
            track.draw();
        });
    },
    draw_tile: function( resolution, tile_index, parent_element, w_scale, h_scale ) {
        var tile_low = tile_index * DENSITY * resolution,
            tile_high = ( tile_index + 1 ) * DENSITY * resolution,
            tile_length = DENSITY * resolution;

        var view = this.view,
            range = view.high - view.low,
            width = this.content_div.width(),
            slots = [],
            new_div = $("<div class='tile' style='position: relative;'></div>");

        var chunk = this.cache.get( resolution, tile_index );
        if ( chunk.state == "loading" ) {
	  parent_element.addClass("loading");
          return null;
        } else {
	  parent_element.removeClass("loading");
	}
        var values = chunk.values;

        for ( var index in values ) {
            var value = values[index];
            var start = value[1], end = value[2], strand = value[5];
            // Determine slot based on entire feature and label
            var screenStart = ( start - tile_low ) * w_scale;
            var screenEnd = ( end - tile_low ) * w_scale;
            var screenWidth = screenEnd - screenStart;
            var screenStartWithLabel = screenStart;
            // Determine slot
            var slot = slots.length;
            for ( i in slots ) {
                if ( slots[i] < screenStartWithLabel ) {
                    slot = i;
                    break;
                }
            }
            slots[slot] = Math.ceil( screenEnd );
            var feature_div = $("<div class='feature'></div>").css( {
                position: 'absolute',
                left: screenStart,
                top: (slot*(itemHeight+itemPad)),
                height: itemHeight,
                width: Math.max( screenWidth, 1 )
            });
            new_div.append( feature_div );
        }
        new_div.css( {
            position: "absolute",
            top: 0,
            left: ( tile_low - this.view.low ) * w_scale,
            width: Math.ceil( tile_length * w_scale ),
            height: slots.length * ( itemHeight + itemPad ) + itemPad
        });
        parent_element.append( new_div );
        return new_div;
    }
});

var TrackLayout = function ( view ) {
    this.view = view;
    this.tracks = [];
};
$.extend( TrackLayout.prototype, {
    add: function ( track ) {
        this.tracks.push( track );
    },
    redraw : function () {
        for ( var index in this.tracks ) {
	  this.tracks[index].draw();
        }
        // Overview
        $("#overview-box").css( {
            left: ( this.view.low / this.view.length ) * $("#overview-viewport").width(),
            width: Math.max( 1, ( ( this.view.high - this.view.low ) / this.view.length ) * $("#overview-viewport").width() )
        }).show();
        $("#low").text( this.view.low );
        $("#high").text( this.view.high );
    }
});