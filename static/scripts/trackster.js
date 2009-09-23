/* Trackster
    2009, James Taylor, Kanwei Li
*/

var DENSITY = 1000;

var DataCache = function( type, track ) {
    this.type = type;
    this.track = track;
    this.cache = Object();
};
$.extend( DataCache.prototype, {
    get: function( resolution, position ) {
        var cache = this.cache;
        if ( !( cache[resolution] && cache[resolution][position] ) ) {
            if ( !cache[resolution] ) {
                cache[resolution] = Object();
            }
            var low = position * DENSITY * resolution;
            var high = ( position + 1 ) * DENSITY * resolution;
            cache[resolution][position] = { state: "loading" };
            
            $.getJSON( data_url, { track_type: this.track.track_type, chrom: this.track.view.chrom, low: low, high: high, dataset_id: this.track.dataset_id }, function ( data ) {
                if( data == "pending" ) {
                    setTimeout( fetcher, 5000 );
                } else {
                    cache[resolution][position] = { state: "loaded", values: data };
                }
                $(document).trigger( "redraw" );
            });
        }
        return cache[resolution][position];
    }
});

var View = function( chrom, max_length ) {
    this.chrom = chrom;
    this.tracks = [];
    this.max_low = 0;
    this.max_high = max_length;
    this.low = this.max_low;
    this.high = this.max_high;
    this.length = this.max_high - this.max_low;
};
$.extend( View.prototype, {
    add_track: function ( track ) {
        track.view = this;
        this.tracks.push( track );
        if (track.init) { track.init(); }
    },
    redraw: function () {
        // Overview
        $("#overview-box").css( {
            left: ( this.low / this.length ) * $("#overview-viewport").width(),
            width: Math.max( 4, ( ( this.high - this.low ) / this.length ) * $("#overview-viewport").width() )
        }).show();
        $("#low").text( this.low );
        $("#high").text( this.high );
        for ( var i in this.tracks ) {
            this.tracks[i].draw();
        }
        $("#bottom-spacer").remove();
        $("#viewport").append('<div id="bottom-spacer" style="height: 200px;"></div>');
    },
    move: function ( new_low, new_high ) {
        this.low = Math.max( this.max_low, Math.floor( new_low ) );
        this.high = Math.min( this.length, Math.ceil( new_high ) );
    },
    zoom_in: function ( factor, point ) {
        var range = this.high - this.low;
        var diff = range / factor / 2;
        
        if (point == undefined) {
            var center = ( this.low + this.high ) / 2;
        } else {
            // console.log(100*point/$(document).width());
            var center = this.low + range * point / $(document).width();
        }
        // console.log(center);
        this.low = Math.floor( center - diff );
        this.high = Math.ceil( center + diff );
        if (this.low < this.max_low) {
            this.low = this.max_low;
            this.high = range / factor;
        } else if (this.high > this.max_high) {
            this.high = this.max_high;
            this.low = this.max_high - range / factor;
            // console.log(this.high, this.low);
        } 
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

var Track = function ( name, parent_element ) {
    this.name = name;
    this.parent_element = parent_element;
    this.make_container();
};
$.extend( Track.prototype, {
    make_container: function () {
        this.header_div = $("<div class='track-header'>").text( this.name );;
        this.content_div = $("<div class='track-content'>");
        this.container_div = $("<div class='track'></div>").append( this.header_div ).append( this.content_div );
        this.parent_element.append( this.container_div );
    }
});

var TiledTrack = function() {
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
                tile_element = this.draw_tile( resolution, tile_index, parent_element, w_scale, h );
            }
            if ( tile_element ) {
                // console.log( typeof(tile_element) );
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

var LineTrack = function ( name, dataset_id, height ) {
    Track.call( this, name, $("#viewport") );
    
    this.track_type = "line";
    this.height_px = (height ? height : 100);
    this.container_div.addClass( "line-track" );
    this.dataset_id = dataset_id;
    this.cache = new DataCache( "", this );
};
$.extend( LineTrack.prototype, TiledTrack.prototype, {
    make_container: function () {
        Track.prototype.make_container.call(this);
        // console.log("height:", this.height_px);
        this.content_div.css( "height", this.height_px );
    },
    init: function() {
        track = this;
        $.getJSON( data_url, { stats: true, track_type: track.track_type, chrom: this.view.chrom, low: null, high: null, dataset_id: this.dataset_id }, function ( data ) {
            // console.log(data);
            if (data) {
                track.min_value = data['min'];
                track.max_value = data['max'];
                track.vertical_range = track.max_value - track.min_value;
                track.view.redraw();
            }
        });
    },
    draw_tile: function( resolution, tile_index, parent_element, w_scale, h_scale ) {
        if (!this.vertical_range) // We don't have the necessary information yet
            return;
            
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
        });
        parent_element.append( element );
        // Chunk is still loading, do nothing
        if ( chunk.state == "loading" ) {
            in_path = false;
            return null;
        }
        var canvas = element;
        canvas.get(0).width = Math.ceil( tile_length * w_scale );
        canvas.get(0).height = this.height_px;
        var ctx = canvas.get(0).getContext("2d");
        var in_path = false;
        ctx.beginPath();
        var data = chunk.values;
        if (!data) return;
        for ( var i = 0; i < data.length - 1; i++ ) {
            var x = data[i][0] - tile_low;
            var y = data[i][1];
            // Missing data causes us to stop drawing
            if ( isNaN( y ) ) {
                in_path = false;
            } else {
                // Translate
                x = x * w_scale;
                y_above_min = y - this.min_value;
                y = y_above_min / this.vertical_range * this.height_px;
                if ( in_path ) {
                    ctx.lineTo( x, y );
                } else {
                    ctx.moveTo( x, y );
                    in_path = true;
                }
            }
        }
        ctx.stroke();
        return element;
    }
});

var LabelTrack = function ( parent_element ) {
    Track.call( this, null, parent_element );
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
            }));
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

var FeatureTrack = function ( name, dataset_id ) {
    Track.call( this, name, $("#viewport") );
    this.track_type = "feature";
    this.container_div.addClass( "feature-track" );
    this.dataset_id = dataset_id;
    this.zo_slots = new Object();
    this.show_labels_scale = 0.01;
    this.showing_labels = false;
};
$.extend( FeatureTrack.prototype, TiledTrack.prototype, {
    
    calc_slots: function( include_labels ) {
        // console.log("num vals: " + this.values.length);
        end_ary = new Array();
        var scale = this.container_div.width() / (this.view.high - this.view.low);
        // console.log(scale);
        if (include_labels) this.zi_slots = new Object();
        var dummy_canvas = $("<canvas></canvas>").get(0).getContext("2d");
        for (var i in this.values) {

            feature = this.values[i];
            f_start = Math.floor( Math.max(this.view.max_low, (feature.start - this.view.max_low) * scale) );
            if (include_labels) {
                f_start -= dummy_canvas.measureText(feature.name).width;
            }

            f_end = Math.ceil( Math.min(this.view.max_high, (feature.end - this.view.max_low) * scale) );
            // if (include_labels) { console.log(f_start, f_end); }
            j = 0;
            while (true) {
                if (end_ary[j] == undefined || end_ary[j] < f_start) {
                    end_ary[j] = f_end;
                    if (include_labels) {
                        this.zi_slots[feature.name] = j;
                    } else {
                        this.zo_slots[feature.name] = j;
                    }
                    break;
                }
                j++;
            }
        }
    },
    
    init: function() {
        var track = this;
        $.getJSON( "getfeature", { 'start': this.view.max_low, 'end': this.view.max_high, 'dataset_id': this.dataset_id, 'chrom': this.view.chrom }, function ( data ) {
            track.values = data;
            track.calc_slots();
            track.slots = track.zo_slots;
            // console.log(track.zo_slots);
            track.draw();
        });
    },
    
    draw_tile: function( resolution, tile_index, parent_element, w_scale, h_scale ) {
        if (!this.values) // Still loading
            return null;
        
        if (w_scale > this.show_labels_scale && !this.showing_labels) {
            this.showing_labels = true;
            if (!this.zi_slots) this.calc_slots(true); // Once we zoom in enough, show name labels
            this.slots = this.zi_slots;
        } else if (w_scale <= this.show_labels_scale && this.showing_labels) {
            this.showing_labels = false;
            this.slots = this.zo_slots;
        }
        // console.log(this.slots);
        
        var tile_low = tile_index * DENSITY * resolution,
            tile_high = ( tile_index + 1 ) * DENSITY * resolution,
            tile_length = DENSITY * resolution;
        // console.log(tile_low, tile_high, tile_length, w_scale);
        var view = this.view,
            range = view.high - view.low,
            width = Math.ceil( tile_length * w_scale ),
            slots = new Array(),
            height = 200,
            new_canvas = $("<canvas class='tile'></canvas>");
        
        new_canvas.css({
            position: "absolute",
            top: 0,
            left: ( tile_low - this.view.low ) * w_scale,
            "border-right": "1px solid #ddd"
        });
        new_canvas.get(0).width = width;
        new_canvas.get(0).height = height;
        // console.log(( tile_low - this.view.low ) * w_scale, tile_index, w_scale);
        var ctx = new_canvas.get(0).getContext("2d");
        
        var j = 0;
        for (var i in this.values) {
            feature = this.values[i];
            if (feature.start <= tile_high && feature.end >= tile_low) {
                f_start = Math.floor( Math.max(0, (feature.start - tile_low) * w_scale) );
                f_end   = Math.ceil( Math.min(width, (feature.end - tile_low) * w_scale) );
                // console.log(feature.start, feature.end, f_start, f_end, j);
                ctx.fillStyle = "#000";
                ctx.fillRect(f_start, this.slots[feature.name] * 10 + 5, f_end - f_start, 1);
                
                if (this.showing_labels && ctx.fillText) {
                    ctx.font = "10px monospace";
                    ctx.textAlign = "right";
                    ctx.fillText(feature.name, f_start, this.slots[feature.name] * 10 + 8);
                }
                
                if (feature.exon_start && feature.exon_end) {
                    var exon_start = Math.floor( Math.max(0, (feature.exon_start - tile_low) * w_scale) );
                    var exon_end = Math.ceil( Math.min(width, (feature.exon_end - tile_low) * w_scale) );
                    // ctx.fillRect(exon_start, j * 10 + 3, exon_end - exon_start, 5);
                    // ctx.fillRect(exon_start, this.slots[feature.name] * 10 + 3, exon_end - exon_start, 3);
                }
                
                for (var i in feature.blocks) {
                    block = feature.blocks[i];
                    block_start = Math.floor( Math.max(0, (block[0] - tile_low) * w_scale) );
                    block_end = Math.ceil( Math.min(width, (block[1] - tile_low) * w_scale) );
                    var thickness = 3, y_start = 4;
                    if (exon_start && block_start >= exon_start && block_end <= exon_end) {
                        thickness = 5, y_start = 3;
                    }                    
                    ctx.fillRect(exon_start, this.slots[feature.name] * 10 + y_start, block_end - block_start, thickness);
                    // console.log(block_start, block_end);
                }
                
                j++;
            }
        }        

        parent_element.append( new_canvas );
        return new_canvas;
    },
});
