/* Trackster
    2010, James Taylor, Kanwei Li
*/

var DENSITY = 200,
    FEATURE_LEVELS = 10,
    DATA_ERROR = "There was an error in indexing this dataset. ",
    DATA_NOCONVERTER = "A converter for this dataset is not installed. Please check your datatypes_conf.xml file.",
    DATA_NONE = "No data for this chrom/contig.",
    DATA_PENDING = "Currently indexing... please wait",
    DATA_LOADING = "Loading data...",
    CACHED_TILES_FEATURE = 10,
    CACHED_TILES_LINE = 30,
    CACHED_DATA = 5,
    CONTEXT = $("<canvas></canvas>").get(0).getContext("2d"),
    PX_PER_CHAR = CONTEXT.measureText("A").width,
    RIGHT_STRAND, LEFT_STRAND;
    
var right_img = new Image();
right_img.src = image_path + "/visualization/strand_right.png";
right_img.onload = function() {
    RIGHT_STRAND = CONTEXT.createPattern(right_img, "repeat");
};
var left_img = new Image();
left_img.src = image_path + "/visualization/strand_left.png";
left_img.onload = function() {
    LEFT_STRAND = CONTEXT.createPattern(left_img, "repeat");
};
var right_img_inv = new Image();
right_img_inv.src = image_path + "/visualization/strand_right_inv.png";
right_img_inv.onload = function() {
    RIGHT_STRAND_INV = CONTEXT.createPattern(right_img_inv, "repeat");
};
var left_img_inv = new Image();
left_img_inv.src = image_path + "/visualization/strand_left_inv.png";
left_img_inv.onload = function() {
    LEFT_STRAND_INV = CONTEXT.createPattern(left_img_inv, "repeat");
};

var Cache = function( num_elements ) {
    this.num_elements = num_elements;
    this.clear();
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
    },
    clear: function() {
        this.obj_cache = {};
        this.key_ary = [];
    }
});

var View = function( container, chrom, title, vis_id, dbkey ) {
    this.container = container;
    this.vis_id = vis_id;
    this.dbkey = dbkey;
    this.title = title;
    this.chrom = chrom;
    this.tracks = [];
    this.label_tracks = [];
    this.max_low = 0;
    this.max_high = 0;
    this.track_id_counter = 0;
    this.zoom_factor = 3;
    this.min_separation = 30;
    this.has_changes = false;
    this.init();
    this.reset();
};
$.extend( View.prototype, {
    init: function() {
        // Create DOM elements
        var parent_element = this.container,
            view = this;
        this.top_labeltrack = $("<div/>").addClass("top-labeltrack").appendTo(parent_element);        
        this.content_div = $("<div/>").addClass("content").css("position", "relative").appendTo(parent_element);
        this.viewport_container = $("<div/>").addClass("viewport-container").addClass("viewport-container").appendTo(this.content_div);
        this.viewport = $("<div/>").addClass("viewport").appendTo(this.viewport_container);
        
        this.nav_container = $("<div/>").addClass("nav-container").appendTo(parent_element);
        this.nav_labeltrack = $("<div/>").addClass("nav-labeltrack").appendTo(this.nav_container);
        this.nav = $("<div/>").addClass("nav").appendTo(this.nav_container);
        this.overview = $("<div/>").addClass("overview").appendTo(this.nav);
        this.overview_viewport = $("<div/>").addClass("overview-viewport").appendTo(this.overview);
        this.overview_box = $("<div/>").addClass("overview-box").appendTo(this.overview_viewport);
        
        this.nav_controls = $("<div/>").addClass("nav-controls").appendTo(this.nav);
        this.chrom_form = $("<form/>").attr("action", function() { void(0); } ).appendTo(this.nav_controls);
        this.chrom_select = $("<select/>").attr({ "name": "chrom"}).css("width", "15em").addClass("no-autocomplete").append("<option value=''>Loading</option>").appendTo(this.chrom_form);
        this.low_input = $("<input/>").addClass("low").css("width", "10em").appendTo(this.chrom_form);
        $("<span/>").text(" - ").appendTo(this.chrom_form);
        this.high_input = $("<input/>").addClass("high").css("width", "10em").appendTo(this.chrom_form);
        if (this.vis_id !== undefined) {
            this.hidden_input = $("<input/>").attr("type", "hidden").val(this.vis_id).appendTo(this.chrom_form);
        }
        this.zi_link = $("<a/>").click(function() { view.zoom_in(); view.redraw() }).html('<img src="'+image_path+'/fugue/magnifier-zoom.png" />').appendTo(this.chrom_form);
        this.zo_link = $("<a/>").click(function() { view.zoom_out(); view.redraw() }).html('<img src="'+image_path+'/fugue/magnifier-zoom-out.png" />').appendTo(this.chrom_form);;
        
        $.ajax({
            url: chrom_url, 
            data: (this.vis_id !== undefined ? { vis_id: this.vis_id } : { dbkey: this.dbkey }),
            dataType: "json",
            success: function ( result ) {
                if (result['reference']) {
                    view.add_label_track( new ReferenceTrack(view) );
                }
                view.chrom_data = result['chrom_info'];
                var chrom_options = '<option value="">Select Chrom/Contig</option>';
                for (i in view.chrom_data) {
                    var chrom = view.chrom_data[i]['chrom'];
                    chrom_options += '<option value="' + chrom + '">' + chrom + '</option>';
                }
                view.chrom_select.html(chrom_options);
                view.chrom_select.bind( "change", function () {
                    view.chrom = view.chrom_select.val();
                    var found = $.grep(view.chrom_data, function(v, i) {
                        return v.chrom === view.chrom;
                    })[0];
                    view.max_high = (found.len !== undefined ? found.len : 0);
                    view.reset();
                    view.redraw(true);
                
                    for (var track_id in view.tracks) {
                        var track = view.tracks[track_id];
                        if (track.init) {
                            track.init();
                        }
                    }
                    view.redraw();
                });
            },
            error: function() {
                alert( "Could not load chroms for this dbkey:", view.dbkey );
            }
        });
        
        /*
        this.content_div.bind("mousewheel", function( e, delta ) {
            if (Math.abs(delta) < 0.5) {
                return;
            }
            if (delta > 0) {
                view.zoom_in(e.pageX, this.viewport_container);
            } else {
                view.zoom_out();
            }
            e.preventDefault();
        });
        */

        this.content_div.bind("dblclick", function( e ) {
            view.zoom_in(e.pageX, this.viewport_container);
        });

        // To let the overview box be draggable
        this.overview_box.bind("dragstart", function( e ) {
            this.current_x = e.offsetX;
        }).bind("drag", function( e ) {
            var delta = e.offsetX - this.current_x;
            this.current_x = e.offsetX;

            var delta_chrom = Math.round(delta / view.viewport_container.width() * (view.max_high - view.max_low) );
            view.move_delta(-delta_chrom);
        });
        
        this.viewport_container.bind( "dragstart", function( e ) {
            this.original_low = view.low;
            this.current_height = e.clientY;
            this.current_x = e.offsetX;
        }).bind( "drag", function( e ) {
            var container = $(this);
            var delta = e.offsetX - this.current_x;
            var new_scroll = container.scrollTop() - (e.clientY - this.current_height);
            if ( new_scroll < container.get(0).scrollHeight - container.height() ) {
                container.scrollTop(new_scroll);
            }
            this.current_height = e.clientY;
            this.current_x = e.offsetX;

            var delta_chrom = Math.round(delta / view.viewport_container.width() * (view.high - view.low));
            view.move_delta(delta_chrom);
        });
        
        this.top_labeltrack.bind( "dragstart", function(e) {
            this.drag_origin_x = e.clientX;
            this.drag_origin_pos = e.clientX / view.viewport_container.width() * (view.high - view.low) + view.low;
            this.drag_div = $("<div />").css( { 
                "height": view.content_div.height(), "top": "0px", "position": "absolute", 
                "background-color": "#cfc", "border": "1px solid #6a6", "opacity": 0.5
            } ).appendTo( $(this) );
        }).bind( "drag", function(e) {
            var min = Math.min(e.clientX, this.drag_origin_x),
                max = Math.max(e.clientX, this.drag_origin_x),
                span = (view.high - view.low),
                width = view.viewport_container.width();
            
            view.low_input.val(commatize(Math.round(min / width * span) + view.low));
            view.high_input.val(commatize(Math.round(max / width * span) + view.low));
            this.drag_div.css( { "left": min + "px", "width": (max - min) + "px" } );
        }).bind( "dragend", function(e) {
            var min = Math.min(e.clientX, this.drag_origin_x),
                max = Math.max(e.clientX, this.drag_origin_x),
                span = (view.high - view.low),
                width = view.viewport_container.width(),
                old_low = view.low;
                
            view.low = Math.round(min / width * span) + old_low;
            view.high = Math.round(max / width * span) + old_low;
            this.drag_div.remove();
            view.redraw();
        });
        
        this.add_label_track( new LabelTrack( this, this.top_labeltrack ) );
        this.add_label_track( new LabelTrack( this, this.nav_labeltrack ) );
    },
    move_delta: function(delta_chrom) {
        var view = this;
        var current_chrom_span = view.high - view.low;
        // Check for left and right boundaries
        if (view.low - delta_chrom < view.max_low) {
            view.low = view.max_low;
            view.high = view.max_low + current_chrom_span;
        } else if (view.high - delta_chrom > view.max_high) {
            view.high = view.max_high;
            view.low = view.max_high - current_chrom_span;
        } else {
            view.high -= delta_chrom;
            view.low -= delta_chrom;
        }
        view.redraw();
    },
    add_track: function(track) {
        track.view = this;
        track.track_id = this.track_id_counter;
        this.tracks.push(track);
        if (track.init) { track.init(); }
        track.container_div.attr('id', 'track_' + track.track_id);
        this.track_id_counter += 1;
    },
    add_label_track: function (label_track) {
        label_track.view = this;
        this.label_tracks.push(label_track);
    },
    remove_track: function(track) {
        this.has_changes = true;
        track.container_div.fadeOut('slow', function() { $(this).remove(); });
        delete this.tracks[this.tracks.indexOf(track)];
    },
    update_options: function() {
        this.has_changes = true;
        var sorted = $("ul#sortable-ul").sortable('toArray');
        for (var id_i in sorted) {
            var id = sorted[id_i].split("_li")[0].split("track_")[1];
            this.viewport.append( $("#track_" + id) );
        }
        
        for (var track_id in view.tracks) {
            var track = view.tracks[track_id];
            if (track && track.update_options) {
                track.update_options(track_id);
            }
        }
    },
    reset: function() {
        this.low = this.max_low;
        this.high = this.max_high;
        this.viewport_container.find(".yaxislabel").remove();
    },        
    redraw: function(nodraw) {
        var span = this.high - this.low,
            low = this.low,
            high = this.high;
        
        if (low < this.max_low) {
            low = this.max_low;
        }
        if (high > this.max_high) {
            high = this.max_high;
        }
        if (this.high !== 0 && span < this.min_separation) {
            high = low + this.min_separation;
        }
        this.low = Math.floor(low);
        this.high = Math.ceil(high);
        
        // 10^log10(range / DENSITY) Close approximation for browser window, assuming DENSITY = window width
        this.resolution = Math.pow( 10, Math.ceil( Math.log( (this.high - this.low) / 200 ) / Math.LN10 ) );
        this.zoom_res = Math.pow( FEATURE_LEVELS, Math.max(0,Math.ceil( Math.log( this.resolution, FEATURE_LEVELS ) / Math.log(FEATURE_LEVELS) )));
        
        // Overview
        this.overview_box.css( {
            left: ( this.low / (this.max_high - this.max_low) ) * this.overview_viewport.width(),
            // Minimum width for usability
            width: Math.max( 12, (this.high - this.low)/(this.max_high - this.max_low) * this.overview_viewport.width() )
        }).show();
        this.low_input.val( commatize(this.low) );
        this.high_input.val( commatize(this.high) );
        if (!nodraw) {
            for (var i = 0, len = this.tracks.length; i < len; i++) {
                if (this.tracks[i] && this.tracks[i].enabled) {
                    this.tracks[i].draw();
                }
            }
            for (var i = 0, len = this.label_tracks.length; i < len; i++) {
                this.label_tracks[i].draw();
            }
        }
    },
    zoom_in: function (point, container) {
        if (this.max_high === 0 || this.high - this.low < this.min_separation) {
            return;
        }
        var span = this.high - this.low,
            cur_center = span / 2 + this.low,
            new_half = (span / this.zoom_factor) / 2;
        if (point) {
            cur_center = point / this.viewport_container.width() * (this.high - this.low) + this.low;
        }
        this.low = Math.round(cur_center - new_half);
        this.high = Math.round(cur_center + new_half);
        this.redraw();
    },
    zoom_out: function () {
        if (this.max_high === 0) {
            return;
        }
        var span = this.high - this.low,
            cur_center = span / 2 + this.low,
            new_half = (span * this.zoom_factor) / 2;
        this.low = Math.round(cur_center - new_half);
        this.high = Math.round(cur_center + new_half);
        this.redraw();
    }
});

var Track = function (name, view, parent_element) {
    this.name = name;
    this.parent_element = parent_element;
    this.view = view;
    this.init_global();
};
$.extend( Track.prototype, {
    init_global: function () {
        this.header_div = $("<div class='track-header'>").text( this.name );
        this.content_div = $("<div class='track-content'>");
        this.container_div = $("<div />").addClass('track').append( this.header_div ).append( this.content_div );
        this.parent_element.append( this.container_div );
    },
    init_each: function(params, success_fn) {
        var track = this;
        track.enabled = false;
        track.data_queue = {};
        track.tile_cache.clear();
        track.data_cache.clear();
        // track.content_div.css( "height", "30px" );
        if (!track.content_div.text()) {
            track.content_div.text(DATA_LOADING);
        }
        track.container_div.removeClass("nodata error pending");

        if (track.view.chrom) {
            $.getJSON( data_url, params, function (result) {
                if (!result || result === "error" || result.kind === "error") {
                    track.container_div.addClass("error");
                    track.content_div.text(DATA_ERROR);
                    if (result.message) {
                        var track_id = track.view.tracks.indexOf(track);
                        var error_link = $("<a href='javascript:void(0);'></a>").attr("id", track_id + "_error");
                        error_link.text("Click to view error");
                        $("#" + track_id + "_error").live("click", function() {                        
                            show_modal( "Trackster Error", "<pre>" + result.message + "</pre>", { "Close" : hide_modal } );
                        });
                        track.content_div.append(error_link);
                    }
                } else if (result === "no converter") {
                    track.container_div.addClass("error");
                    track.content_div.text(DATA_NOCONVERTER);
                } else if (result.data !== undefined && (result.data === null || result.data.length === 0)) {
                    track.container_div.addClass("nodata");
                    track.content_div.text(DATA_NONE);
                } else if (result === "pending") {
                    track.container_div.addClass("pending");
                    track.content_div.text(DATA_PENDING);
                    setTimeout(function() { track.init(); }, 5000);
                } else {
                    track.content_div.text("");
                    track.content_div.css( "height", track.height_px + "px" );
                    track.enabled = true;
                    success_fn(result);
                    track.draw();
                }
            });
        } else {
            track.container_div.addClass("nodata");
            track.content_div.text(DATA_NONE);
        }
    }
});

var TiledTrack = function() {
    this.left_offset = 200;
};
$.extend( TiledTrack.prototype, Track.prototype, {
    draw: function() {
        var low = this.view.low,
            high = this.view.high,
            range = high - low,
            resolution = this.view.resolution;

        var parent_element = $("<div style='position: relative;'></div>"),
            w_scale = this.content_div.width() / range,
            tile_element;

        this.content_div.children( ":first" ).remove();
        this.content_div.append( parent_element ),
        this.max_height = 0;
        // Index of first tile that overlaps visible region
        var tile_index = Math.floor( low / resolution / DENSITY );
        while ( ( tile_index * DENSITY * resolution ) < high ) {
            // Check in cache
            var key = this.content_div.width() + '_' + w_scale + '_' + tile_index;
            var cached = this.tile_cache.get(key);
            if ( cached ) {
                // console.log("cached tile " + tile_index);
                var tile_low = tile_index * DENSITY * resolution;
                var left = ( tile_low - low ) * w_scale;
                if (this.left_offset) {
                    left -= this.left_offset;
                }
                cached.css({ left: left });
                // Our responsibility to move the element to the new parent
                parent_element.append( cached );
                this.max_height = Math.max( this.max_height, cached.height() );
                this.content_div.css("height", this.max_height + "px");
            } else {
                this.delayed_draw(this, key, low, high, tile_index, resolution, parent_element, w_scale);
            }
            tile_index += 1;
        }
    }, delayed_draw: function(track, key, low, high, tile_index, resolution, parent_element, w_scale) {
        // Put a 50ms delay on drawing so that if the user scrolls fast, we don't load extra data
        setTimeout(function() {
            if ( !(low > track.view.high || high < track.view.low) ) {
                tile_element = track.draw_tile( resolution, tile_index, parent_element, w_scale );
                if ( tile_element ) {
                    track.tile_cache.set(key, tile_element);
                    track.max_height = Math.max( track.max_height, tile_element.height() );
                    track.content_div.css("height", track.max_height + "px");
                }
            }
        }, 50);
    }
});

var LabelTrack = function (view, parent_element) {
    Track.call( this, null, view, parent_element );
    this.track_type = "LabelTrack";
    this.hidden = true;
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

var ReferenceTrack = function (view) {
    this.track_type = "ReferenceTrack";
    Track.call( this, null, view, view.nav_labeltrack );
    TiledTrack.call( this );
    
    this.hidden = true;
    this.height_px = 12;
    this.container_div.addClass( "reference-track" );
    this.dummy_canvas = $("<canvas></canvas>").get(0).getContext("2d");
    this.data_queue = {};
    this.data_cache = new Cache(CACHED_DATA);
    this.tile_cache = new Cache(CACHED_TILES_LINE);
};
$.extend( ReferenceTrack.prototype, TiledTrack.prototype, {
    get_data: function(resolution, position) {
        var track = this,
            low = position * DENSITY * resolution,
            high = ( position + 1 ) * DENSITY * resolution,
            key = resolution + "_" + position;
        
        if (!track.data_queue[key]) {
            track.data_queue[key] = true;
            $.ajax({ 'url': reference_url, 'dataType': 'json', 'data': {  "chrom": this.view.chrom,
                                    "low": low, "high": high, "dbkey": this.view.dbkey },
                success: function (seq) {
                    track.data_cache.set(key, seq);
                    delete track.data_queue[key];
                    track.draw();
                }, error: function(r, t, e) {
                    console.log(r, t, e);
                }
            });
        }
    },
    draw_tile: function( resolution, tile_index, parent_element, w_scale ) {
        var tile_low = tile_index * DENSITY * resolution,
            tile_length = DENSITY * resolution,
            canvas = $("<canvas class='tile'></canvas>"),
            ctx = canvas.get(0).getContext("2d"),
            key = resolution + "_" + tile_index;
        
        if (w_scale > PX_PER_CHAR) {
            if (this.data_cache.get(key) === undefined) {
                this.get_data( resolution, tile_index );
                return;
            }
            
            var seq = this.data_cache.get(key);
            if (seq === null) { return; }
            
            canvas.get(0).width = Math.ceil( tile_length * w_scale + this.left_offset);
            canvas.get(0).height = this.height_px;
            
            canvas.css( {
                position: "absolute",
                top: 0,
                left: ( tile_low - this.view.low ) * w_scale + this.left_offset
            });
            
            for (var c = 0, str_len = seq.length; c < str_len; c++) {
                var c_start = Math.round(c * w_scale);
                ctx.fillText(seq[c], c_start + this.left_offset, 10);
            }
            parent_element.append( canvas );
            return canvas;
        }
    }
});

var LineTrack = function ( name, view, dataset_id, prefs ) {
    this.track_type = "LineTrack";
    Track.call( this, name, view, view.viewport_container );
    TiledTrack.call( this );
    
    this.height_px = 100;
    this.dataset_id = dataset_id;
    this.data_cache = new Cache(CACHED_DATA);
    this.tile_cache = new Cache(CACHED_TILES_LINE);
    this.prefs = { 'min_value': undefined, 'max_value': undefined, 'mode': 'Line' };
    if (prefs.min_value !== undefined) { this.prefs.min_value = prefs.min_value; }
    if (prefs.max_value !== undefined) { this.prefs.max_value = prefs.max_value; }
    if (prefs.mode !== undefined) { this.prefs.mode = prefs.mode; }
};
$.extend( LineTrack.prototype, TiledTrack.prototype, {
    init: function() {
        var track = this,
            track_id = track.view.tracks.indexOf(track);
        
        track.vertical_range = undefined;
        this.init_each({  stats: true, chrom: track.view.chrom, low: null, high: null,
                                dataset_id: track.dataset_id }, function(result) {
            
            track.container_div.addClass( "line-track" );
            data = result.data;
            if ( isNaN(parseFloat(track.prefs.min_value)) || isNaN(parseFloat(track.prefs.max_value)) ) {
                track.prefs.min_value = data.min;
                track.prefs.max_value = data.max;
                // Update the config
                $('#track_' + track_id + '_minval').val(track.prefs.min_value);
                $('#track_' + track_id + '_maxval').val(track.prefs.max_value);
            }
            track.vertical_range = track.prefs.max_value - track.prefs.min_value;
            track.total_frequency = data.total_frequency;
        
            // Draw y-axis labels if necessary
            $('#linetrack_' + track_id + '_minval').remove();
            $('#linetrack_' + track_id + '_maxval').remove();
            
            var min_label = $("<div />").addClass('yaxislabel').attr("id", 'linetrack_' + track_id + '_minval').text(track.prefs.min_value);
            var max_label = $("<div />").addClass('yaxislabel').attr("id", 'linetrack_' + track_id + '_maxval').text(track.prefs.max_value);
            
            max_label.css({ position: "relative", top: "25px", left: "10px" });
            max_label.prependTo(track.container_div);
    
            min_label.css({ position: "relative", top: track.height_px + 55 + "px", left: "10px" });
            min_label.prependTo(track.container_div);
        });
    },
    get_data: function( resolution, position ) {
        var track = this,
            low = position * DENSITY * resolution,
            high = ( position + 1 ) * DENSITY * resolution,
            key = resolution + "_" + position;
        
        if (!track.data_queue[key]) {
            track.data_queue[key] = true;
            /*$.getJSON( data_url, {  "chrom": this.view.chrom, 
                                    "low": low, "high": high, "dataset_id": this.dataset_id,
                                    "resolution": this.view.resolution }, function (data) {
                track.data_cache.set(key, data);
                delete track.data_queue[key];
                track.draw();
            });*/
            $.ajax({ 'url': data_url, 'dataType': 'json', 'data': {  "chrom": this.view.chrom, 
                                    "low": low, "high": high, "dataset_id": this.dataset_id,
                                    "resolution": this.view.resolution }, 
                success: function (result) {
                    data = result.data;
                    track.data_cache.set(key, data);
                    delete track.data_queue[key];
                    track.draw();
                }, error: function(r, t, e) {
                    console.log(r, t, e);
                } 
            });
        }
    },
    draw_tile: function( resolution, tile_index, parent_element, w_scale ) {
        if (this.vertical_range === undefined) {
            return;
        }
        
        var tile_low = tile_index * DENSITY * resolution,
            tile_length = DENSITY * resolution,
            canvas = $("<canvas class='tile'></canvas>"),
            key = resolution + "_" + tile_index;
        
        if (this.data_cache.get(key) === undefined) {
            this.get_data( resolution, tile_index );
            return;
        }
        
        var result = this.data_cache.get(key);
        if (result === null) { return; }
        
        canvas.css( {
            position: "absolute",
            top: 0,
            left: ( tile_low - this.view.low ) * w_scale
        });
        
        canvas.get(0).width = Math.ceil( tile_length * w_scale + this.left_offset);
        canvas.get(0).height = this.height_px;
        var ctx = canvas.get(0).getContext("2d"),
            in_path = false,
            min_value = this.prefs.min_value,
            max_value = this.prefs.max_value,
            vertical_range = this.vertical_range,
            total_frequency = this.total_frequency,
            height_px = this.height_px,
            mode = this.prefs.mode;
            
        ctx.beginPath();
        
        // for intensity, calculate delta x in pixels to for width of box
        if (data.length > 1) {
            var delta_x_px = Math.ceil((data[1][0] - data[0][0]) * w_scale);
        } else {
            var delta_x_px = 10;
        }
        
        var x_scaled, y;
        
        for ( var i = 0; i < data.length; i++ ) {
            x_scaled = (data[i][0] - tile_low) * w_scale;
            y = data[i][1];
            
            if ( mode == "Intensity" ) {
                // DRAW INTENSITY
                if (y === null) {
                    continue;
                }
                if (y <= min_value) {
                    y = min_value;
                } else if (y >= max_value) {
                    y = max_value;
                }
                y = 255 - Math.floor( (y - min_value) / vertical_range * 255 );
                ctx.fillStyle = "rgb(" +y+ "," +y+ "," +y+ ")";
                ctx.fillRect(x_scaled, 0, delta_x_px, this.height_px);
            }
            else {
                // Missing data causes us to stop drawing
                if (y === null) {
                    if (in_path && mode === "Filled") {
                        ctx.lineTo(x_scaled, height_px);
                    }
                    in_path = false;
                    continue;
                } else {
                    // console.log(y, this.min_value, this.vertical_range, (y - this.min_value) / this.vertical_range * this.height_px);
                    if (y <= min_value) {
                        y = min_value;
                    } else if (y >= max_value) {
                        y = max_value;
                    }
                    y = Math.round( height_px - (y - min_value) / vertical_range * height_px );
                    // console.log(canvas.get(0).height, canvas.get(0).width);
                    if (in_path) {
                        ctx.lineTo(x_scaled, y);
                    } else {
                        in_path = true;
                        if (mode === "Filled") {
                            ctx.moveTo(x_scaled, height_px);
                            ctx.lineTo(x_scaled, y);
                        } else {
                            ctx.moveTo(x_scaled, y);
                        }
                    }
                }
            }
        }
        if (mode === "Filled") {
            if (in_path) {
                ctx.lineTo(x_scaled, height_px);
            }
            ctx.fill();
        } else {
            ctx.stroke();
        }
        parent_element.append( canvas );
        return canvas;
    }, gen_options: function(track_id) {
        var container = $("<div />").addClass("form-row");
        
        var minval = 'track_' + track_id + '_minval',
            min_label = $('<label></label>').attr("for", minval).text("Min value:"),
            min_val = (this.prefs.min_value === undefined ? "" : this.prefs.min_value),
            min_input = $('<input></input>').attr("id", minval).val(min_val),
            maxval = 'track_' + track_id + '_maxval',
            max_label = $('<label></label>').attr("for", maxval).text("Max value:"),
            max_val = (this.prefs.max_value === undefined ? "" : this.prefs.max_value),
            max_input = $('<input></input>').attr("id", maxval).val(max_val),
            mode = 'track_' + track_id + '_mode',
            mode_label = $('<label></label>').attr("for", mode).text("Display mode:"),
            mode_val = (this.prefs.mode === undefined ? "Line" : this.prefs.mode),
            mode_input = $('<select id="' +mode+ '"><option value="Line" id="mode_Line">Line</option><option value="Filled" id="mode_Filled">Filled</option><option value="Intensity" id="mode_Intensity">Intensity</option></select>');
            
            mode_input.children("#mode_"+mode_val).attr('selected', 'selected');
            
        return container.append(min_label).append(min_input).append(max_label).append(max_input).append(mode_label).append(mode_input);
    }, update_options: function(track_id) {
        var min_value = $('#track_' + track_id + '_minval').val(),
            max_value = $('#track_' + track_id + '_maxval').val(),
            mode = $('#track_' + track_id + '_mode option:selected').val();
        if ( min_value !== this.prefs.min_value || max_value !== this.prefs.max_value || mode !== this.prefs.mode ) {
            this.prefs.min_value = parseFloat(min_value);
            this.prefs.max_value = parseFloat(max_value);
            this.prefs.mode = mode;
            this.vertical_range = this.prefs.max_value - this.prefs.min_value;
            // Update the y-axis
            $('#linetrack_' + track_id + '_minval').text(this.prefs.min_value);
            $('#linetrack_' + track_id + '_maxval').text(this.prefs.max_value);
            this.tile_cache.clear();
            this.draw();
        }
    }
});

var FeatureTrack = function ( name, view, dataset_id, prefs ) {
    this.track_type = "FeatureTrack";
    Track.call( this, name, view, view.viewport_container );
    TiledTrack.call( this );
    
    this.height_px = 0;
    this.container_div.addClass( "feature-track" );
    this.dataset_id = dataset_id;
    this.zo_slots = {};
    this.show_labels_scale = 0.001;
    this.showing_details = false;
    this.vertical_detail_px = 10;
    this.vertical_nodetail_px = 3;
    this.default_font = "9px Monaco, Lucida Console, monospace";
    this.inc_slots = {};
    this.data_queue = {};
    this.s_e_by_tile = {};
    this.tile_cache = new Cache(CACHED_TILES_FEATURE);
    this.data_cache = new Cache(20);
    
    this.prefs = { 'block_color': 'black', 'label_color': 'black', 'show_counts': false };
    if (prefs.block_color !== undefined) { this.prefs.block_color = prefs.block_color; }
    if (prefs.label_color !== undefined) { this.prefs.label_color = prefs.label_color; }
    if (prefs.show_counts !== undefined) { this.prefs.show_counts = prefs.show_counts; }
};
$.extend( FeatureTrack.prototype, TiledTrack.prototype, {
    init: function() {
        var track = this,
            key = track.view.max_low + '_' + track.view.max_high;
            track.mode = "Auto";
            if (track.mode_div) {
                track.mode_div.remove();
            }
            
            this.init_each({  low: track.view.max_low, 
                                    high: track.view.max_high, dataset_id: track.dataset_id,
                                    chrom: track.view.chrom, resolution: this.view.resolution }, function (result) {
            
            track.mode_div = $("<div class='right-float menubutton popup' />").text("Display Mode");
            track.header_div.append(track.mode_div);
            track.mode = "Auto";
            var change_mode = function(name) {
                track.mode_div.text(name);
                track.mode = name;
                track.tile_cache.clear();
                track.draw();
            };
            make_popupmenu(track.mode_div, {
                "Auto": function() {
                    change_mode("Auto");
                },
                "Dense": function() {
                    change_mode("Dense");
                },
                "Squish": function() {
                    change_mode("Squish");
                },
                "Pack": function() {
                    change_mode("Pack");
                }
            });
            track.data_cache.set(key, result);
            track.draw();
        });
    },
    get_data: function( low, high ) {
        var track = this,
            key = low + '_' + high;
        
        if (!track.data_queue[key]) {
            track.data_queue[key] = true;
            $.getJSON( data_url, {  chrom: track.view.chrom, 
                                    low: low, high: high, dataset_id: track.dataset_id,
                                    resolution: this.view.resolution, mode: this.mode }, function (result) {
                track.data_cache.set(key, result);
                // console.log("datacache", track.data_cache.get(key));
                delete track.data_queue[key];
                track.draw();
            });
        }
    },
    incremental_slots: function( level, features, no_detail, mode ) {
        if (!this.inc_slots[level]) {
            this.inc_slots[level] = {};
            this.inc_slots[level].w_scale = 1 / level;
            this.inc_slots[level].mode = mode;
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
            
        var slotted = [];
        
        // Reset packing when we change display mode
        if (this.inc_slots[level].mode !== mode) {
            delete this.inc_slots[level];
            this.inc_slots[level] = { "mode": mode, "w_scale": w_scale };
            delete this.s_e_by_tile[level];
            this.s_e_by_tile[level] = {};
        }
        // If feature already exists in slots (from previously seen tiles), use the same slot,
        // otherwise if not seen, add to "undone" list for slot calculation
        for (var i = 0, len = features.length; i < len; i++) {
            var feature = features[i],
                feature_uid = feature[0];
            if (this.inc_slots[level][feature_uid] !== undefined) {
                highest_slot = Math.max(highest_slot, this.inc_slots[level][feature_uid]);
                slotted.push(this.inc_slots[level][feature_uid]);
            } else {
                undone.push(i);
            }
        }
        
        // console.log("Slotted: ", features.length - undone.length, "/", features.length, slotted);
        for (var i = 0, len = undone.length; i < len; i++) {
            var feature = features[undone[i]],
                feature_uid = feature[0],
                feature_start = feature[1],
                feature_end = feature[2],
                feature_name = feature[3],
                f_start = Math.floor( (feature_start - max_low) * w_scale ),
                f_end = Math.ceil( (feature_end - max_low) * w_scale );
                        
            if (feature_name !== undefined && !no_detail) {
                var text_len = dummy_canvas.measureText(feature_name).width;
                if (f_start - text_len < 0) {
                    f_end += text_len;
                } else {
                    f_start -= text_len;
                }
            }
            
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
                    this.inc_slots[level][feature_uid] = j;
                    highest_slot = Math.max(highest_slot, j);
                    break;
                }
                j++;
            }
        }
        return highest_slot;
        
    },
    rect_or_text: function( ctx, w_scale, tile_low, tile_high, feature_start, name, x, x_len, y_center ) {
        ctx.textAlign = "center";
        var gap = Math.round(w_scale / 2);
        if ( (this.mode === "Pack" || this.mode === "Auto") && name !== undefined && w_scale > PX_PER_CHAR) {
            ctx.fillStyle = this.prefs.block_color;
            ctx.fillRect(x, y_center + 1, x_len, 9);
            ctx.fillStyle = "#eee";
            for (var c = 0, str_len = name.length; c < str_len; c++) {
                if (feature_start + c >= tile_low && feature_start + c <= tile_high) {
                    var c_start = Math.floor( Math.max(0, (feature_start + c - tile_low) * w_scale) );
                    ctx.fillText(name[c], c_start + this.left_offset + gap, y_center + 9);
                }
            }
        } else {
            ctx.fillStyle = this.prefs.block_color;
            ctx.fillRect(x, y_center + 4, x_len, 3);
        }
    },
    draw_tile: function( resolution, tile_index, parent_element, w_scale ) {
        var tile_low = tile_index * DENSITY * resolution,
            tile_high = ( tile_index + 1 ) * DENSITY * resolution,
            tile_span = DENSITY * resolution;
        // console.log("drawing " + tile_index);

        /*for (var k in this.data_cache.obj_cache) {
            var k_split = k.split("_"), k_low = k_split[0], k_high = k_split[1];
            if (k_low <= tile_low && k_high >= tile_high) {
                data = this.data_cache.get(k);
                break;
            }
        }*/
        
        // var k = this.view.low + '_' + this.view.high;
        var k = tile_low + '_' + tile_high;
        var result = this.data_cache.get(k);
        
        if (result === undefined) {
            this.data_queue[ [tile_low, tile_high] ] = true;
            this.get_data(tile_low, tile_high);
            return;
        }
        
        var width = Math.ceil( tile_span * w_scale ),
            new_canvas = $("<canvas class='tile'></canvas>"),
            label_color = this.prefs.label_color,
            block_color = this.prefs.block_color,
            mode = this.mode,
            no_detail = (mode === "Squish") || (mode === "Dense") && (mode !== "Pack") || (mode === "Auto" && (result.extra_info === "no_detail")),
            left_offset = this.left_offset,
            slots, required_height, y_scale;
        
        if (result.dataset_type === "summary_tree") {
            required_height = 30;
        } else if (mode === "Dense") {
            required_height = 15;
            y_scale = 10;
        } else {
            // Calculate new slots incrementally for this new chunk of data and update height if necessary
            y_scale = ( no_detail ? this.vertical_nodetail_px : this.vertical_detail_px );
            required_height = this.incremental_slots( this.view.zoom_res, result.data, no_detail, mode ) * y_scale + 15;
            slots = this.inc_slots[this.view.zoom_res];
        }
        
        new_canvas.css({
            position: "absolute",
            top: 0,
            left: ( tile_low - this.view.low ) * w_scale - left_offset
        });
        new_canvas.get(0).width = width + left_offset;
        new_canvas.get(0).height = required_height;
        parent_element.parent().css("height", Math.max(this.height_px, required_height) + "px");
        // console.log(( tile_low - this.view.low ) * w_scale, tile_index, w_scale);
        var ctx = new_canvas.get(0).getContext("2d");
        ctx.fillStyle = block_color;
        ctx.font = this.default_font;
        ctx.textAlign = "right";
        
        if (result.dataset_type == "summary_tree") {
            var color,
                min_color = 55,
                color_span = 255 - min_color,
                color_cutoff = color_span*2/3, // Where text switches from black to white
                points = result.data,
                max = result.max,
                avg = result.avg;
            if (points.length > 2) {
                var delta_x_px = Math.ceil((points[1][0] - points[0][0]) * w_scale);
            } else {
                var delta_x_px = 50; // Arbitrary, fix
            }
        
            for ( var i = 0, len = points.length; i < len; i++ ) {
                var x = Math.ceil( (points[i][0] - tile_low) * w_scale );
                var y = points[i][1];
            
                if (!y) { continue; }
                color = Math.floor( color_span - (y / max) * color_span );
                ctx.fillStyle = "rgb(" +color+ "," +color+ "," +color+ ")";
                ctx.fillRect(x + left_offset, 0, delta_x_px, 20);

                if (this.prefs.show_counts) {
                    if (color > color_cutoff) {
                        ctx.fillStyle = "black";
                    } else {
                        ctx.fillStyle = "#ddd";
                    }
                    ctx.textAlign = "center";
                    ctx.fillText(points[i][1], x + left_offset + (delta_x_px/2), 12);
                }
            }
            
            parent_element.append( new_canvas );
            return new_canvas;
        }
        
        var data = result.data;
        var j = 0;
        for (var i = 0, len = data.length; i < len; i++) {
            var feature = data[i],
                feature_uid = feature[0],
                feature_start = feature[1],
                feature_end = feature[2],
                feature_name = feature[3];
                
            if (feature_start <= tile_high && feature_end >= tile_low) {
                var f_start = Math.floor( Math.max(0, (feature_start - tile_low) * w_scale) ),
                    f_end   = Math.ceil( Math.min(width, Math.max(0, (feature_end - tile_low) * w_scale)) ),
                    y_center = (mode === "Dense" ? 0 : slots[feature_uid] * y_scale);
                
                if (result.dataset_type === "bai") {
                    ctx.fillStyle = block_color;
                    if (feature[4] instanceof Array) {
                        var b1_start = Math.floor( Math.max(0, (feature[4][0] - tile_low) * w_scale) ),
                            b1_end   = Math.ceil( Math.min(width, Math.max(0, (feature[4][1] - tile_low) * w_scale)) ),
                            b2_start = Math.floor( Math.max(0, (feature[5][0] - tile_low) * w_scale) ),
                            b2_end   = Math.ceil( Math.min(width, Math.max(0, (feature[5][1] - tile_low) * w_scale)) );
                        
                        if (feature[4][1] >= tile_low && feature[4][0] <= tile_high) {
                            this.rect_or_text(ctx, w_scale, tile_low, tile_high, feature[4][0], feature[4][2], b1_start + left_offset, b1_end - b1_start, y_center);
                        }
                        if (feature[5][1] >= tile_low && feature[5][0] <= tile_high) {
                            this.rect_or_text(ctx, w_scale, tile_low, tile_high, feature[5][0], feature[5][2], b2_start + left_offset, b2_end - b2_start, y_center);
                        }
                        if (b2_start > b1_end) {
                            ctx.fillStyle = "#999";
                            ctx.fillRect(b1_end + left_offset, y_center + 5, b2_start - b1_end, 1);
                        }
                    } else {
                        ctx.fillStyle = block_color;
                        this.rect_or_text(ctx, w_scale, tile_low, tile_high, feature_start, feature_name, f_start + left_offset, f_end - f_start, y_center);
                    }
                    if (mode !== "Dense" && !no_detail && feature_start > tile_low) {
                        // Draw label
                        ctx.fillStyle = this.prefs.label_color;
                        if (tile_index === 0 && f_start - ctx.measureText(feature_name).width < 0) {
                            ctx.textAlign = "left";
                            ctx.fillText(feature_uid, f_end + 2 + left_offset, y_center + 8);
                        } else {
                            ctx.textAlign = "right";
                            ctx.fillText(feature_uid, f_start - 2 + left_offset, y_center + 8);
                        }
                        ctx.fillStyle = block_color;
                    }
                        
                } else if (result.dataset_type === "interval_index") {
                    
                    // console.log(feature_uid, feature_start, feature_end, f_start, f_end, y_center);
                    if (no_detail) {
                        ctx.fillRect(f_start + left_offset, y_center + 5, f_end - f_start, 1);
                    } else {
                        // Showing labels, blocks, details
                        var feature_strand = feature[4],
                            feature_ts = feature[5],
                            feature_te = feature[6],
                            feature_blocks = feature[7];
                    
                        var thickness, y_start, thick_start = null, thick_end = null;
                        if (feature_ts && feature_te) {
                            thick_start = Math.floor( Math.max(0, (feature_ts - tile_low) * w_scale) );
                            thick_end = Math.ceil( Math.min(width, Math.max(0, (feature_te - tile_low) * w_scale)) );
                        }
                        if (mode !== "Dense" && feature_name !== undefined && feature_start > tile_low) {
                            // Draw label
                            ctx.fillStyle = label_color;
                            if (tile_index === 0 && f_start - ctx.measureText(feature_name).width < 0) {
                                ctx.textAlign = "left";
                                ctx.fillText(feature_name, f_end + 2 + left_offset, y_center + 8);
                            } else {
                                ctx.textAlign = "right";
                                ctx.fillText(feature_name, f_start - 2 + left_offset, y_center + 8);
                            }
                            ctx.fillStyle = block_color;
                        }
                        if (feature_blocks) {
                            // Draw introns
                            if (feature_strand) {
                                if (feature_strand == "+") {
                                    ctx.fillStyle = RIGHT_STRAND;
                                } else if (feature_strand == "-") {
                                    ctx.fillStyle = LEFT_STRAND;
                                }
                                ctx.fillRect(f_start + left_offset, y_center, f_end - f_start, 10);
                                ctx.fillStyle = block_color;
                            }
                        
                            for (var k = 0, k_len = feature_blocks.length; k < k_len; k++) {
                                var block = feature_blocks[k],
                                    block_start = Math.floor( Math.max(0, (block[0] - tile_low) * w_scale) ),
                                    block_end = Math.ceil( Math.min(width, Math.max((block[1] - tile_low) * w_scale)) );
                                if (block_start > block_end) { continue; }
                                // Draw the block
                                thickness = 5;
                                y_start = 3;
                                ctx.fillRect(block_start + left_offset, y_center + y_start, block_end - block_start, thickness);
                            
                                // Draw thick regions: check if block intersects with thick region
                                if (thick_start !== undefined && !(block_start > thick_end || block_end < thick_start) ) {
                                    thickness = 9;
                                    y_start = 1;
                                    var block_thick_start = Math.max(block_start, thick_start),
                                        block_thick_end = Math.min(block_end, thick_end);
                                    ctx.fillRect(block_thick_start + left_offset, y_center + y_start, block_thick_end - block_thick_start, thickness);

                                }
                            }
                        } else {
                            // If there are no blocks, we treat the feature as one big exon
                            thickness = 9;
                            y_start = 1;
                            ctx.fillRect(f_start + left_offset, y_center + y_start, f_end - f_start, thickness);
                            if ( feature.strand ) {
                                if (feature.strand == "+") {
                                    ctx.fillStyle = RIGHT_STRAND_INV;
                                } else if (feature.strand == "-") {
                                    ctx.fillStyle = LEFT_STRAND_INV;
                                }
                                ctx.fillRect(f_start + left_offset, y_center, f_end - f_start, 10);
                                ctx.fillStyle = prefs.block_color;
                            }
                        }
                    }
                }
                j++;
            }
        }
        parent_element.append( new_canvas );
        return new_canvas;
    }, gen_options: function(track_id) {
        var container = $("<div />").addClass("form-row");

        var block_color = 'track_' + track_id + '_block_color',
            block_color_label = $('<label />').attr("for", block_color).text("Block color:"),
            block_color_input = $('<input />').attr("id", block_color).attr("name", block_color).val(this.prefs.block_color),
            label_color = 'track_' + track_id + '_label_color',
            label_color_label = $('<label />').attr("for", label_color).text("Text color:"),
            label_color_input = $('<input />').attr("id", label_color).attr("name", label_color).val(this.prefs.label_color),
            show_count = 'track_' + track_id + '_show_count',
            show_count_label = $('<label />').attr("for", show_count).text("Show summary counts"),
            show_count_input = $('<input type="checkbox" style="float:left;"></input>').attr("id", show_count).attr("name", show_count).attr("checked", this.prefs.show_counts),
            show_count_div = $('<div />').append(show_count_input).append(show_count_label);
            
        return container.append(block_color_label).append(block_color_input).append(label_color_label).append(label_color_input).append(show_count_div);
    }, update_options: function(track_id) {
        var block_color = $('#track_' + track_id + '_block_color').val(),
            label_color = $('#track_' + track_id + '_label_color').val(),
            mode = $('#track_' + track_id + '_mode option:selected').val(),
            show_counts = $('#track_' + track_id + '_show_count').attr("checked");
        if (block_color !== this.prefs.block_color || label_color !== this.prefs.label_color || show_counts !== this.prefs.show_counts) {
            this.prefs.block_color = block_color;
            this.prefs.label_color = label_color;
            this.prefs.show_counts = show_counts;
            this.tile_cache.clear();
            this.draw();
        }
    }
});

var ReadTrack = function ( name, view, dataset_id, prefs ) {
    FeatureTrack.call( this, name, view, dataset_id, prefs );
    this.track_type = "ReadTrack";
    this.vertical_detail_px = 10;
    this.vertical_nodetail_px = 5;
    
};
$.extend( ReadTrack.prototype, TiledTrack.prototype, FeatureTrack.prototype, {
});
