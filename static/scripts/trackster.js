/* Trackster
    2010, James Taylor, Kanwei Li
*/
var DEBUG = false;

var DENSITY = 1000,
    FEATURE_LEVELS = 100,
    DATA_ERROR = "There was an error in indexing this dataset.",
    DATA_NONE = "No data for this chrom/contig.",
    DATA_PENDING = "Currently indexing... please wait",
    DATA_LOADING = "Loading data...",
    CACHED_TILES_FEATURE = 10,
    CACHED_TILES_LINE = 30,
    CACHED_DATA = 20,
    CONTEXT = $("<canvas></canvas>").get(0).getContext("2d"),
    RIGHT_STRAND, LEFT_STRAND;
    
var right_img = new Image();
right_img.src = "../images/visualization/strand_right.png";
right_img.onload = function() {
    RIGHT_STRAND = CONTEXT.createPattern(right_img, "repeat");
};
var left_img = new Image();
left_img.src = "../images/visualization/strand_left.png";
left_img.onload = function() {
    LEFT_STRAND = CONTEXT.createPattern(left_img, "repeat");
};
var right_img_inv = new Image();
right_img_inv.src = "../images/visualization/strand_right_inv.png";
right_img_inv.onload = function() {
    RIGHT_STRAND_INV = CONTEXT.createPattern(right_img_inv, "repeat");
};
var left_img_inv = new Image();
left_img_inv.src = "../images/visualization/strand_left_inv.png";
left_img_inv.onload = function() {
    LEFT_STRAND_INV = CONTEXT.createPattern(left_img_inv, "repeat");
};

function commatize( number ) {
    number += ''; // Convert to string
    var rgx = /(\d+)(\d{3})/;
    while (rgx.test(number)) {
        number = number.replace(rgx, '$1' + ',' + '$2');
    }
    return number;
}

var Cache = function( num_elements ) {
    this.num_elements = num_elements;
    this.obj_cache = {};
    this.key_ary = [];
};
$.extend( Cache.prototype, {
    get: function( key ) {
        var index = this.key_ary.indexOf(key);
        if (index != -1) {
            // Move to the end
            this.key_ary.splice(index, 1);
            this.key_ary.push(key);
        }
        return this.obj_cache[key];
    },
    set: function( key, value ) {
        if (!this.obj_cache[key]) {
            if (this.key_ary.length >= this.num_elements) {
                // Remove first element
                var deleted_key = this.key_ary.shift();
                delete this.obj_cache[deleted_key];
            }
            this.key_ary.push(key);
        }
        this.obj_cache[key] = value;
        return value;
    }
});

var View = function( chrom, max_high ) {
    this.chrom = chrom;
    this.tracks = [];
    this.max_low = 0;
    this.max_high = max_high;
    this.center = (this.max_high - this.max_low) / 2;
    this.span = this.max_high - this.max_low;
    this.zoom_factor = 3;
    this.zoom_level = 0;
};
$.extend( View.prototype, {
    add_track: function ( track ) {
        track.view = this;
        this.tracks.push( track );
        if (track.init) { track.init(); }
    },
    redraw: function () {
        var span = this.span / Math.pow(this.zoom_factor, this.zoom_level),
            low = this.center - (span / 2),
            high = low + span;
        
        if (low < 0) {
            low = 0;
            high = low + span;
            
        } else if (high > this.max_high) {
            high = this.max_high;
            low = high - span;
        }
        this.low = Math.floor(low);
        this.high = Math.ceil(high);
        this.center = Math.round( this.low + (this.high - this.low) / 2 );
        
        // 10^log10(range / DENSITY) Close approximation for browser window, assuming DENSITY = window width
        this.resolution = Math.pow( 10, Math.ceil( Math.log( (this.high - this.low) / DENSITY ) / Math.LN10 ) );
        this.zoom_res = Math.pow( FEATURE_LEVELS, Math.max(0,Math.ceil( Math.log( this.resolution, FEATURE_LEVELS ) / Math.log(FEATURE_LEVELS) )));
        
        // Overview
        $("#overview-box").css( {
            left: ( this.low / this.span ) * $("#overview-viewport").width(),
            // Minimum width for usability
            width: Math.max( 12, ( ( this.high - this.low ) / this.span ) * $("#overview-viewport").width() )
        }).show();
        $("#low").val( commatize(this.low) );
        $("#high").val( commatize(this.high) );
        for ( var i = 0, len = this.tracks.length; i < len; i++ ) {
            this.tracks[i].draw();
        }
        //$("#bottom-spacer").remove();
        //$("#viewport").append('<div id="bottom-spacer" style="height: 200px;"></div>');
    },
    zoom_in: function ( point ) {
        if (this.max_high === 0 || this.high - this.low < 30) {
            return;
        }
        
        if ( point ) {
            this.center = point / $(document).width() * (this.high - this.low) + this.low;
        }
        this.zoom_level += 1;
        this.redraw();
    },
    zoom_out: function () {
        if (this.max_high === 0) {
            return;
        }
        if (this.zoom_level <= 0) {
            this.zoom_level = 0;
            return;            
        }
        this.zoom_level -= 1;
        this.redraw();
    }
});

var Track = function ( name, parent_element ) {
    this.name = name;
    this.parent_element = parent_element;
    this.make_container();
};
$.extend( Track.prototype, {
    make_container: function () {
        this.header_div = $("<div class='track-header'>").text( this.name );
        this.content_div = $("<div class='track-content'>");
        this.container_div = $("<div class='track'></div>").append( this.header_div ).append( this.content_div );
        this.parent_element.append( this.container_div );
    }
});

var TiledTrack = function() {
};
$.extend( TiledTrack.prototype, Track.prototype, {
    draw: function() {
        var low = this.view.low,
            high = this.view.high,
            range = high - low,
            resolution = this.view.resolution;
            
        
        if (DEBUG) { $("#debug").text(resolution + " " + this.view.zoom_res); }

        var parent_element = $("<div style='position: relative;'></div>");
            this.content_div.children( ":first" ).remove();
            this.content_div.append( parent_element );

        var w_scale = this.content_div.width() / range;

        var max_height = 20;
        var tile_element;
        // Index of first tile that overlaps visible region
        var tile_index = Math.floor( low / resolution / DENSITY );
        while ( ( tile_index * DENSITY * resolution ) < high ) {
            // Check in cache
            var key = this.content_div.width() + '_' + this.view.zoom_level + '_' + tile_index;
            var cached = this.tile_cache.get(key);
            if ( cached ) {
                // console.log("cached tile " + tile_index);
                var tile_low = tile_index * DENSITY * resolution;
                var left = ( tile_low - low ) * w_scale;
                if (this.left_offset) {
                    left -= this.left_offset;
                }
                cached.css( {
                    left: left
                });
                // Our responsibility to move the element to the new parent
                parent_element.append( cached );
                max_height = Math.max( max_height, cached.height() );
            } else {
                tile_element = this.draw_tile( resolution, tile_index, parent_element, w_scale );
                if ( tile_element ) {
                    this.tile_cache.set(key, tile_element);
                    max_height = Math.max( max_height, tile_element.height() );
                }
            }
            this.content_div.css( "height", max_height );
            tile_index += 1;
        }
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
            new_div.append( $("<div class='label'>" + commatize( position ) + "</div>").css( {
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

var LineTrack = function ( name, dataset_id, indexer, height ) {
    this.tile_cache = new Cache(CACHED_TILES_LINE);
    Track.call( this, name, $("#viewport") );
    TiledTrack.call( this );
    
    this.indexer = indexer;
    this.height_px = (height ? height : 100);
    this.container_div.addClass( "line-track" );
    this.dataset_id = dataset_id;
    this.data_queue = {};
    this.cache = new Cache(CACHED_DATA); // We need to cache some data because of
                                         // asynchronous calls
};
$.extend( LineTrack.prototype, TiledTrack.prototype, {
    init: function() {
        var track = this;
        track.content_div.text(DATA_LOADING);
        $.getJSON( data_url, {  stats: true, indexer: track.indexer,
                                chrom: track.view.chrom, low: null, high: null,
                                dataset_id: track.dataset_id }, function ( data ) {
            if (!data || data == "error") {
                track.container_div.addClass("error");
                track.content_div.text(DATA_ERROR);
            } else if (data == "no data") {
                track.container_div.addClass("nodata");
                track.content_div.text(DATA_NONE);
            } else if (data == "pending") {
                track.container_div.addClass("pending");
                track.content_div.text(DATA_PENDING);
                setTimeout(function() { track.init(); }, 5000);
            } else {
                track.content_div.text("");
                track.content_div.css( "height", track.height_px + "px" );
                track.min_value = data.min;
                track.max_value = data.max;
                track.vertical_range = track.max_value - track.min_value;
                
                // Draw y-axis labels
                var min_label = $("<div class='yaxislabel'>" + track.min_value + "</div>");
                var max_label = $("<div class='yaxislabel'>" + track.max_value + "</div>");
                
                max_label.css({ position: "relative", top: "25px" });
                max_label.prependTo(track.container_div);
                
                min_label.css({ position: "relative", top: track.height_px + 55 + "px" });
                min_label.prependTo(track.container_div);
                
                track.draw();
            }
        });
    },
    get_data: function( resolution, position ) {
        var track = this,
            low = position * DENSITY * resolution,
            high = ( position + 1 ) * DENSITY * resolution,
            key = resolution + "_" + position;
        
        if (!track.data_queue[key]) {
            track.data_queue[key] = true;
            $.getJSON( data_url, {  indexer: this.indexer, chrom: this.view.chrom, 
                                    low: low, high: high, dataset_id: this.dataset_id,
                                    resolution: this.view.resolution }, function ( data ) {
                track.cache.set(key, data);
                delete track.data_queue[key];
                track.draw();
            });
        }            
    },
    draw_tile: function( resolution, tile_index, parent_element, w_scale ) {
        if (!this.vertical_range) { // We don't have the necessary information yet
            return;
        }
        
        var tile_low = tile_index * DENSITY * resolution,
            tile_length = DENSITY * resolution,
            canvas = $("<canvas class='tile'></canvas>"),
            key = resolution + "_" + tile_index;
        
        if (!this.cache.get(key)) {
            this.get_data( resolution, tile_index );
            return;
        }
        
        var data = this.cache.get(key);
        canvas.css( {
            position: "absolute",
            top: 0,
            left: ( tile_low - this.view.low ) * w_scale
        });
                
        canvas.get(0).width = Math.ceil( tile_length * w_scale );
        canvas.get(0).height = this.height_px;
        var ctx = canvas.get(0).getContext("2d");
        var in_path = false;
        ctx.beginPath();
        for ( var i = 0; i < data.length - 1; i++ ) {
            var x = data[i][0] - tile_low;
            var y = data[i][1];
            // Missing data causes us to stop drawing
            if ( isNaN( y ) ) {
                in_path = false;
            } else {
                // Translate
                x = x * w_scale;
                y = (y - this.min_value) / this.vertical_range * this.height_px;
                if ( in_path ) {
                    ctx.lineTo( x, y );
                } else {
                    ctx.moveTo( x, y );
                    in_path = true;
                }
            }
        }
        ctx.stroke();
        parent_element.append( canvas );
        return canvas;
    }
});

var FeatureTrack = function ( name, dataset_id, indexer, height ) {
    this.tile_cache = new Cache(CACHED_TILES_FEATURE);
    Track.call( this, name, $("#viewport") );
    TiledTrack.call( this );
    
    this.indexer = indexer;
    this.height_px = (height ? height : 100);
    this.container_div.addClass( "feature-track" );
    this.dataset_id = dataset_id;
    this.zo_slots = {};
    this.show_labels_scale = 0.001;
    this.showing_details = false;
    this.vertical_detail_px = 10;
    this.vertical_nodetail_px = 3;
    this.base_color = "#2C3143";
    this.default_font = "9px Monaco, Lucida Console, monospace";
    this.left_offset = 200;
    this.inc_slots = {};
    this.data_queue = {};
    this.s_e_by_tile = {};
    this.data_cache = new Cache(20);
};
$.extend( FeatureTrack.prototype, TiledTrack.prototype, {
    init: function() {
        var track = this;
        track.content_div.text(DATA_LOADING);
        $.getJSON( data_url, {  indexer: track.indexer, low: track.view.max_low, 
                                high: track.view.max_high, dataset_id: track.dataset_id,
                                chrom: track.view.chrom }, function ( data ) {
            if (data == "error") {
                track.container_div.addClass("error");
                track.content_div.text(DATA_ERROR);
            } else if (data.length === 0 || data == "no data") {
                track.container_div.addClass("nodata");
                track.content_div.text(DATA_NONE);
            } else if (data == "pending") {
                track.container_div.addClass("pending");
                track.content_div.text(DATA_PENDING);
                setTimeout(function() { track.init(); }, 5000);
            } else {
                track.content_div.text("");
                track.content_div.css( "height", track.height_px + "px" );
                track.values = data;
                track.calc_slots();
                track.slots = track.zo_slots;
                track.draw();
            }
        });
    },
    get_data: function( low, high ) {
        // console.log("getting: ", low, high);
        var track = this,
            key = low + '_' + high;
        
        if (!track.data_queue[key]) {
            track.data_queue[key] = true;
            $.getJSON( data_url, {  indexer: track.indexer, chrom: track.view.chrom, 
                                    low: low, high: high, dataset_id: track.dataset_id,
                                    include_blocks: true }, function ( data ) {
                track.data_cache.set(key, data);
                // console.log("datacache", track.data_cache.get(key));
                delete track.data_queue[key];
                track.draw();
            });
        }
    },
    calc_slots: function() {
        var end_ary = [],
            scale = this.content_div.width() / (this.view.high - this.view.low),
            max_low = this.view.max_low;
        // console.log(scale, this.view.high, this.view.low);
        for (var i = 0, len = this.values.length; i < len; i++) {
            var f_start, f_end, feature = this.values[i];
            f_start = Math.floor( (feature.start - max_low) * scale );
            f_end = Math.ceil( (feature.end - max_low) * scale );
            
            // if (include_labels) { console.log(f_start, f_end); }
            var j = 0;
            while (true) {
                if (end_ary[j] === undefined || end_ary[j] < f_start) {
                    end_ary[j] = f_end;
                    this.zo_slots[feature.uid] = j;
                    break;
                }
                j++;
            }
        }
        this.height_px = end_ary.length * this.vertical_nodetail_px + 15;
        this.content_div.css( "height", this.height_px + "px" );
    },
    incremental_slots: function( level, features ) {
        if (!this.inc_slots[level]) {
            this.inc_slots[level] = {};
            this.inc_slots[level].w_scale = 1 / level;
            this.s_e_by_tile[level] = {};
        }
        // TODO: Should calculate zoom tile index, which will improve performance
        // by only having to look at a smaller subset
        // if (this.s_e_by_tile[0] === undefined) { this.s_e_by_tile[0] = []; }
        var w_scale = this.inc_slots[level].w_scale,
            undone = [],
            highest_slot = 0, // To measure how big to draw canvas
            dummy_canvas = $("<canvas></canvas>").get(0).getContext("2d"),
            max_low = this.view.max_low;
            
        var f_start, f_end, slotted = [];
        
        // If feature already exists in slots (from previously seen tiles), use the same slot,
        // otherwise if not seen, add to "undone" list for slot calculation
        for (var i = 0, len = features.length; i < len; i++) {
            var feature = features[i];
            if (this.inc_slots[level][feature.uid] !== undefined) {
                highest_slot = Math.max(highest_slot, this.inc_slots[level][feature.uid]);
                slotted.push(this.inc_slots[level][feature.uid]);
            } else {
                undone.push(i);
            }
        }
        
        // console.log("Slotted: ", features.length - undone.length, "/", features.length, slotted);
        for (var i = 0, len = undone.length; i < len; i++) {
            var feature = features[undone[i]];
            f_start = Math.floor( (feature.start - max_low) * w_scale );
            f_start -= dummy_canvas.measureText(feature.name).width;
            f_end = Math.ceil( (feature.end - max_low) * w_scale );
            
            var j = 0;
            // Try to fit the feature to the first slot that doesn't overlap any other features in that slot
            while (true) {
                var found = true;
                if (this.s_e_by_tile[level][j] !== undefined) {
                    for (var k = 0, k_len = this.s_e_by_tile[level][j].length; k < k_len; k++) {
                        var s_e = this.s_e_by_tile[level][j][k];
                        if (f_end > s_e[0] && f_start < s_e[1]) {
                            found = false;
                            break;
                        }
                    }
                }
                if (found) {
                    if (this.s_e_by_tile[level][j] === undefined) { this.s_e_by_tile[level][j] = []; }
                    this.s_e_by_tile[level][j].push([f_start, f_end]);
                    this.inc_slots[level][feature.uid] = j;
                    highest_slot = Math.max(highest_slot, j);
                    break;
                }
                j++;
            }
        }
        return highest_slot;
        
    },
    draw_tile: function( resolution, tile_index, parent_element, w_scale ) {
        if (!this.values) {
            return;
        }
        var tile_low = tile_index * DENSITY * resolution,
            tile_high = ( tile_index + 1 ) * DENSITY * resolution,
            tile_span = DENSITY * resolution;
        // console.log("drawing " + tile_index);
        // Once we zoom in enough, show name labels
        var data, slots, required_height;
        if (w_scale > this.show_labels_scale) {
            if (!this.showing_details) {
                this.showing_details = true;
            }
            for (var k in this.data_cache.obj_cache) {
                var k_split = k.split("_"), k_low = k_split[0], k_high = k_split[1];
                if (k_low <= tile_low && k_high >= tile_high) {
                    data = this.data_cache.get(k);
                    break;
                }
            }
            if (!data) {
                this.data_queue[ [tile_low, tile_high] ] = true;
                this.get_data(tile_low, tile_high);
                return;
            }
            // Calculate new slots incrementally for this new chunk of data and update height if necessary
            required_height = this.incremental_slots( this.view.zoom_res, data ) * this.vertical_detail_px + 15;
            // console.log(required_height);
            slots = this.inc_slots[this.view.zoom_res];
        } else {
            if (this.showing_details) {
                this.showing_details = false;
            }
            required_height = this.height_px;
            slots = this.zo_slots;
            data = this.values;
        }

        // console.log(tile_low, tile_high, tile_length, w_scale);
        var width = Math.ceil( tile_span * w_scale ),
            new_canvas = $("<canvas class='tile'></canvas>");
        
        new_canvas.css({
            position: "absolute",
            top: 0,
            left: ( tile_low - this.view.low ) * w_scale - this.left_offset
        });
        new_canvas.get(0).width = width + this.left_offset;
        new_canvas.get(0).height = required_height;
        // console.log(( tile_low - this.view.low ) * w_scale, tile_index, w_scale);
        var ctx = new_canvas.get(0).getContext("2d");
        ctx.fillStyle = this.base_color;
        ctx.font = this.default_font;
        ctx.textAlign = "right";

        var j = 0;
        for (var i = 0, len = data.length; i < len; i++) {
            var feature = data[i];
            if (feature.start <= tile_high && feature.end >= tile_low) {
                var f_start = Math.floor( Math.max(0, (feature.start - tile_low) * w_scale) ),
                    f_end   = Math.ceil( Math.min(width, (feature.end - tile_low) * w_scale) ),
                    y_center = slots[feature.uid] * (this.showing_details ? this.vertical_detail_px : this.vertical_nodetail_px);
                
                var thickness, y_start, thick_start = null, thick_end = null;
                if (feature.thick_start && feature.thick_end) {
                    thick_start = Math.floor( Math.max(0, (feature.thick_start - tile_low) * w_scale) );
                    thick_end = Math.ceil( Math.min(width, (feature.thick_end - tile_low) * w_scale) );
                }
                if (!this.showing_details) {
                    // Non-detail levels
                    ctx.fillRect(f_start + this.left_offset, y_center + 5, f_end - f_start, 1);
                } else {
                    // Showing labels, blocks, details
                    if (ctx.fillText && feature.start > tile_low) {
                        ctx.fillText(feature.name, f_start - 1 + this.left_offset, y_center + 8);
                        // ctx.fillText(commatize(feature.start), f_start - 1 + this.left_offset, y_center + 8);
                        // ctx.fillText(slots[feature.uid], f_start - 1 + this.left_offset, y_center + 8);
                    }
                    var blocks = feature.blocks;
                    if (blocks) {
                        // Draw introns
                        if (feature.strand) {
                            if (feature.strand == "+") {
                                ctx.fillStyle = RIGHT_STRAND;
                            } else if (feature.strand == "-") {
                                ctx.fillStyle = LEFT_STRAND;
                            }
                            ctx.fillRect(f_start + this.left_offset, y_center, f_end - f_start, 10);
                            ctx.fillStyle = this.base_color;
                        }
                        
                        for (var k = 0, k_len = blocks.length; k < k_len; k++) {
                            var block = blocks[k],
                                block_start = Math.floor( Math.max(0, (block[0] - tile_low) * w_scale) ),
                                block_end = Math.ceil( Math.min(width, (block[1] - tile_low) * w_scale) );
                            if (block_start > block_end) { continue; }
                            // Draw the block
                            thickness = 5;
                            y_start = 3;
                            ctx.fillRect(block_start + this.left_offset, y_center + y_start, block_end - block_start, thickness);
                            
                            if (thick_start !== undefined && (block_start <= thick_end || block_end >= thick_start) ) {
                                thickness = 9;
                                y_start = 1;
                                var block_thick_start = Math.max(block_start, thick_start),
                                    block_thick_end = Math.min(block_end, thick_end);
                                ctx.fillRect(block_thick_start + this.left_offset, y_center + y_start, block_thick_end - block_thick_start, thickness);

                            }
                        }
                    } else {
                        // If there are no blocks, we treat the feature as one big exon
                        thickness = 9;
                        y_start = 1;
                        ctx.fillRect(f_start + this.left_offset, y_center + y_start, f_end - f_start, thickness);
                        if ( feature.strand ) {
                            if (feature.strand == "+") {
                                ctx.fillStyle = RIGHT_STRAND_INV;
                            } else if (feature.strand == "-") {
                                ctx.fillStyle = LEFT_STRAND_INV;
                            }
                            ctx.fillRect(f_start + this.left_offset, y_center, f_end - f_start, 10);
                            ctx.fillStyle = this.base_color;
                        }
                    }
                }
                j++;
            }
        }        

        parent_element.append( new_canvas );
        return new_canvas;
    }
});

var ReadTrack = function ( name, dataset_id, indexer, height ) {
    this.tile_cache = new Cache(CACHED_TILES_FEATURE);
    Track.call( this, name, $("#viewport") );
    TiledTrack.call( this );
    FeatureTrack.call( this, name, dataset_id, indexer, height );
    this.default_font = "9px Monaco, Lucida Console, monospace";
    
};
$.extend( ReadTrack.prototype, TiledTrack.prototype, FeatureTrack.prototype, {
    draw_tile: function( resolution, tile_index, parent_element, w_scale ) {
        if (!this.values) {
            return;
        }
        var tile_low = tile_index * DENSITY * resolution,
            tile_high = ( tile_index + 1 ) * DENSITY * resolution,
            tile_span = DENSITY * resolution;
        // console.log("drawing " + tile_index);
        // Once we zoom in enough, show name labels
        var data, slots, required_height;
            required_height = this.height_px;
            slots = this.zo_slots;
            data = this.values;
        
        // console.log(tile_low, tile_high, tile_length, w_scale);
        var width = Math.ceil( tile_span * w_scale ),
            new_canvas = $("<canvas class='tile'></canvas>");

        new_canvas.css({
            position: "absolute",
            top: 0,
            left: ( tile_low - this.view.low ) * w_scale - this.left_offset
        });
        new_canvas.get(0).width = width + this.left_offset;
        new_canvas.get(0).height = required_height;
        // console.log(( tile_low - this.view.low ) * w_scale, tile_index, w_scale);
        var ctx = new_canvas.get(0).getContext("2d");
        ctx.fillStyle = this.base_color;
        ctx.font = this.default_font;
        ctx.textAlign = "right";
        var px_per_char = ctx.measureText("A").width;
        
        var j = 0;
        for (var i = 0, len = data.length; i < len; i++) {
            var feature = data[i];
            if (feature.start <= tile_high && feature.end >= tile_low) {
                var f_start = Math.floor( Math.max(0, (feature.start - tile_low) * w_scale) ),
                    f_end   = Math.ceil( Math.min(width, (feature.end - tile_low) * w_scale) ),
                    y_center = slots[feature.uid] * this.vertical_detail_px;
                
                var thickness, y_start, thick_start = null, thick_end = null;
                if (w_scale > px_per_char) {
                    for (var c = 0, str_len = feature.name.length; c < str_len; c++) {
                        var c_start = Math.floor( Math.max(0, (feature.start + c - tile_low) * w_scale) );
                        ctx.fillText(feature.name[c], c_start + this.left_offset, y_center + 8);
                    }
                } else {
                    ctx.fillRect(f_start + this.left_offset, y_center + 4, f_end - f_start, 3);
                }
            }
        }        

        parent_element.append( new_canvas );
        return new_canvas;
    }
});
