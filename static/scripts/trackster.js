/* Trackster
    2010-2011: James Taylor, Kanwei Li, Jeremy Goecks
*/

/** Simple extend function for inheritence */
var extend = function() {
    var target = arguments[0];
    for ( var i = 1; i < arguments.length; i++ ) {
        var other = arguments[i];
        for ( key in other ) {
            target[key] = other[key];
        }
    }
};

// Encapsulate -- anything to be availabe outside this block is added to exports
var trackster_module = function(require, exports){

var slotting = require('slotting'),
    painters = require('painters');
    
// ---- Canvas management and extensions ----

/**
 * Canvas manager is used to create canvases, for browsers, this deals with
 * backward comparibility using excanvas, as well as providing a pattern cache
 */
var CanvasManager = function( document, default_font ) {
    this.document = document;
    this.default_font = default_font !== undefined ? default_font : "9px Monaco, Lucida Console, monospace";
    
    this.dummy_canvas = this.new_canvas();
    this.dummy_context = this.dummy_canvas.getContext('2d');
    this.dummy_context.font = this.default_font;
    
    this.char_width_px = this.dummy_context.measureText("A").width;
    
    this.patterns = {};

    // FIXME: move somewhere to make this more general
    this.load_pattern( 'right_strand', "/visualization/strand_right.png" );
    this.load_pattern( 'left_strand', "/visualization/strand_left.png" );
    this.load_pattern( 'right_strand_inv', "/visualization/strand_right_inv.png" );
    this.load_pattern( 'left_strand_inv', "/visualization/strand_left_inv.png" );
}

extend( CanvasManager.prototype, {
    load_pattern: function( key, path ) {
        var patterns = this.patterns,
            dummy_context = this.dummy_context,
            image = new Image();
        // FIXME: where does image_path come from? not in browser.mako...
        image.src = image_path + path;
        image.onload = function() {
            patterns[key] = dummy_context.createPattern( image, "repeat" );
        }
    },
    get_pattern: function( key ) {
        return this.patterns[key];
    },
    new_canvas: function() {
        var canvas = this.document.createElement("canvas");
        // If using excanvas in IE, we need to explicately attach the canvas
        // methods to the DOM element
        if (window.G_vmlCanvasManager) { G_vmlCanvasManager.initElement(canvas); }
        // Keep a reference back to the manager
        canvas.manager = this;
        return canvas;
    }
});

// ---- Web UI specific utilities ----

/** 
 * Make `element` sortable in parent by dragging `handle` (a selector)
 */
var sortable = function( element, handle ) {
    element.bind( "drag", { handle: handle, relative: true }, function ( e, d ) {
        var parent = $(this).parent();
        var children = parent.children();
        var i;
        // Determine new position
        for ( i = 0; i < children.length; i++ ) {
            if ( d.offsetY < $(children.get(i)).position().top ) {
                break;
            }
        }
        // If not already in the right place, move. Need 
        // to handle the end specially since we don't have 
        // insert at index
        if ( i === children.length ) {
            if ( this !== children.get( i - 1 ) ) {
                parent.append( this );
            }
        }
        else if ( this !== children.get( i ) ) {
            $(this).insertBefore( children.get( i ) );
        }
    });
}

/**
 * Calculates step for slider with a given min, max.
 */
var get_slider_step = function(min, max) {
    var range = max - min;
    return (range <= 2 ? 0.01 : (range <= 100 ? 1 : (range <= 1000 ? 5 : 10)));
}

/**
 * Init constants & functions used throughout trackster.
 */
var 
    // Drawing constants; track height is (constant) height of track, and feature height is the
    // height of individual features within tracks. Feature height, then, should always be less
    // than track height.
    CHAR_HEIGHT_PX = 9, // FIXME: font size may not be static
    ERROR_PADDING = 10, // Padding at the top of tracks for error messages
    SUMMARY_TREE_TOP_PADDING = CHAR_HEIGHT_PX + 2,
    // Maximum number of rows un a slotted track
    MAX_FEATURE_DEPTH = 100,
    // Minimum width for window for squish to be used.
    MIN_SQUISH_VIEW_WIDTH = 12000,
    
    // Other constants.
    DENSITY = 200,
    FEATURE_LEVELS = 10,
    DEFAULT_DATA_QUERY_WAIT = 5000,
    // Maximum number of chromosomes that are selectable at any one time.
    MAX_CHROMS_SELECTABLE = 100,
    DATA_ERROR = "There was an error in indexing this dataset. ",
    DATA_NOCONVERTER = "A converter for this dataset is not installed. Please check your datatypes_conf.xml file.",
    DATA_NONE = "No data for this chrom/contig.",
    DATA_PENDING = "Currently indexing... please wait",
    DATA_CANNOT_RUN_TOOL = "Tool cannot be rerun: ",
    DATA_LOADING = "Loading data...",
    DATA_OK = "Ready for display",
    CACHED_TILES_FEATURE = 10,
    CACHED_TILES_LINE = 5,
    CACHED_DATA = 5;

function round_1000(num) {
    return Math.round(num * 1000) / 1000;    
}

/**
 * Generic cache that handles key/value pairs.
 */ 
var Cache = function( num_elements ) {
    this.num_elements = num_elements;
    this.clear();
};
extend(Cache.prototype, {
    get: function(key) {
        var index = this.key_ary.indexOf(key);
        if (index !== -1) {
            this.move_key_to_end(key, index);
        }
        return this.obj_cache[key];
    },
    set: function(key, value) {
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
    // Move key to end of cache. Keys are removed from the front, so moving a key to the end 
    // delays the key's removal.
    move_key_to_end: function(key, index) {
        this.key_ary.splice(index, 1);
        this.key_ary.push(key);
    },
    clear: function() {
        this.obj_cache = {};
        this.key_ary = [];
    },
    // Returns the number of elements in the cache.
    size: function() {
        return this.key_ary.length;
    }
});

/**
 * Data manager for a track.
 */
var DataManager = function(num_elements, track, subset) {
    Cache.call(this, num_elements);
    this.track = track;
    this.subset = (subset !== undefined ? subset : true);
};
extend(DataManager.prototype, Cache.prototype, {
    /**
     * Load data from server; returns AJAX object so that use of Deferred is possible.
     */
    load_data: function(chrom, low, high, mode, resolution, extra_params) {
        // Setup data request params.
        var params = {"chrom": chrom, "low": low, "high": high, "mode": mode, 
                      "resolution": resolution, "dataset_id" : this.track.dataset_id, 
                      "hda_ldda": this.track.hda_ldda};
        $.extend(params, extra_params);
        
        // Add track filters to params.
        var filter_names = [];
        for (var i = 0; i < this.track.filters.length; i++) {
            filter_names[filter_names.length] = this.track.filters[i].name;
        }
        params.filter_cols = JSON.stringify(filter_names);
                
        // Do request.
        var manager = this;
        return $.getJSON(this.track.data_url, params, function (result) {
            manager.set_data(low, high, mode, result);
        });
    },
    /**
     * Get data and do callback.
     */
    get_data: function(chrom, low, high, mode, resolution, extra_params) {
        // Debugging:
        //console.log("get_data", low, high, mode);
        /*
        console.log("cache contents:")
        for (var i = 0; i < this.key_ary.length; i++) {
            console.log("\t", this.key_ary[i], this.obj_cache[this.key_ary[i]]);
        }
        */
        
        // Look for key in cache and, if found, do callback.
        var entry = this.get(this.gen_key(low, high, mode));
        if (entry) {
            return entry;
        }

        //
        // If data supports subsetting:
        // Look in cache for data that can be used. Data can be reused if it
        // has the requested data and is not summary tree and has details.
        // TODO: this logic could be improved if the visualization knew whether
        // the data was "index" or "data." Also could slice the data so that
        // only data points in request are returned.
        //
        
        /* Disabling for now, more detailed data is never loaded for line tracks
        if (this.subset) {
            var key, split_key, entry_low, entry_high, mode, entry;
            for (var i = 0; i < this.key_ary.length; i++) {
                key = this.key_ary[i];
                split_key = this.split_key(key);
                entry_low = split_key[0];
                entry_high = split_key[1];
            
                if (low >= entry_low && high <= entry_high) {
                    // This track has the range of data needed; check other attributes.
                    entry = this.obj_cache[key];
                    if (entry.dataset_type !== "summary_tree" && entry.extra_info !== "no_detail") {
                        // Data is usable.
                        this.move_key_to_end(key, i);
                        return entry;
                    }
                }
            }
        }
        */
                
        // Load data from server. The deferred is immediately saved until the
        // data is ready, it then replaces itself with the actual data
        entry = this.load_data(chrom, low, high, mode, resolution, extra_params);
        this.set_data( low, high, mode, entry );
        return entry
    },
    set_data: function(low, high, mode, result) {
        //console.log("set_data", low, high, mode, result);
        return this.set(this.gen_key(low, high, mode), result);
    },
    /**
     * Generate key for cache.
     */
    gen_key: function(low, high, mode) {
        var key = low + "_" + high + "_" + mode;
        return key;
    },
    /**
     * Split key from cache into array with format [low, high, mode]
     */
    split_key: function(key) {
        return key.split("_");
    }
});

/**
 * View object manages complete viz view, including tracks and user interactions.
 */
var View = function( container, title, vis_id, dbkey, callback ) {
    this.container = container;
    this.chrom = null;
    this.vis_id = vis_id;
    this.dbkey = dbkey;
    this.title = title;
    this.tracks = [];
    this.label_tracks = [];
    this.max_low = 0;
    this.max_high = 0;
    this.num_tracks = 0;
    this.track_id_counter = 0;
    this.zoom_factor = 3;
    this.min_separation = 30;
    this.has_changes = false;
    this.init( callback );
    this.canvas_manager = new CanvasManager( container.get(0).ownerDocument );
    this.reset();
};
extend( View.prototype, {
    init: function( callback ) {
        // Create DOM elements
        var parent_element = this.container,
            view = this;
        // Top container for things that are fixed at the top
        this.top_container = $("<div/>").addClass("top-container").appendTo(parent_element);
        // Content container, primary tracks are contained in here
        this.content_div = $("<div/>").addClass("content").css("position", "relative").appendTo(parent_element);
        // Bottom container for things that are fixed at the bottom
        this.bottom_container = $("<div/>").addClass("bottom-container").appendTo(parent_element);
        // Label track fixed at top 
        this.top_labeltrack = $("<div/>").addClass("top-labeltrack").appendTo(this.top_container);        
        // Viewport for dragging tracks in center    
        this.viewport_container = $("<div/>").addClass("viewport-container").addClass("viewport-container").appendTo(this.content_div);
        // Future overlay?
        this.intro_div = $("<div/>").addClass("intro").text("Select a chrom from the dropdown below").hide(); 
        // Another label track at bottom
        this.nav_labeltrack = $("<div/>").addClass("nav-labeltrack").appendTo(this.bottom_container);
        // Navigation at top
        this.nav_container = $("<div/>").addClass("nav-container").prependTo(this.top_container);
        this.nav = $("<div/>").addClass("nav").appendTo(this.nav_container);
        // Overview (scrollbar and overview plot) at bottom
        this.overview = $("<div/>").addClass("overview").appendTo(this.bottom_container);
        this.overview_viewport = $("<div/>").addClass("overview-viewport").appendTo(this.overview);
        this.overview_close = $("<a href='javascript:void(0);'>Close Overview</a>").addClass("overview-close").hide().appendTo(this.overview_viewport);
        this.overview_highlight = $("<div/>").addClass("overview-highlight").hide().appendTo(this.overview_viewport);
        this.overview_box_background = $("<div/>").addClass("overview-boxback").appendTo(this.overview_viewport);
        this.overview_box = $("<div/>").addClass("overview-box").appendTo(this.overview_viewport);
        this.default_overview_height = this.overview_box.height();
        
        this.nav_controls = $("<div/>").addClass("nav-controls").appendTo(this.nav);
        this.chrom_select = $("<select/>").attr({ "name": "chrom"}).css("width", "15em").addClass("no-autocomplete").append("<option value=''>Loading</option>").appendTo(this.nav_controls);
        var submit_nav = function(e) {
            if (e.type === "focusout" || (e.keyCode || e.which) === 13 || (e.keyCode || e.which) === 27 ) {
                if ((e.keyCode || e.which) !== 27) { // Not escape key
                    view.go_to( $(this).val() );
                }
                $(this).hide();
                $(this).val('');
                view.location_span.show();
                view.chrom_select.show();
            }
        };
        this.nav_input = $("<input/>").addClass("nav-input").hide().bind("keyup focusout", submit_nav).appendTo(this.nav_controls);
        this.location_span = $("<span/>").addClass("location").appendTo(this.nav_controls);
        this.location_span.bind("click", function() {
            view.location_span.hide();
            view.chrom_select.hide();
            view.nav_input.val(view.chrom + ":" + view.low + "-" + view.high);
            view.nav_input.css("display", "inline-block");
            view.nav_input.select();
            view.nav_input.focus();
        });
        if (this.vis_id !== undefined) {
            this.hidden_input = $("<input/>").attr("type", "hidden").val(this.vis_id).appendTo(this.nav_controls);
        }
        this.zo_link = $("<a id='zoom-out' />").click(function() { view.zoom_out(); view.redraw(); }).appendTo(this.nav_controls);
        this.zi_link = $("<a id='zoom-in' />").click(function() { view.zoom_in(); view.redraw(); }).appendTo(this.nav_controls);        
        
        // Get initial set of chroms.
        this.load_chroms({low: 0}, callback);
        this.chrom_select.bind("change", function() {
            view.change_chrom(view.chrom_select.val());
        });
        this.intro_div.show();
                
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
        
        // Blur tool/filter inputs when user clicks on content div.
        this.content_div.bind("click", function( e ) {
            $(this).find("input").trigger("blur"); 
        });

        // Double clicking zooms in
        this.content_div.bind("dblclick", function( e ) {
            view.zoom_in(e.pageX, this.viewport_container);
        });

        // Dragging the overview box (~ horizontal scroll bar)
        this.overview_box.bind("dragstart", function( e, d ) {
            this.current_x = d.offsetX;
        }).bind("drag", function( e, d ) {
            var delta = d.offsetX - this.current_x;
            this.current_x = d.offsetX;
            var delta_chrom = Math.round(delta / view.viewport_container.width() * (view.max_high - view.max_low) );
            view.move_delta(-delta_chrom);
        });
        
        this.overview_close.bind("click", function() {
            for (var track_id = 0, len = view.tracks.length; track_id < len; track_id++) {
                view.tracks[track_id].is_overview = false;
            }
            $(this).siblings().filter("canvas").remove();
            $(this).parent().css("height", view.overview_box.height());
            view.overview_highlight.hide();
            $(this).hide();
        });
        
        // Dragging in the viewport scrolls
        this.viewport_container.bind( "draginit", function( e, d ) {
            // Disable interaction if started in scrollbar (for webkit)
            if ( e.clientX > view.viewport_container.width() - 16 ) {
                return false;
            }
        }).bind( "dragstart", function( e, d ) {
            d.original_low = view.low;
            d.current_height = e.clientY;
            d.current_x = d.offsetX;
        }).bind( "drag", function( e, d ) {
            var container = $(this);
            var delta = d.offsetX - d.current_x;
            var new_scroll = container.scrollTop() - (e.clientY - d.current_height);
            container.scrollTop(new_scroll);
            d.current_height = e.clientY;
            d.current_x = d.offsetX;
            var delta_chrom = Math.round(delta / view.viewport_container.width() * (view.high - view.low));
            view.move_delta(delta_chrom);
        // Also capture mouse wheel for left/right scrolling
        }).bind( 'mousewheel', function( e, d, dx, dy ) { 
            // Only act on x axis scrolling if we see if, y will be i
            // handled by the browser when the event bubbles up
            if ( dx ) {
                var delta_chrom = Math.round( - dx / view.viewport_container.width() * (view.high - view.low) );
                view.move_delta( delta_chrom );
            }
        });
       
        // Dragging in the top label track allows selecting a region
        // to zoom in 
        this.top_labeltrack.bind( "dragstart", function( e, d ) {
            return $("<div />").css( { 
                "height": view.content_div.height() + view.top_labeltrack.height() 
                            + view.nav_labeltrack.height() + 1, 
                "top": "0px", 
                "position": "absolute", 
                "background-color": "#ccf", 
                "opacity": 0.5, 
                 "z-index": 1000
            } ).appendTo( $(this) );
        }).bind( "drag", function( e, d ) {
            $( d.proxy ).css({ left: Math.min( e.pageX, d.startX ), width: Math.abs( e.pageX - d.startX ) });
            var min = Math.min(e.pageX, d.startX ) - view.container.offset().left,
                max = Math.max(e.pageX, d.startX ) - view.container.offset().left,
                span = (view.high - view.low),
                width = view.viewport_container.width();
            view.update_location( Math.round(min / width * span) + view.low, 
                                  Math.round(max / width * span) + view.low );
        }).bind( "dragend", function( e, d ) {
            var min = Math.min(e.pageX, d.startX),
                max = Math.max(e.pageX, d.startX),
                span = (view.high - view.low),
                width = view.viewport_container.width(),
                old_low = view.low;
            view.low = Math.round(min / width * span) + old_low;
            view.high = Math.round(max / width * span) + old_low;
            $(d.proxy).remove();
            view.redraw();
        });
        
        this.add_label_track( new LabelTrack( this, this.top_labeltrack ) );
        this.add_label_track( new LabelTrack( this, this.nav_labeltrack ) );
        
        $(window).bind("resize", function() { view.resize_window(); });
        $(document).bind("redraw", function() { view.redraw(); });
        
        this.reset();
        $(window).trigger("resize");
    },
    update_location: function(low, high) {
        this.location_span.text( commatize(low) + ' - ' + commatize(high) );
        this.nav_input.val( this.chrom + ':' + commatize(low) + '-' + commatize(high) );
    },
    load_chroms: function(url_parms, callback) {
        url_parms['num'] = MAX_CHROMS_SELECTABLE;
        $.extend( url_parms, (this.vis_id !== undefined ? { vis_id: this.vis_id } : { dbkey: this.dbkey } ) );
        var view = this;
        $.ajax({
            url: chrom_url, 
            data: url_parms,
            dataType: "json",
            success: function (result) {
                // Show error if could not load chroms.
                if (result.chrom_info.length === 0) {
                    alert("Invalid chromosome: " + url_parms.chrom);
                    return;
                }
                
                // Load chroms.
                if (result.reference) {
                    view.add_label_track( new ReferenceTrack(view) );
                }
                view.chrom_data = result.chrom_info;
                var chrom_options = '<option value="">Select Chrom/Contig</option>';
                for (var i = 0, len = view.chrom_data.length; i < len; i++) {
                    var chrom = view.chrom_data[i].chrom;
                    chrom_options += '<option value="' + chrom + '">' + chrom + '</option>';
                }
                if (result.prev_chroms) {
                    chrom_options += '<option value="previous">Previous ' + MAX_CHROMS_SELECTABLE + '</option>';
                }
                if (result.next_chroms) {
                    chrom_options += '<option value="next">Next ' + MAX_CHROMS_SELECTABLE + '</option>';
                }
                view.chrom_select.html(chrom_options);
                if ( callback ) {
                    callback();
                }
                view.chrom_start_index = result.start_index;
            },
            error: function() {
                alert("Could not load chroms for this dbkey:", view.dbkey);
            }
        });
        
    },
    change_chrom: function(chrom, low, high) {
        // Don't do anything if chrom is "None" (hackish but some browsers already have this set), or null/blank
        if (!chrom || chrom === "None") {
            return;
        }
        
        var view = this;
        
        //
        // If user is navigating to previous/next set of chroms, load new chrom set and return.
        //
        if (chrom === "previous") {
            view.load_chroms({low: this.chrom_start_index - MAX_CHROMS_SELECTABLE});
            return;
        }
        if (chrom === "next") {
            view.load_chroms({low: this.chrom_start_index + MAX_CHROMS_SELECTABLE});
            return;
        }
    
        //
        // User is loading a particular chrom. Look first in current set; if not in current set, load new
        // chrom set.
        //
        var found = $.grep(view.chrom_data, function(v, i) {
            return v.chrom === chrom;
        })[0];
        if (found === undefined) {
            // Try to load chrom and then change to chrom.
            view.load_chroms({'chrom': chrom}, function() { view.change_chrom(chrom, low, high); });
            return;
        }
        else {
            // Switching to local chrom.
            if (chrom !== view.chrom) {
                view.chrom = chrom;
                if (!view.chrom) {
                    // No chrom selected
                    view.intro_div.show();
                } else {
                    view.intro_div.hide();
                }
                view.chrom_select.val(view.chrom);
                view.max_high = found.len-1; // -1 because we're using 0-based indexing.
                view.reset();
                view.redraw(true);

                for (var track_id = 0, len = view.tracks.length; track_id < len; track_id++) {
                    var track = view.tracks[track_id];
                    if (track.init) {
                        track.init();
                    }
                }
            }
            if (low !== undefined && high !== undefined) {
                view.low = Math.max(low, 0);
                view.high = Math.min(high, view.max_high);
            }
            view.reset_overview();
            view.redraw();
        }
    },
    go_to: function(str) {
        var view = this,
            new_low, 
            new_high,
            chrom_pos = str.split(":"),
            chrom = chrom_pos[0],
            pos = chrom_pos[1];
        
        if (pos !== undefined) {
            try {
                var pos_split = pos.split("-");
                new_low = parseInt(pos_split[0].replace(/,/g, ""), 10);
                new_high = parseInt(pos_split[1].replace(/,/g, ""), 10);
            } catch (e) {
                return false;
            }
        }
        view.change_chrom(chrom, new_low, new_high);
    },
    move_fraction : function( fraction ) {
        var view = this;
        var span = view.high - view.low;
        this.move_delta( fraction * span );
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
        sortable( track.container_div, '.draghandle' );
        this.track_id_counter += 1;
        this.num_tracks += 1;
    },
    add_label_track: function (label_track) {
        label_track.view = this;
        this.label_tracks.push(label_track);
    },
    remove_track: function(track) {
        this.has_changes = true;
        track.container_div.fadeOut('slow', function() { $(this).remove(); });
        delete this.tracks[this.tracks.indexOf(track)];
        this.num_tracks -= 1;
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
        var left_px = ( this.low / (this.max_high - this.max_low) * this.overview_viewport.width() ) || 0;
        var width_px = ( (this.high - this.low)/(this.max_high - this.max_low) * this.overview_viewport.width() ) || 0;
        var min_width_px = 13;
        
        this.overview_box.css({ left: left_px, width: Math.max(min_width_px, width_px) }).show();
        if (width_px < min_width_px) {
            this.overview_box.css("left", left_px - (min_width_px - width_px)/2);
        }
        if (this.overview_highlight) {
            this.overview_highlight.css({ left: left_px, width: width_px });
        }
        
        this.update_location(this.low, this.high);
        if (!nodraw) {
            for (var i = 0, len = this.tracks.length; i < len; i++) {
                if (this.tracks[i] && this.tracks[i].enabled) {
                    this.tracks[i].draw();
                }
            }
            for (i = 0, len = this.label_tracks.length; i < len; i++) {
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
    },
    resize_window: function() {
        this.viewport_container.height( this.container.height() - this.top_container.height() - this.bottom_container.height() );
        this.nav_container.width( this.container.width() );
        this.redraw();
    },
    reset_overview: function() {
        this.overview_viewport.find("canvas").remove();
        this.overview_viewport.height(this.default_overview_height);
        this.overview_box.height(this.default_overview_height);
        this.overview_close.hide();
        this.overview_highlight.hide();
    }
});

/**
 * Encapsulation of a tool that users can apply to tracks/datasets.
 */
var Tool = function(track, tool_dict) {
    //
    // Unpack tool information from dictionary.
    //
    this.track = track;
    this.name = tool_dict.name;
    this.params = [];
    var params_dict = tool_dict.params;
    for (var i = 0; i < params_dict.length; i++) {
        var param_dict = params_dict[i],
            name = param_dict.name,
            label = param_dict.label,
            html = unescape(param_dict.html),
            type = param_dict.type;
        if (type === "number") {
            this.params[this.params.length] = 
                new NumberParameter(name, label, html, param_dict.min, param_dict.max);
        }
        else if (type == "select") {
            this.params[this.params.length] = new ToolParameter(name, label, html);
        }
        else {
            console.log("WARNING: unrecognized tool parameter type:", name, type);
        }
    }
    
    //
    // Create div elt for tool UI.
    //
    this.parent_div = $("<div/>").addClass("dynamic-tool").hide();
    // Disable dragging, clicking, double clicking on div so that actions on slider do not impact viz.
    this.parent_div.bind("drag", function(e) {
        e.stopPropagation();
    }).bind("click", function(e) {
        e.stopPropagation();
    }).bind("dblclick", function(e) {
        e.stopPropagation();
    });
    var name_div = $("<div class='tool-name'>").appendTo(this.parent_div).text(this.name);
    var tool_params = this.params;
    var tool = this;
    $.each(this.params, function(index, param) {
        var param_div = $("<div>").addClass("param-row").appendTo(tool.parent_div);
        // Param label.
        var label_div = $("<div>").addClass("param-label").text(param.label).appendTo(param_div);
        // Param HTML.
        // TODO: either generalize .slider CSS attributes or create new rule for tool input div.
        var html_div = $("<div/>").addClass("slider").html(param.html).appendTo(param_div);
        
        // Add to clear floating layout.
        $("<div style='clear: both;'/>").appendTo(param_div);
    });
    
    // Highlight value for inputs for easy replacement.
    this.parent_div.find("input").click(function() { $(this).select() });
    
    // Add 'Go' button.
    var run_tool_row = $("<div>").addClass("slider-row").appendTo(this.parent_div);
    var run_tool_button = $("<input type='submit'>").attr("value", "Run").appendTo(run_tool_row);
    var tool = this;
    run_tool_button.click( function() {
        tool.run();
    });
};
extend(Tool.prototype, {
    /** 
     * Returns dictionary of parameter name-values.
     */
    get_param_values_dict: function() {
        var param_dict = {};
        this.parent_div.find(":input").each(function() {
            var name = $(this).attr("name"), value = $(this).val();
            param_dict[name] = JSON.stringify(value);
        });
        return param_dict;
    },
    /**
     * Returns array of parameter values.
     */
    get_param_values: function() {
        var param_values = [];
        var param_dict = {};
        this.parent_div.find(":input").each(function() {
            // Only include inputs with names; this excludes Run button.
            var name = $(this).attr("name"), value = $(this).val();
            if (name) {
                param_values[param_values.length] = value;
            }
        });
        return param_values;
    },
    /**
     * Run tool. This creates a new child track, runs tool, and places tool's output in the new track.
     */
    run: function() {
        // Put together params for running tool.
        var url_params = { 
            dataset_id: this.track.original_dataset_id,
            chrom: this.track.view.chrom,
            low: this.track.view.low,
            high: this.track.view.high,
            tool_id: this.name
        };
        $.extend(url_params, this.get_param_values_dict());
        
        //
        // Create track for tool's output immediately to provide user feedback.
        //
        var 
            current_track = this.track,
            // Set name of track to include tool name, parameters, and region used.
            track_name = url_params.tool_id +
                         current_track.tool_region_and_parameters_str(url_params.chrom, url_params.low, url_params.high),
            new_track;
            
        // TODO: add support for other kinds of tool data tracks.
        if (current_track.track_type === 'FeatureTrack') {
            new_track = new ToolDataFeatureTrack(track_name, view, current_track.hda_ldda, undefined, {}, {}, current_track);    
        }
              
        this.track.add_track(new_track);
        new_track.content_div.text("Starting job.");
        
        // Run tool.
        var json_run_tool = function() {
            $.getJSON(run_tool_url, url_params, function(track_data) {
                if (track_data === "no converter") {
                    // No converter available for input datasets, so cannot run tool.
                    new_track.container_div.addClass("error");
                    new_track.content_div.text(DATA_NOCONVERTER);
                }
                else if (track_data.error) {
                    // General error.
                    new_track.container_div.addClass("error");
                    new_track.content_div.text(DATA_CANNOT_RUN_TOOL + track_data.message);
                }
                else if (track_data === "pending") {
                    // Converting/indexing input datasets; show message and try again.
                    new_track.container_div.addClass("pending");
                    new_track.content_div.text("Converting input data so that it can be easily reused.");
                    setTimeout(json_run_tool, 2000);
                }
                else {
                    // Job submitted and running.
                    new_track.dataset_id = track_data.dataset_id;
                    new_track.content_div.text("Running job.");
                    new_track.init();
                }
            });
        };
        json_run_tool();
    }
});

/**
 * Tool parameters.
 */
var ToolParameter = function(name, label, html) {
    this.name = name;
    this.label = label;
    this.html = html;
};

var NumberParameter = function(name, label, html, min, max) {
    ToolParameter.call(this, name, label, html)
    this.min = min;
    this.max = max;
};

/**
 * Filters that enable users to show/hide data points dynamically.
 */
var Filter = function(name, index, value) {
    this.name = name;
    this.index = index;
    this.value = value;
};
/**
 * Number filters have a min, max as well as a low, high; low and high are used 
 */
var NumberFilter = function(name, index) {
    this.name = name;
    // Index into payload to filter.
    this.index = index;
    // Filter low/high. These values are used to filter elements.
    this.low = -Number.MAX_VALUE;
    this.high = Number.MAX_VALUE;
    // Slide min/max. These values are used to set/update slider.
    this.min = Number.MAX_VALUE;
    this.max = -Number.MAX_VALUE;
    // UI Slider element and label that is associated with filter.
    this.slider = null;
    this.slider_label = null;
};
extend(NumberFilter.prototype, {
    /** 
     * Returns true if filter can be applied to element.
     */
    applies_to: function(element) {
        if (element.length > this.index) {
            return true;
        }
        return false;
    },
    /**
     * Returns true iff element is in [low, high]; range is inclusive.
     */
    keep: function(element) {
        if ( !this.applies_to( element ) ) {
            // No element to filter on.
            return true;
        }
        return (element[this.index] >= this.low && element[this.index] <= this.high);
    },
    /**
     * Update filter's min and max values based on element's values.
     */
    update_attrs: function(element) {
        var updated = false;
        if (!this.applies_to(element) ) {
            return updated;
        }
        
        // Update filter's min, max based on element values.
        if (element[this.index] < this.min) {
            this.min = Math.floor(element[this.index]);
            updated = true;
        }
        if (element[this.index] > this.max) {
            this.max = Math.ceil(element[this.index]);
            updated = true;
        }
        return updated;
    },
    /**
     * Update filter's slider.
     */
    update_ui_elt: function () {
        var 
            slider_min = this.slider.slider("option", "min"),
            slider_max = this.slider.slider("option", "max");
        if (this.min < slider_min || this.max > slider_max) {
            // Update slider min, max, step.
            this.slider.slider("option", "min", this.min);
            this.slider.slider("option", "max", this.max);
            this.slider.slider("option", "step", get_slider_step(this.min, this.max));
            // Refresh slider:
            // TODO: do we want to keep current values or reset to min/max?
            // Currently we reset values:
            this.slider.slider("option", "values", [this.min, this.max]);
            // To use the current values.
            //var values = this.slider.slider( "option", "values" );
            //this.slider.slider( "option", "values", values );
        }
    }
});

/** 
 * Parse filters dict and return filters.
 */
var get_filters_from_dict = function(filters_dict) {
    var filters = [];
    for (var i = 0; i < filters_dict.length; i++) {
        var filter_dict = filters_dict[i];
        var name = filter_dict.name, type = filter_dict.type, index = filter_dict.index;
        if (type === 'int' || type === 'float') {
            filters[i] = new NumberFilter(name, index);
        } else {
            filters[i] = new Filter(name, index, type);
        }
    }
    return filters;
};

/**
 * Container for track configuration data.
 */
var TrackConfig = function( options ) {
    this.track = options.track;
    this.params = options.params;
    this.values = {}
    if ( options.saved_values ) {
        this.restore_values( options.saved_values );
    }
    this.onchange = options.onchange
}
extend( TrackConfig.prototype, {
    restore_values: function( values ) {
        var track_config = this;
        $.each( this.params, function( index, param ) {
            if ( values[ param.key ] !== undefined ) {
                track_config.values[ param.key ] = values[ param.key ];
            } else {
                track_config.values[ param.key ] = param.default_value;
            }
        }); 
    },
    build_form: function() {
        var track_config = this;
        var container = $("<div />");
        $.each( this.params, function( index, param ) {
            if ( ! param.hidden ) {
                var id = 'param_' + index;
                var row = $("<div class='form-row' />").appendTo( container );
                row.append( $('<label />').attr("for", id ).text( param.label + ":" ) );
                if ( param.type === 'bool' ) {
                    row.append( $('<input type="checkbox" />').attr("id", id ).attr("name", id ).attr( 'checked', track_config.values[ param.key ] ) );
                } else if ( param.type === 'color' ) {
                    var value = track_config.values[ param.key ];
                    var input = $('<input />').attr("id", id ).attr("name", id ).val( value );
                    // Color picker in tool tip style float
                    var tip = $( "<div class='tipsy tipsy-north' style='position: absolute;' />" ).hide();
                    // Inner div for padding purposes
                    var tip_inner = $("<div style='background-color: black; padding: 10px;'></div>").appendTo(tip);
                    var farb_container = $("<div/>")
                            .appendTo(tip_inner)
                            .farbtastic( { width: 100, height: 100, callback: input, color: value });
                            
                    // Outer div container input and tip for hover to work
                    $("<div />").append( input ).append( tip ).appendTo( row ).bind( "click", function ( e ) { 
                        tip.css( { 
                            left: $(this).position().left + ( $(input).width() / 2 ) - 60,
                            top: $(this).position().top + $(this.height) 
                            } ).show();
                        $(document).bind( "click.color-picker", function() {
                            tip.hide();
                            $(document).unbind( "click.color-picker" );
                        }); 
                        e.stopPropagation();
                    });
                } else {
                    row.append( $('<input />').attr("id", id ).attr("name", id ).val( track_config.values[ param.key ] ) ); 
                }
            }
        });
        return container;
    },
    update_from_form: function( container ) {
        var track_config = this;
        var changed = false;
        $.each( this.params, function( index, param ) {
            if ( ! param.hidden ) {
                // Parse value from form element
                var id = 'param_' + index;
                var value = container.find( '#' + id ).val();
                if ( param.type === 'float' ) {
                    value = parseFloat( value );
                } else if ( param.type === 'int' ) {
                    value = parseInt( value );
                } else if ( param.type === 'bool' ) {
                    value = container.find( '#' + id ).is( ':checked' );
                } 
                // Save value only if changed
                if ( value !== track_config.values[ param.key ] ) {
                    track_config.values[ param.key ] = value;
                    changed = true;
                }
            }
        });
        if ( changed ) {
            this.onchange();
        }
    }
});

/**
 * Tiles for TiledTracks.
 */
var Tile = function(track, canvas, histo_max) {
    this.track = track;
    this.canvas = canvas;
    this.histo_max = histo_max;
};

/**
 * Tracks are objects can be added to the View. 
 * 
 * Track object hierarchy:
 * Track
 * -> LabelTrack 
 * -> TiledTrack
 * ----> LineTrack
 * ----> ReferenceTrack
 * ----> FeatureTrack
 * -------> ReadTrack
 * -------> ToolDataFeatureTrack
 */
var Track = function(name, view, parent_element, data_url, data_query_wait) {
    //
    // Attribute init.
    //
    this.name = name;
    this.view = view;    
    this.parent_element = parent_element;
    this.data_url = (data_url ? data_url : default_data_url);
    this.data_url_extra_params = {}
    this.data_query_wait = (data_query_wait ? data_query_wait : DEFAULT_DATA_QUERY_WAIT);
    this.dataset_check_url = converted_datasets_state_url;
    
    //
    // Create HTML element structure for track.
    //
    this.container_div = $("<div />").addClass('track').css("position", "relative");
    if (!this.hidden) {
        this.header_div = $("<div class='track-header' />").appendTo(this.container_div);
        if (this.view.editor) { this.drag_div = $("<div class='draghandle' />").appendTo(this.header_div); }
        this.name_div = $("<div class='menubutton popup' />").appendTo(this.header_div);
        this.name_div.text(this.name);
        this.name_div.attr( "id", this.name.replace(/\s+/g,'-').replace(/[^a-zA-Z0-9\-]/g,'').toLowerCase() );
    }
    
    //
    // Create content div, which is where track is displayed.
    //
    this.content_div = $("<div class='track-content'>").appendTo(this.container_div);
    this.parent_element.append(this.container_div);
};
extend(Track.prototype, {
    /**
     * Initialize and draw the track.
     */
    init: function() {
        var track = this;
        track.enabled = false;
        track.tile_cache.clear();    
        track.data_cache.clear();
        track.initial_canvas = undefined;
        track.content_div.css("height", "auto");
        /*
        if (!track.content_div.text()) {
            track.content_div.text(DATA_LOADING);
        }
        */
        track.container_div.removeClass("nodata error pending");
        
        //
        // Tracks with no dataset id are handled differently.
        //
        if (!track.dataset_id) {
            return;
        }
       
        // Get dataset state; if state is fine, enable and draw track. Otherwise, show message 
        // about track status.
        $.getJSON(converted_datasets_state_url, { hda_ldda: track.hda_ldda, dataset_id: track.dataset_id, chrom: track.view.chrom}, 
                 function (result) {
            if (!result || result === "error" || result.kind === "error") {
                track.container_div.addClass("error");
                track.content_div.text(DATA_ERROR);
                if (result.message) {
                    var track_id = track.view.tracks.indexOf(track);
                    var error_link = $(" <a href='javascript:void(0);'></a>").text("View error").bind("click", function() {
                        show_modal( "Trackster Error", "<pre>" + result.message + "</pre>", { "Close" : hide_modal } );
                    });
                    track.content_div.append(error_link);
                }
            } else if (result === "no converter") {
                track.container_div.addClass("error");
                track.content_div.text(DATA_NOCONVERTER);
            } else if (result === "no data" || (result.data !== undefined && (result.data === null || result.data.length === 0))) {
                track.container_div.addClass("nodata");
                track.content_div.text(DATA_NONE);
            } else if (result === "pending") {
                track.container_div.addClass("pending");
                track.content_div.text(DATA_PENDING);
                setTimeout(function() { track.init(); }, track.data_query_wait);
            } else if (result['status'] === "data") {
                if (result['valid_chroms']) {
                    track.valid_chroms = result['valid_chroms'];
                    track.make_name_popup_menu();
                }
                track.content_div.text(DATA_OK);
                if (track.view.chrom) {
                    track.content_div.text("");
                    track.content_div.css( "height", track.height_px + "px" );
                    track.enabled = true;
                    // predraw_init may be asynchronous, wait for it and then draw
                    $.when( track.predraw_init() ).done( function() { track.draw() } );
                }
            }
        });
    },
    /**
     * Additional initialization required before drawing track for the first time.
     */
    predraw_init: function() {},
    // Provide support for updating and reverting track name. Currently, it's only possible to revert once.
    update_name: function(new_name) {
        this.old_name = this.name;
        this.name = new_name;
        this.name_div.text(this.name);
    },
    revert_name: function() {
        this.name = this.old_name;
        this.name_div.text(this.name);
    }
});

var TiledTrack = function(filters, tool_dict, parent_track) {
    var track = this,
        view = track.view;
    
    // Attribute init.
    this.filters = (filters !== undefined ? get_filters_from_dict( filters ) : []);
    // filters_available is determined by data, filters_visible is set by user.
    this.filters_available = false;
    this.filters_visible = false;
    this.tool = (tool_dict !== undefined && obj_length(tool_dict) > 0 ? new Tool(this, tool_dict) : undefined);
    
    //
    // TODO: Right now there is only the notion of a parent track and multiple child tracks. However, 
    // a more general notion of a 'track group' is probably needed and can be easily created using
    // the code already in place for parent/child tracks. The view would then manage track groups, and
    // each track group could be managed on its own.
    //
    this.parent_track = parent_track;
    this.child_tracks = [];
    
    if (track.hidden) { return; }
    
    //
    // Init HTML elements for tool, filters.
    //
    
    // Function that supports inline text editing of slider values for tools, filters.
    // Enable users to edit parameter's value via a text box.
    var edit_slider_values = function(container, span, slider) {
        container.click(function() {
            var cur_value = span.text();
                max = parseFloat(slider.slider("option", "max")),
                input_size = (max <= 1 ? 4 : max <= 1000000 ? max.toString().length : 6),
                multi_value = false;
            // Increase input size if there are two values.
            if (slider.slider("option", "values")) {
                input_size = 2*input_size + 1;
                multi_value = true;
            }
            span.text("");
            // Temporary input for changing value.
            $("<input type='text'/>").attr("size", input_size).attr("maxlength", input_size)
                                     .attr("value", cur_value).appendTo(span).focus().select()
                                     .click(function(e) {
                // Don't want click to propogate up to values_span and restart everything.
                e.stopPropagation();
            }).blur(function() {
                $(this).remove();
                span.text(cur_value);
            }).keyup(function(e) {
                if (e.keyCode === 27) {
                    // Escape key.
                    $(this).trigger("blur");
                } else if (e.keyCode === 13) {
                    //
                    // Enter/return key initiates callback. If new value(s) are in slider range, 
                    // change value (which calls slider's change() function).
                    //
                    var slider_min = slider.slider("option", "min"),
                        slider_max = slider.slider("option", "max"),
                        invalid = function(a_val) {
                            return (isNaN(a_val) || a_val > slider_max || a_val < slider_min);
                        },
                        new_value = $(this).val();
                    if (!multi_value) {
                        new_value = parseFloat(new_value);
                        if (invalid(new_value)) {
                            alert("Parameter value must be in the range [" + slider_min + "-" + slider_max + "]");
                            return $(this);
                        }
                    }
                    else { // Multi value.
                        new_value = new_value.split("-");
                        new_value = [parseFloat(new_value[0]), parseFloat(new_value[1])];
                        if (invalid(new_value[0]) || invalid(new_value[1])) {
                            alert("Parameter value must be in the range [" + slider_min + "-" + slider_max + "]");
                            return $(this);
                        }
                    }
                    slider.slider((multi_value ? "values" : "value"), new_value);
                }
            });
        });
    };
    
    
    // If track has parent:
    //   -replace drag handle with child-track icon button; (TODO: eventually, we'll want to be able 
    //    to make a set of child tracks dragable.)
    //   -remove tool b/c child tracks cannot have tools.
    if (this.parent_track) {
        this.header_div.find(".draghandle").removeClass('draghandle').addClass('child-track-icon').addClass('icon-button');
        this.parent_element.addClass("child-track");
        this.tool = undefined;
    }
    
    // Create filtering div.
    this.filters_div = $("<div/>").addClass("filters").hide();
    this.header_div.after(this.filters_div);
    // Disable dragging, double clicking on div so that actions on slider do not impact viz.
    this.filters_div.bind("drag", function(e) {
        e.stopPropagation();
    }).bind("click", function(e) {
        e.stopPropagation();
    }).bind("dblclick", function(e) {
        e.stopPropagation();
    });
    $.each(this.filters, function(index, filter) {
        var filter_div = $("<div/>").addClass("slider-row").appendTo(track.filters_div);
        
        // Set up filter label (name, values).
        var filter_label = $("<div/>").addClass("slider-label").appendTo(filter_div)
        var name_span = $("<span/>").addClass("slider-name").text(filter.name + "  ").appendTo(filter_label);
        var values_span = $("<span/>");
        var values_span_container = $("<span/>").addClass("slider-value").appendTo(filter_label).append("[").append(values_span).append("]");
        
        // Set up slider for filter.
        var slider_div = $("<div/>").addClass("slider").appendTo(filter_div);
        filter.control_element = $("<div/>").attr("id", filter.name + "-filter-control").appendTo(slider_div);
        var prev_values = [0,0];
        filter.control_element.slider({
            range: true,
            min: Number.MAX_VALUE,
            max: -Number.MIN_VALUE,
            values: [0, 0],
            slide: function(event, ui) {
                //
                // Always update UI values, but set timeout for doing more--especially drawing--
                // so that viz is more responsive.
                //
                prev_values = ui.values;
                values_span.text(ui.values[0] + "-" + ui.values[1]);
                setTimeout(function() {
                    if (ui.values[0] == prev_values[0] && ui.values[1] == prev_values[1]) {
                        var values = ui.values;
                        // Set new values in UI.
                        values_span.text(values[0] + "-" + values[1]);
                        // Set new values in filter.
                        filter.low = values[0];
                        filter.high = values[1];                    
                        // Redraw track.
                        track.draw(true, true);
                    }
                }, 50); 
            },
            change: function(event, ui) {
                filter.control_element.slider("option", "slide").call(filter.control_element, event, ui);
            }
        });
        filter.slider = filter.control_element;
        filter.slider_label = values_span;
        
        // Enable users to edit slider values via text box.
        edit_slider_values(values_span_container, values_span, filter.control_element);
        
        // Add to clear floating layout.
        $("<div style='clear: both;'/>").appendTo(filter_div);
    });
    
    //
    // Create dynamic tool div.
    //
    if (this.tool) {  
        this.dynamic_tool_div = this.tool.parent_div;
        this.header_div.after(this.dynamic_tool_div);
    }
    
    //
    // Child tracks container setup.
    //
    track.child_tracks_container = $("<div/>").addClass("child-tracks-container").hide();
    track.container_div.append(track.child_tracks_container);
    
    //
    // Create modes control.
    //
    if (track.display_modes !== undefined) {
        if (track.mode_div === undefined) {
            track.mode_div = $("<div class='right-float menubutton popup' />").appendTo(track.header_div);
            var init_mode = (track.track_config && track.track_config.values['mode'] ? 
                             track.track_config.values['mode'] : track.display_modes[0]);
            track.mode = init_mode;
            track.mode_div.text(init_mode);
        
            var change_mode = function(name) {
                track.mode_div.text(name);
                // TODO: is it necessary to store the mode in two places (.mode and track_config)?
                track.mode = name;
                track.track_config.values['mode'] = name;
                track.tile_cache.clear();
                track.draw();
            };
            var mode_mapping = {};
            for (var i = 0, len = track.display_modes.length; i < len; i++) {
                var mode = track.display_modes[i];
                mode_mapping[mode] = function(mode) {
                    return function() { change_mode(mode); };
                }(mode);
            }
            make_popupmenu(track.mode_div, mode_mapping);
        } else {
            track.mode_div.hide();
        }
    }
    
    this.make_name_popup_menu();
    
    /*
    if (track.overview_check_div === undefined) {
        track.overview_check_div = $("<div class='right-float' />").css("margin-top", "-3px").appendTo(track.header_div);
        track.overview_check = $("<input type='checkbox' class='overview_check' />").appendTo(track.overview_check_div);
        track.overview_check.bind("click", function() {
            var curr = this;
            view.overview_viewport.find("canvas").remove();
            track.set_overview();
            $(".overview_check").each(function() {
                if (this !== curr) {
                    $(this).attr("checked", false);
                }
            });
        });
        track.overview_check_div.append( $("<label />").text("Overview") );
    }
    */
};
extend(TiledTrack.prototype, Track.prototype, {
    /**
     * Make popup menu for track name.
     */
    make_name_popup_menu: function() {
        var track = this;
        
        var track_dropdown = {};
        
        //
        // Edit config option.
        //
        track_dropdown["Edit configuration"] = function() {
            var cancel_fn = function() { hide_modal(); $(window).unbind("keypress.check_enter_esc"); },
                ok_fn = function() { 
                    track.track_config.update_from_form( $(".dialog-box") );
                    hide_modal(); 
                    $(window).unbind("keypress.check_enter_esc"); 
                },
                check_enter_esc = function(e) {
                    if ((e.keyCode || e.which) === 27) { // Escape key
                        cancel_fn();
                    } else if ((e.keyCode || e.which) === 13) { // Enter key
                        ok_fn();
                    }
                };

            $(window).bind("keypress.check_enter_esc", check_enter_esc);        
            show_modal("Configure Track", track.track_config.build_form(), {
                "Cancel": cancel_fn,
                "OK": ok_fn
            });
        };
        /*
        track_dropdown["Set as overview"] = function() {
            view.overview_viewport.find("canvas").remove();
            track.is_overview = true;
            track.set_overview();
            for (var track_id in view.tracks) {
                if (view.tracks[track_id] !== track) {
                    view.tracks[track_id].is_overview = false;
                }
            }
        };*/

        //
        // Show/hide filters option.
        //
        if (track.filters_available > 0) {
            // Show/hide filters menu item.
            var text = (track.filters_div.is(":visible") ? "Hide filters" : "Show filters");
            track_dropdown[text] = function() {
                // Toggle filtering div and remake menu.
                track.filters_visible = (track.filters_div.is(":visible"));
                track.filters_div.toggle();
                track.make_name_popup_menu();
            };
        }
        
        //
        // Show/hide tool option.
        //
        if (track.tool) {
            // Show/hide dynamic tool menu item.
            var text = (track.dynamic_tool_div.is(":visible") ? "Hide tool" : "Show tool");
            track_dropdown[text] = function() {
                // Set track name, toggle tool div, and remake menu.
                if (!track.dynamic_tool_div.is(":visible")) {
                    track.update_name(track.name + track.tool_region_and_parameters_str());
                }
                else {
                    menu_option_text = "Show dynamic tool";
                    track.revert_name();
                }
                track.dynamic_tool_div.toggle();
                track.make_name_popup_menu();
            };
        }
                
        //
        // List chrom/contigs with data option.
        //
        if (track.valid_chroms) {
            track_dropdown["List chrom/contigs with data"] = function() {
                show_modal("Chrom/contigs with data", "<p>" + track.valid_chroms.join("<br/>") + "</p>", { "Close": function() { hide_modal(); } });
            };
        }
        
        //
        // Remove option.
        //

        // Need to either remove track from view or from parent.
        var parent_obj = view;
        var no_tracks_fn = function() { $("#no-tracks").show(); };
        if (this.parent_track) {
            // Track is child track.
            parent_obj = this.parent_track;
            no_tracks_fn = function() {};
        }
        track_dropdown.Remove = function() {
            parent_obj.remove_track(track);
            if (parent_obj.num_tracks === 0) {
                no_tracks_fn();
            }
        };
        
        make_popupmenu(track.name_div, track_dropdown);
    },
    /**
     * Draw track. It is possible to force a redraw rather than use cached tiles and/or clear old 
     * tiles after drawing new tiles.
     */
    draw: function(force, clear_after) {
        var low = this.view.low,
            high = this.view.high,
            range = high - low,
            width = this.view.container.width(),
            // w_scale units are pixels per base.
            w_scale = width / range,
            resolution = this.view.resolution,
            parent_element = $("<div style='position: relative;'></div>");
        
        if (!clear_after) { this.content_div.children().remove(); }
        this.content_div.append( parent_element );
        this.max_height = 0;
        // Index of first tile that overlaps visible region
        var tile_index = Math.floor( low / resolution / DENSITY );
        // A set of setTimeout() ids used when drawing tiles. Each ID indicates
        // a tile has been requested to be drawn or is being drawn.
        var draw_tile_dict = {};
        while ( ( tile_index * DENSITY * resolution ) < high ) {
            // Check in cache
            var key = width + '_' + w_scale + '_' + tile_index;
            var cached = this.tile_cache.get(key);
            var tile_low = tile_index * DENSITY * this.view.resolution;
            var tile_high = tile_low + DENSITY * this.view.resolution;
            // console.log(cached, this.tile_cache);
            if ( !force && cached ) {
                this.show_tile(cached, parent_element, tile_low, w_scale);
            } else {
                this.delayed_draw(force, key, tile_low, tile_high, tile_index, 
                                    resolution, parent_element, w_scale, draw_tile_dict);
            }
            tile_index += 1;
        }
                
        //
        // Post-draw actions:
        //
        var track = this;
        var intervalId = setInterval(function() {
            if (obj_length(draw_tile_dict) === 0) {
                // All tiles have been drawn.
                clearInterval(intervalId);
                
                // Clear tiles?
                if (clear_after) {
                    // Clear out track content in order to show the most recent content.
                    // Most recent content is the div with children (tiles) most recently appended to track.
                    // However, do not delete recently-appended empty content as calls to draw() may still be active
                    // and using these divs.
                    var track_content = track.content_div.children();
                    var remove = false;
                    for (var i = track_content.length-1, len = 0; i >= len; i--) {
                        var child = $(track_content[i]);
                        if (remove) {
                            child.remove();
                        }
                        else if (child.children().length !== 0) {
                            // Found most recent content with tiles: set remove to start removing old elements.
                            remove = true;
                        }
                    }
                }
                
                //
                // Update filter attributes, UI.
                //

                // Update filtering UI.
                for (var f = 0; f < track.filters.length; f++) {
                    track.filters[f].update_ui_elt();
                }

                // Determine if filters are available; this is based on the example feature.
                var filters_available = false;
                if (track.example_feature) {
                    for (var f = 0; f < track.filters.length; f++) {
                        if (track.filters[f].applies_to(track.example_feature)) {
                            filters_available = true;
                            break;
                        }
                    }
                }

                // If filter availability changed, hide filter div if necessary and update menu.
                if (track.filters_available !== filters_available) {
                    track.filters_available = filters_available;
                    if (!track.filters_available) {
                        track.filters_div.hide();
                    }
                    track.make_name_popup_menu();
                }
            }
        }, 50);
             
        //
        // Draw child tracks.
        //
        for (var i = 0; i < this.child_tracks.length; i++) {
            this.child_tracks[i].draw(force, clear_after);
        }
    }, 
    delayed_draw: function(force, key, tile_low, tile_high, tile_index, resolution, parent_element, w_scale, draw_tile_dict) {
        var track = this;
        // Put a 50ms delay on drawing so that if the user scrolls fast, we don't load extra data
        var draw_and_show_tile = function(id, result, resolution, tile_index, parent_element, w_scale, seq_data) {
            // DEBUG: this is still called too many times when moving slowly,
            // console.log( "draw_and_show_tile", resolution, tile_index, w_scale );
            returned_tile = track.draw_tile(result, resolution, tile_index, parent_element, w_scale, seq_data)
            
            // Wrap element in div for background
            var wrapper_element = $("<div class='track-tile'>").prepend(returned_tile);
            tile_element = wrapper_element;
            
            track.tile_cache.set(key, tile_element);
            track.show_tile(tile_element, parent_element, tile_low, w_scale);
            
            // TODO: this should go in a post-draw function.
            // Store initial canvas in case we need to use it for overview
            /* This is completely broken, just saves the first tile it sees
               regardless of if it should be the overview
            if (!track.initial_canvas && !window.G_vmlCanvasManager) {
                track.initial_canvas = $(tile_element).clone();
                var src_ctx = tile_element.get(0).getContext("2d");
                var tgt_ctx = track.initial_canvas.get(0).getContext("2d");
                var data = src_ctx.getImageData(0, 0, src_ctx.canvas.width, src_ctx.canvas.height);
                tgt_ctx.putImageData(data, 0, 0);
                track.set_overview();
            }
            */
            
            delete draw_tile_dict[id];
        };
        var id = setTimeout(function() {
            if (tile_low <= track.view.high && tile_high >= track.view.low) {
                // Show/draw tile: check cache for tile; if tile not in cache, draw it.
                var tile_element = (force ? undefined : track.tile_cache.get(key));
                if (tile_element) { 
                    track.show_tile(tile_element, parent_element, tile_low, w_scale);
                    delete draw_tile_dict[id];
                }
                else {
                    //
                    // Really draw tile: get data, seq data if available, and draw tile.
                    //
                    $.when(track.data_cache.get_data(view.chrom, tile_low, tile_high, track.mode, 
                                                     resolution, track.data_url_extra_params)).then(function(tile_data) {
                        // If sequence data needed, get that and draw. Otherwise draw.
                        if (view.reference_track && w_scale > view.canvas_manager.char_width_px) {
                            $.when(view.reference_track.data_cache.get_data(view.chrom, tile_low, tile_high, 
                                                                            track.mode, resolution, 
                                                                            view.reference_track.data_url_extra_params)).then(function(seq_data) {
                                draw_and_show_tile(id, tile_data, resolution, tile_index, parent_element, w_scale, seq_data);
                            });
                        }
                        else {
                            draw_and_show_tile(id, tile_data, resolution, tile_index, parent_element, w_scale);
                        }
                    });              
                }
            }
        }, 50);
        draw_tile_dict[id] = true;
    }, 
    /**
     * Show track tile and perform associated actions.
     */
    show_tile: function(tile_element, parent_element, tile_low, w_scale) {
        // Readability.
        var track = this;
        
        //
        // Show tile element.
        //
      
        // Position tile element, recalculate left position at display time
        var range = this.view.high - this.view.low,
            left = (tile_low - this.view.low) * w_scale;
        if (this.left_offset) {
            left -= this.left_offset;
        }
        tile_element.css({ position: 'absolute', top: 0, left: left, height: '' });

        // Setup and show tile element.
        parent_element.append(tile_element);
        track.max_height = Math.max(track.max_height, tile_element.height());
        track.content_div.css("height", track.max_height + "px");
        parent_element.children().css("height", track.max_height + "px");        
    }, 
    // Set track as the overview track in the visualization.
    set_overview: function() {
        var view = this.view;
        
        if (this.initial_canvas && this.is_overview) {
            view.overview_close.show();
            view.overview_viewport.append(this.initial_canvas);
            view.overview_highlight.show().height(this.initial_canvas.height());
            view.overview_viewport.height(this.initial_canvas.height() + view.overview_box.height());
        }
        $(window).trigger("resize");
    },
    /**
     * Utility function that creates a label string describing the region and parameters of a track's tool.
     */
    tool_region_and_parameters_str: function(chrom, low, high) {
        // Region is chrom:low-high or 'all.'
        var 
            track = this,
            region = (chrom !== undefined && low !== undefined && high !== undefined ?
                      chrom + ":" + low + "-" + high : "all");
        return " - region=[" + region + "], parameters=[" + track.tool.get_param_values().join(", ") + "]";
    },
    /**
     * Add a child track to this track.
     */
    add_track: function(child_track) {
        child_track.track_id = this.track_id + "_" + this.child_tracks.length;
        child_track.container_div.attr('id', 'track_' + child_track.track_id);
        this.child_tracks_container.append(child_track.container_div);
        sortable( child_track.container_div, '.child-track-icon' );
        if (!$(this.child_tracks_container).is(":visible")) {
            this.child_tracks_container.show();
        }
        this.child_tracks.push(child_track);
        this.view.has_changes = true;
    },
    /**
     * Remove a child track from this track.
     */
    remove_track: function(child_track) {
        child_track.container_div.fadeOut('slow', function() { $(this).remove(); });
    }
});

var LabelTrack = function (view, parent_element) {
    this.track_type = "LabelTrack";
    this.hidden = true;
    Track.call( this, null, view, parent_element );
    this.container_div.addClass( "label-track" );
};
extend( LabelTrack.prototype, Track.prototype, {
    draw: function() {
        var view = this.view,
            range = view.high - view.low,
            tickDistance = Math.floor( Math.pow( 10, Math.floor( Math.log( range ) / Math.log( 10 ) ) ) ),
            position = Math.floor( view.low / tickDistance ) * tickDistance,
            width = this.view.container.width(),
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
    this.hidden = true;
    Track.call(this, null, view, view.top_labeltrack);
    TiledTrack.call(this);
    
    view.reference_track = this;
    this.left_offset = 200;
    this.height_px = 12;
    this.container_div.addClass( "reference-track" );
    this.content_div.css("background", "none");
    this.content_div.css("min-height", "0px");
    this.content_div.css("border", "none");
    this.data_url = reference_url;
    this.data_url_extra_params = {dbkey: view.dbkey};
    this.data_cache = new DataManager(CACHED_DATA, this, false);
    this.tile_cache = new Cache(CACHED_TILES_LINE);
};
extend(ReferenceTrack.prototype, TiledTrack.prototype, {
    /**
     * Draw ReferenceTrack tile.
     */
    draw_tile: function(seq, resolution, tile_index, parent_element, w_scale) {
        var track = this,
            tile_length = DENSITY * resolution;
        
        if (w_scale > this.view.canvas_manager.char_width_px) {
            if (seq === null) {
                track.content_div.css("height", "0px");
                return;
            }
            var canvas = this.view.canvas_manager.new_canvas();
            var ctx = canvas.getContext("2d");
            canvas.width = Math.ceil( tile_length * w_scale + track.left_offset);
            canvas.height = track.height_px;
            ctx.font = ctx.canvas.manager.default_font;
            ctx.textAlign = "center";
            for (var c = 0, str_len = seq.length; c < str_len; c++) {
                var c_start = Math.round(c * w_scale);
                ctx.fillText(seq[c], c_start + track.left_offset, 10);
            }
            return canvas;
        }
        this.content_div.css("height", "0px");
    }
});

var LineTrack = function (name, view, hda_ldda, dataset_id, prefs) {
    var track = this;
    this.track_type = "LineTrack";
    this.display_modes = ["Histogram", "Line", "Filled", "Intensity"];
    this.mode = "Histogram";
    Track.call( this, name, view, view.viewport_container );
    TiledTrack.call( this );
   
    this.min_height_px = 16; 
    this.max_height_px = 400; 
    this.height_px = 80;
    this.hda_ldda = hda_ldda;
    this.dataset_id = dataset_id;
    this.original_dataset_id = dataset_id;
    this.data_cache = new DataManager(CACHED_DATA, this);
    this.tile_cache = new Cache(CACHED_TILES_LINE);

    // Define track configuration
    this.track_config = new TrackConfig( {
        track: this,
        params: [
            { key: 'color', label: 'Color', type: 'color', default_value: 'black' },
            { key: 'min_value', label: 'Min Value', type: 'float', default_value: undefined },
            { key: 'max_value', label: 'Max Value', type: 'float', default_value: undefined },
            { key: 'mode', type: 'string', default_value: this.mode, hidden: true },
            { key: 'height', type: 'int', default_value: this.height_px, hidden: true }
        ], 
        saved_values: prefs,
        onchange: function() {
            track.vertical_range = track.prefs.max_value - track.prefs.min_value;
            // Update the y-axis
            $('#linetrack_' + track.track_id + '_minval').text(track.prefs.min_value);
            $('#linetrack_' + track.track_id + '_maxval').text(track.prefs.max_value);
            track.tile_cache.clear();
            track.draw();
        }
    });

    this.prefs = this.track_config.values;
    this.height_px = this.track_config.values.height;
    this.vertical_range = this.track_config.values.max_value - this.track_config.values.min_value;

    this.add_resize_handle();
};
extend(LineTrack.prototype, TiledTrack.prototype, {
    add_resize_handle: function () {
        // Add control for resizing
        // Trickery here to deal with the hovering drag handle, can probably be
        // pulled out and reused.
        var track = this;
        var in_handle = false;
        var in_drag = false;
        var drag_control = $( "<div class='track-resize'>" )
        // Control shows on hover over track, stays while dragging
        $(track.container_div).hover( function() { 
            in_handle = true;
            drag_control.show(); 
        }, function() { 
            in_handle = false;
            if ( ! in_drag ) { drag_control.hide(); }
        });
        // Update height and force redraw of current view while dragging,
        // clear cache to force redraw of other tiles.
        drag_control.hide().bind( "dragstart", function( e, d ) {
            in_drag = true;
            d.original_height = $(track.content_div).height();
        }).bind( "drag", function( e, d ) {
            var new_height = Math.min( Math.max( d.original_height + d.deltaY, track.min_height_px ), track.max_height_px );
            $(track.content_div).css( 'height', new_height );
            track.height_px = new_height;
            track.draw( true );
        }).bind( "dragend", function( e, d ) {
            track.tile_cache.clear();    
            in_drag = false;
            if ( ! in_handle ) { drag_control.hide(); }
            track.track_config.values.height = track.height_px;
        }).appendTo( track.container_div );
    },
    predraw_init: function() {
        var track = this,
            track_id = track.view.tracks.indexOf(track);
        
        track.vertical_range = undefined;
        return $.getJSON( track.data_url, {  stats: true, chrom: track.view.chrom, low: null, high: null,
                                        hda_ldda: track.hda_ldda, dataset_id: track.dataset_id }, function(result) {
            track.container_div.addClass( "line-track" );
            var data = result.data;
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
            track.container_div.find(".yaxislabel").remove();
            
            var min_label = $("<div />").addClass('yaxislabel').attr("id", 'linetrack_' + track_id + '_minval').text(round_1000(track.prefs.min_value));
            var max_label = $("<div />").addClass('yaxislabel').attr("id", 'linetrack_' + track_id + '_maxval').text(round_1000(track.prefs.max_value));
            
            max_label.css({ position: "absolute", top: "24px", left: "10px" });
            max_label.prependTo(track.container_div);
    
            min_label.css({ position: "absolute", bottom: "2px", left: "10px" });
            min_label.prependTo(track.container_div);
        });
    },
    /**
     * Draw LineTrack tile.
     */
    draw_tile: function(result, resolution, tile_index, parent_element, w_scale) {
        if (this.vertical_range === undefined) {
            return;
        }
        
        var tile_low = tile_index * DENSITY * resolution,
            tile_length = DENSITY * resolution,
            width = Math.ceil( tile_length * w_scale ),
            height = this.height_px;
        
        // Create canvas
        var canvas = this.view.canvas_manager.new_canvas();
        canvas.width = width,
        canvas.height = height;
        
        // Paint line onto full canvas
        var ctx = canvas.getContext("2d");
        var painter = new painters.LinePainter( result.data, tile_low, tile_low + tile_length,
                                                this.prefs.min_value, this.prefs.max_value, this.prefs.color, this.mode );
        painter.draw( ctx, width, height );
        
        return canvas;
    } 
});

var FeatureTrack = function (name, view, hda_ldda, dataset_id, prefs, filters, tool, parent_track) {
    //
    // Preinitialization: do things that need to be done before calling Track and TiledTrack
    // initialization code.
    //
    var track = this;
    this.track_type = "FeatureTrack";
    this.display_modes = ["Auto", "Dense", "Squish", "Pack"];
    // Define and restore track configuration.
    this.track_config = new TrackConfig( {
        track: this,
        params: [
            { key: 'block_color', label: 'Block color', type: 'color', default_value: '#444' },
            { key: 'label_color', label: 'Label color', type: 'color', default_value: 'black' },
            { key: 'show_counts', label: 'Show summary counts', type: 'bool', default_value: true },
            { key: 'mode', type: 'string', default_value: this.mode, hidden: true },
        ], 
        saved_values: prefs,
        onchange: function() {
            track.tile_cache.clear();
            track.draw();
        }
    });
    this.prefs = this.track_config.values;
    
    //
    // Initialization.
    //
    Track.call(this, name, view, view.viewport_container);
    TiledTrack.call(this, filters, tool, parent_track);
    
    this.height_px = 0;
    this.container_div.addClass( "feature-track" );
    this.hda_ldda = hda_ldda;
    this.dataset_id = dataset_id;
    this.original_dataset_id = dataset_id;
    this.zo_slots = {};
    this.show_labels_scale = 0.001;
    this.showing_details = false;
    this.summary_draw_height = 30;
    this.inc_slots = {};
    this.start_end_dct = {};
    this.tile_cache = new Cache(CACHED_TILES_FEATURE);
    this.data_cache = new DataManager(20, this);
    this.left_offset = 200;

    this.painter = painters.LinkedFeaturePainter;
};
extend(FeatureTrack.prototype, TiledTrack.prototype, {
    update_auto_mode: function( mode ) {
        if ( this.mode == "Auto" ) {
            if ( mode == "no_detail" ) {
                mode = "reduced to feature spans";
            } else if ( mode == "summary_tree" ) {
                mode = "reduced to coverage histogram";
            }
            this.mode_div.text( "Auto (" + mode + ")" );
        }
    },
    /**
     * Place features in slots for drawing (i.e. pack features).
     * this.inc_slots[level] is created in this method. this.inc_slots[level]
     * is a dictionary of slotted features; key is feature uid, value is a dictionary
     * with keys 'slot' and 'text'.
     * Returns the number of slots used to pack features.
     */
    incremental_slots: function(level, features, mode) {
        
        // Get/create incremental slots for level. If display mode changed,
        // need to create new slots.
        
        var dummy_context = this.view.canvas_manager.dummy_context,
            inc_slots = this.inc_slots[level];
        if (!inc_slots || (inc_slots.mode !== mode)) {
            inc_slots = new (slotting.FeatureSlotter)( level, mode === "Pack", MAX_FEATURE_DEPTH, function ( x ) { return dummy_context.measureText( x ) } );
            inc_slots.mode = mode;
            this.inc_slots[level] = inc_slots;
        }

        return inc_slots.slot_features( features );
    },
    /**
     * Draw FeatureTrack tile.
     */
    draw_tile: function(result, resolution, tile_index, parent_element, w_scale, ref_seq) {
        var track = this,
            tile_low = tile_index * DENSITY * resolution,
            tile_high = ( tile_index + 1 ) * DENSITY * resolution,
            tile_span = tile_high - tile_low,
            width = Math.ceil( tile_span * w_scale ),
            mode = this.mode,
            min_height = 25,
            left_offset = this.left_offset,
            slots,
            required_height;
        
        // Set display mode if Auto.
        if (mode === "Auto") {
            if (result.dataset_type === "summary_tree") {
                mode = result.dataset_type;
            } else if (result.extra_info === "no_detail") {
                mode = "no_detail";
            } else {
                // Choose b/t Squish and Pack.
                // Proxy measures for using Squish: 
                // (a) error message re: limiting number of features shown; 
                // (b) X number of features shown;
                // (c) size of view shown.
                // TODO: cannot use (a) and (b) because it requires coordinating mode across tiles;
                // fix this so that tiles are redrawn as necessary to use the same mode.
                //if ( (result.message && result.message.match(/^Only the first [\d]+/)) ||
                //     (result.data && result.data.length > 2000) ||
                var data = result.data;
                if ( (data.length && data.length < 4) ||
                     (this.view.high - this.view.low > MIN_SQUISH_VIEW_WIDTH) ) {
                    mode = "Squish";
                } else {
                    mode = "Pack";
                }
            }
            this.update_auto_mode( mode );
        }
        
        // Drawing the summary tree (feature coverage histogram)
        if ( mode === "summary_tree" ) {
            // Set height of parent_element
            required_height = this.summary_draw_height;
            parent_element.parent().css("height", Math.max(this.height_px, required_height) + "px");
            // Add label to container div showing maximum count
            // TODO: this shouldn't be done at the tile level
            this.container_div.find(".yaxislabel").remove();
            var max_label = $("<div />").addClass('yaxislabel');
            max_label.text( result.max );
            max_label.css({ position: "absolute", top: "22px", left: "10px" });
            max_label.prependTo(this.container_div);
            // Create canvas
            var canvas = this.view.canvas_manager.new_canvas();
            canvas.width = width + left_offset;
            // Extra padding at top of summary tree
            canvas.height = required_height + SUMMARY_TREE_TOP_PADDING;
            // Paint summary tree into canvas
            var painter = new painters.SummaryTreePainter( result.data, result.delta, result.max, tile_low, tile_high, this.prefs.show_counts );
            var ctx = canvas.getContext("2d");
            // Deal with left_offset by translating
            ctx.translate( left_offset, SUMMARY_TREE_TOP_PADDING );
            painter.draw( ctx, width, required_height );
            // Canvas element is returned
            return canvas;            
        }

        // Start dealing with row-by-row tracks
        
        // If working with a mode where slotting is neccesary, update the incremental slotting
        var slots, slots_required = 1;
        if ( mode === "no_detail" || mode === "Squish" || mode === "Pack" ) {
            slots_required = this.incremental_slots(w_scale, result.data, mode);
            slots = this.inc_slots[w_scale].slots;
        }

        // Filter features
        var filtered = [];
        if ( result.data ) {
            for (var i = 0, len = result.data.length; i < len; i++) {
                var feature = result.data[i];
                var hide_feature = false;
                var filter;
                for (var f = 0, flen = this.filters.length; f < flen; f++) {
                    filter = this.filters[f];
                    filter.update_attrs(feature);
                    if (!filter.keep(feature)) {
                        hide_feature = true;
                        break;
                    }
                }
                if (!hide_feature) {
                    filtered.push( feature );
                }
            }
        }
        
        // Create painter, and canvas of sufficient size to contain all features
        // HACK: ref_seq will only be defined for ReadTracks, and only the ReadPainter accepts that argument
        var painter = new (this.painter)( filtered, tile_low, tile_high, this.prefs, mode, ref_seq );
        // FIXME: ERROR_PADDING is an ugly gap most of the time
        var required_height = painter.get_required_height( slots_required ) + ERROR_PADDING;
        var canvas = this.view.canvas_manager.new_canvas();
        
        canvas.width = width + left_offset;
        canvas.height = required_height;

        parent_element.parent().css("height", Math.max(this.height_px, required_height) + "px");
        // console.log(( tile_low - this.view.low ) * w_scale, tile_index, w_scale);
        var ctx = canvas.getContext("2d");
        ctx.fillStyle = this.prefs.block_color;
        ctx.font = ctx.canvas.manager.default_font;
        ctx.textAlign = "right";
        this.container_div.find(".yaxislabel").remove();
        
        // If there is a message, draw it on canvas so that it moves around with canvas, and make the border red
        // to indicate region where message is applicable
        if (result.message) {
            $(canvas).css({
                "border-top": "1px solid red"
            });

            ctx.fillStyle = "red";
            ctx.textAlign = "left";
            var old_base = ctx.textBaseline;
            ctx.textBaseline = "top";
            ctx.fillText(result.message, left_offset, 0);
            ctx.textBaseline = old_base;

            // If there's no data, return.
            if (!result.data) {
                return canvas;
            }
        }

        // Set example feature. This is needed so that track can update its UI based on feature attributes.
        this.example_feature = (result.data.length ? result.data[0] : undefined);
      
        // Draw features
        ctx.translate( left_offset, ERROR_PADDING );
        painter.draw( ctx, width, required_height, slots );
            
        return canvas;
    }
});

var VcfTrack = function(name, view, hda_ldda, dataset_id, prefs, filters) {
    FeatureTrack.call(this, name, view, hda_ldda, dataset_id, prefs, filters);
    this.track_type = "VcfTrack";
    this.painter = painters.VariantPainter;
};

extend(VcfTrack.prototype, TiledTrack.prototype, FeatureTrack.prototype);


var ReadTrack = function (name, view, hda_ldda, dataset_id, prefs, filters) {
    FeatureTrack.call(this, name, view, hda_ldda, dataset_id, prefs, filters);
    
    this.track_config = new TrackConfig( {
        track: this,
        params: [
            { key: 'block_color', label: 'Block color', type: 'color', default_value: '#444' },
            { key: 'label_color', label: 'Label color', type: 'color', default_value: 'black' },
            { key: 'show_insertions', label: 'Show insertions', type: 'bool', default_value: false },
            { key: 'show_differences', label: 'Show differences only', type: 'bool', default_value: true },
            { key: 'show_counts', label: 'Show summary counts', type: 'bool', default_value: true },
            { key: 'mode', type: 'string', default_value: this.mode, hidden: true },
        ], 
        saved_values: prefs,
        onchange: function() {
            this.track.tile_cache.clear();
            this.track.draw();
        }
    });
    this.prefs = this.track_config.values;
    
    this.track_type = "ReadTrack";
    this.painter = painters.ReadPainter;
    this.make_name_popup_menu();
};
extend(ReadTrack.prototype, TiledTrack.prototype, FeatureTrack.prototype);

/**
 * Feature track that displays data generated from tool.
 */
var ToolDataFeatureTrack = function(name, view, hda_ldda, dataset_id, prefs, filters, parent_track) {
    FeatureTrack.call(this, name, view, hda_ldda, dataset_id, prefs, filters, {}, parent_track);
    this.track_type = "ToolDataFeatureTrack";
    
    // Set up track to fetch initial data from raw data URL when the dataset--not the converted datasets--
    // is ready.
    this.data_url = raw_data_url;
    this.data_query_wait = 1000;
    this.dataset_check_url = dataset_state_url;
};

extend(ToolDataFeatureTrack.prototype, TiledTrack.prototype, FeatureTrack.prototype, {
    /**
     * For this track type, the predraw init sets up postdraw init. 
     */
    predraw_init: function() {        
        // Postdraw init: once data has been fetched, reset data url, wait time and start indexing.
        var track = this; 
        var post_init = function() {
            if (track.data_cache.size() === 0) {
                // Track still drawing initial data, so do nothing.
                setTimeout(post_init, 300);
            }
            else {
                // Track drawing done: reset dataset check, data URL, wait time and get dataset state to start
                // indexing.
                track.data_url = default_data_url;
                track.data_query_wait = DEFAULT_DATA_QUERY_WAIT;
                track.dataset_state_url = converted_datasets_state_url;
                $.getJSON(track.dataset_state_url, {dataset_id : track.dataset_id, hda_ldda: track.hda_ldda}, function(track_data) {});
            }
        };
        post_init();
    }
});

// Exports

exports.View = View;
exports.LineTrack = LineTrack;
exports.FeatureTrack = FeatureTrack;
exports.ReadTrack = ReadTrack;

// End trackster_module encapsulation
};

// ---- To be extracted ------------------------------------------------------

// ---- Feature Packing ----

// Encapsulation
var slotting_module = function(require, exports) {

// HACK: LABEL_SPACING is currently duplicated between here and painters
var LABEL_SPACING = 2,
    PACK_SPACING = 5;

/**
 * FeatureSlotter determines slots in which to draw features for vertical
 * packing.
 *
 * This implementation is incremental, any feature assigned a slot will be
 * retained for slotting future features.
 */
exports.FeatureSlotter = function ( w_scale, include_label, max_rows, measureText ) {
    this.slots = {};
    this.start_end_dct = {};
    this.w_scale = w_scale;
    this.include_label = include_label;
    this.max_rows = max_rows;
    this.measureText = measureText;
}

/**
 * Slot a set of features, `this.slots` will be updated with slots by id, and
 * the largest slot required for the passed set of features is returned
 */
extend( exports.FeatureSlotter.prototype, {
    slot_features: function( features ) {
        var w_scale = this.w_scale, inc_slots = this.slots, start_end_dct = this.start_end_dct,
            undone = [], slotted = [], highest_slot = 0, max_rows = this.max_rows;
        
        // If feature already exists in slots (from previously seen tiles), use the same slot,
        // otherwise if not seen, add to "undone" list for slot calculation.
    
        // TODO: Should calculate zoom tile index, which will improve performance
        // by only having to look at a smaller subset
        // if (this.start_end_dct[0] === undefined) { this.start_end_dct[0] = []; }
        for (var i = 0, len = features.length; i < len; i++) {
            var feature = features[i],
                feature_uid = feature[0];
            if (inc_slots[feature_uid] !== undefined) {
                highest_slot = Math.max(highest_slot, inc_slots[feature_uid]);
                slotted.push(inc_slots[feature_uid]);
            } else {
                undone.push(i);
            }
        }
                
        // Slot unslotted features.
        
        // Find the first slot such that current feature doesn't overlap any other features in that slot.
        // Returns -1 if no slot was found.
        var find_slot = function(f_start, f_end) {
            // TODO: Fix constants
            for (var slot_num = 0; slot_num <= max_rows; slot_num++) {
                var has_overlap = false,
                    slot = start_end_dct[slot_num];
                if (slot !== undefined) {
                    // Iterate through features already in slot to see if current feature will fit.
                    for (var k = 0, k_len = slot.length; k < k_len; k++) {
                        var s_e = slot[k];
                        if (f_end > s_e[0] && f_start < s_e[1]) {
                            // There is overlap
                            has_overlap = true;
                            break;
                        }
                    }
                }
                if (!has_overlap) {
                    return slot_num;
                }
            }
            return -1;
        };
        
        // Do slotting.
        for (var i = 0, len = undone.length; i < len; i++) {
            var feature = features[undone[i]],
                feature_uid = feature[0],
                feature_start = feature[1],
                feature_end = feature[2],
                feature_name = feature[3],
                // Where to start, end drawing on screen.
                f_start = Math.floor( feature_start * w_scale ),
                f_end = Math.ceil( feature_end * w_scale ),
                text_len = this.measureText(feature_name).width,
                text_align;
            
            // Update start, end drawing locations to include feature name.
            // Try to put the name on the left, if not, put on right.
            if (feature_name !== undefined && this.include_label ) {
                // Add gap for label spacing and extra pack space padding
                // TODO: Fix constants
                text_len += (LABEL_SPACING + PACK_SPACING);
                if (f_start - text_len >= 0) {
                    f_start -= text_len;
                    text_align = "left";
                } else {
                    f_end += text_len;
                    text_align = "right";
                }
            }
                        
            // Find slot.
            var slot_num = find_slot(f_start, f_end);

            /*
            if (slot_num < 0) {
                
                TODO: this is not yet working --
                console.log(feature_uid, "looking for slot with text on the right");
                // Slot not found. If text was on left, try on right and see
                // if slot can be found.
                // TODO: are there any checks we need to do to ensure that text
                // will fit on tile?
                if (text_align === "left") {
                    f_start -= text_len;
                    f_end -= text_len;
                    text_align = "right";
                    slot_num = find_slot(f_start, f_end);
                }
                if (slot_num >= 0) {
                    console.log(feature_uid, "found slot with text on the right");
                }
    
            }
            */
            // Do slotting.
            if (slot_num >= 0) {
                // Add current feature to slot.
                if (start_end_dct[slot_num] === undefined) { 
                    start_end_dct[slot_num] = [];
                }
                start_end_dct[slot_num].push([f_start, f_end]);
                inc_slots[feature_uid] = slot_num;
                highest_slot = Math.max(highest_slot, slot_num);
            }
            else {
                // TODO: remove this warning when skipped features are handled.
                // Show warning for skipped feature.
                //console.log("WARNING: not displaying feature", feature_uid, f_start, f_end);
            }
        }
        
        // Debugging: view slots data.
        /*
        for (var i = 0; i < MAX_FEATURE_DEPTH; i++) {
            var slot = start_end_dct[i];
            if (slot !== undefined) {
                console.log(i, "*************");
                for (var k = 0, k_len = slot.length; k < k_len; k++) {
                    console.log("\t", slot[k][0], slot[k][1]);
                }
            }
        }
        */
        return highest_slot + 1;
    }
});

// End slotting_module encapsulation
};

// ---- Painters ----

var painters_module = function(require, exports){

/**
 * Draw a dashed line on a canvas using filled rectangles. This function is based on:
 * http://vetruvet.blogspot.com/2010/10/drawing-dashed-lines-on-html5-canvas.html
 * However, that approach uses lines, which don't seem to render as well, so use
 * rectangles instead.
 */
var dashedLine = function(ctx, x1, y1, x2, y2, dashLen) {
    if (dashLen === undefined) { dashLen = 4; }
    var dX = x2 - x1;
    var dY = y2 - y1;
    var dashes = Math.floor(Math.sqrt(dX * dX + dY * dY) / dashLen);
    var dashX = dX / dashes;
    var dashY = dY / dashes;
    var q;
    
    for (q = 0; q < dashes; q++, x1 += dashX, y1 += dashY) {
        if (q % 2 !== 0) {
            continue;
        }
        ctx.fillRect(x1, y1, dashLen, 1);
    }
};

/**
 * Draw an isosceles triangle that points down.
 */
var drawDownwardEquilateralTriangle = function(ctx, down_vertex_x, down_vertex_y, side_len) {
    // Compute other two points of triangle.
    var 
        x1 = down_vertex_x - side_len/2,
        x2 = down_vertex_x + side_len/2,
        y = down_vertex_y - Math.sqrt( side_len*3/2 );
        
    // Draw and fill.
    ctx.beginPath();
    ctx.moveTo(x1, y);
    ctx.lineTo(x2, y);
    ctx.lineTo(down_vertex_x, down_vertex_y);
    ctx.lineTo(x1, y);

    ctx.strokeStyle = this.fillStyle;
    ctx.fill();
    ctx.stroke();
    ctx.closePath();
};

/**
 * SummaryTreePainter, a histogram showing number of intervals in a region
 */
var SummaryTreePainter = function( data, delta, max, view_start, view_end, show_counts ) {
    // Data and data properties
    this.data = data;
    this.delta = delta;
    this.max = max;
    // View
    this.view_start = view_start;
    this.view_end = view_end;
    // Drawing prefs
    this.show_counts = show_counts;
}

SummaryTreePainter.prototype.draw = function( ctx, width, height ) {
    
    var view_start = this.view_start,
        view_range = this.view_end - this.view_start,
        w_scale = width / view_range;
    
    var points = this.data, delta = this.delta, max = this.max,
        // Set base Y so that max label and data do not overlap. Base Y is where rectangle bases
        // start. However, height of each rectangle is relative to required_height; hence, the
        // max rectangle is required_height.
        base_y = height;
        delta_x_px = Math.ceil(delta * w_scale);
    
    ctx.save();
    
    for (var i = 0, len = points.length; i < len; i++) {
        
        var x = Math.floor( (points[i][0] - view_start) * w_scale );
        var y = points[i][1];
        
        if (!y) { continue; }
        var y_px = y / max * height;
        
        ctx.fillStyle = "black";
        ctx.fillRect( x, base_y - y_px, delta_x_px, y_px );
        
        // Draw number count if it can fit the number with some padding, otherwise things clump up
        var text_padding_req_x = 4;
        if (this.show_counts && (ctx.measureText(y).width + text_padding_req_x) < delta_x_px) {
            ctx.fillStyle = "#666";
            ctx.textAlign = "center";
            ctx.fillText(y, x + (delta_x_px/2), 10);
        }
    }
    
    ctx.restore();
}

var LinePainter = function( data, view_start, view_end, min_value, max_value, color, mode ) {
    // Data and data properties
    this.data = data;
    // View
    this.view_start = view_start;
    this.view_end = view_end;
    // Drawing prefs
    this.min_value = min_value;
    this.max_value = max_value;
    this.color = color;
    this.mode = mode;
    this.overflow_color = "#F66";
}

LinePainter.prototype.draw = function( ctx, width, height ) {
    var 
        in_path = false,
        min_value = this.min_value,
        max_value = this.max_value,
        vertical_range = max_value - min_value,
        height_px = height,
        view_start = this.view_start,
        view_range = this.view_end - this.view_start,
        w_scale = width / view_range,
        mode = this.mode,
        data = this.data;

    ctx.save();

    // Pixel position of 0 on the y axis
    var y_zero = Math.round( height + min_value / vertical_range * height );

    // Line at 0.0
    if ( mode !== "Intensity" ) {
        ctx.fillStyle = "#aaa";
        ctx.fillRect( 0, y_zero, width, 1 );
    }
    
    ctx.beginPath();
    ctx.fillStyle = this.color;
    var x_scaled, y, delta_x_px;
    if (data.length > 1) {
        delta_x_px = Math.ceil((data[1][0] - data[0][0]) * w_scale);
    } else {
        delta_x_px = 10;
    }
    for (var i = 0, len = data.length; i < len; i++) {
        x_scaled = Math.round((data[i][0] - view_start) * w_scale);
        y = data[i][1];
        if (y === null) {
            if (in_path && mode === "Filled") {
                ctx.lineTo(x_scaled, height_px);
            }
            in_path = false;
            continue;
        }
        if (y < min_value) {
            y = min_value;
        } else if (y > max_value) {
            y = max_value;
        }
    
        if (mode === "Histogram") {
            // y becomes the bar height in pixels, which is the negated for canvas coords
            y = Math.round( y / vertical_range * height_px );
            ctx.fillRect(x_scaled, y_zero, delta_x_px, - y );
        } else if (mode === "Intensity" ) {
            y = 255 - Math.floor( (y - min_value) / vertical_range * 255 );
            ctx.fillStyle = "rgb(" +y+ "," +y+ "," +y+ ")";
            ctx.fillRect(x_scaled, 0, delta_x_px, height_px);
        } else {
            // console.log(y, track.min_value, track.vertical_range, (y - track.min_value) / track.vertical_range * track.height_px);
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
    if (mode === "Filled") {
        if (in_path) {
            ctx.lineTo( x_scaled, y_zero );
            ctx.lineTo( 0, y_zero );
        }
        ctx.fill();
    } else {
        ctx.stroke();
    }
    
    // Draw lines at bounderies if overflowing min or max
    var overflow_min_start = -1,
        overflow_max_start = -1;
    ctx.fillStyle = this.overflow_color;
    for (var i = 0, len = data.length; i < len; i++) {
        y = data[i][1];
        x_scaled = Math.round((data[i][0] - view_start) * w_scale);
        x_minus_scaled = Math.round((data[i][0] - 1 - view_start) * w_scale);
        
        // If we are in a min/max run, check if it should be ended
        if ( overflow_max_start >= 0  && ( y === null || y < max_value ) ) {
            // Value does not exist or is in valid range, any overflow ends
            ctx.fillRect( overflow_max_start, 0, x_minus_scaled - overflow_max_start + 1, 2 );
            overflow_max_start = -1;
        } else if ( overflow_min_start >= 0 && ( y === null || y > min_value ) ) {
            // Draw bottom overflow bar
            ctx.fillRect( overflow_min_start, height - 2, x_minus_scaled - overflow_min_start + 1, 2 );
            overflow_min_start = -1;
        }
        
        // Now check if we should start a new one (this may happen on the same
        // base as above if switching between min/max)
        if ( y !== null && y > max_value && overflow_max_start < 0 ) {
            // Top overflows and we are not already in a run of overflow
            overflow_max_start = x_scaled;
        } else if ( y !== null && y < min_value && overflow_min_start < 0 ) {
            // Bottom overflows and we are not already in a run
            overflow_min_start = x_scaled;
        }
    }
    
    ctx.restore();
}

var FeaturePainter = function( data, view_start, view_end, prefs, mode ) {
    this.data = data;
    this.view_start = view_start;
    this.view_end = view_end;
    this.prefs = prefs;
    this.mode = mode;
}

extend( FeaturePainter.prototype, { 

    get_required_height: function( rows_required ) {
        // y_scale is the height per row
        var required_height = y_scale = this.get_row_height(), mode = this.mode;
        // If using a packing mode, need to multiply by the number of slots used
        if (mode === "no_detail" || mode === "Squish" || mode === "Pack") {
            required_height = rows_required * y_scale;
        }
        // Pad bottom by half a row, at least 5 px
        return required_height + Math.max( Math.round( y_scale / 2 ), 5 );
    },

    draw: function( ctx, width, height, slots ) {

        var data = this.data, view_start = this.view_start, view_end = this.view_end;

        ctx.save();

        ctx.fillStyle = this.prefs.block_color;
        ctx.textAlign = "right";

        var view_range = this.view_end - this.view_start,
            w_scale = width / view_range,
            y_scale = this.get_row_height();

        for (var i = 0, len = data.length; i < len; i++) {
            var feature = data[i],
                feature_uid = feature[0],
                feature_start = feature[1],
                feature_end = feature[2],
                // Slot valid only if features are slotted and this feature is slotted; 
                // feature may not be due to lack of space.
                slot = (slots && slots[feature_uid] !== undefined ? slots[feature_uid] : null);
                
            // Draw feature if there's overlap and mode is dense or feature is slotted (as it must be for all non-dense modes).
            if ( ( feature_start < view_end && feature_end > view_start ) && (this.mode == "Dense" || slot !== null)) {
                this.draw_element(ctx, this.mode, feature, slot, view_start, view_end, w_scale, y_scale, 
                                  width );
            }
        }

        ctx.restore();
    }
});

// Contstants specific to feature tracks moved here (HACKING, these should
// basically all be configuration options)
var DENSE_TRACK_HEIGHT = 10,
    NO_DETAIL_TRACK_HEIGHT = 3,
    SQUISH_TRACK_HEIGHT = 5,
    PACK_TRACK_HEIGHT = 10,
    NO_DETAIL_FEATURE_HEIGHT = 1,
    DENSE_FEATURE_HEIGHT = 3,
    SQUISH_FEATURE_HEIGHT = 3,
    PACK_FEATURE_HEIGHT = 9,
    LABEL_SPACING = 2,
    CONNECTOR_COLOR = "#ccc";

var LinkedFeaturePainter = function( data, view_start, view_end, prefs, mode ) {
    FeaturePainter.call( this, data, view_start, view_end, prefs, mode );
}

extend( LinkedFeaturePainter.prototype, FeaturePainter.prototype, {

    /**
     * Height of a single row, depends on mode
     */
    get_row_height: function() {
        var mode = this.mode, y_scale;
           if (mode === "Dense") {
            y_scale = DENSE_TRACK_HEIGHT;            
        }
        else if (mode === "no_detail") {
            y_scale = NO_DETAIL_TRACK_HEIGHT;
        }
        else if (mode === "Squish") {
            y_scale = SQUISH_TRACK_HEIGHT;
        }
        else { // mode === "Pack"
            y_scale = PACK_TRACK_HEIGHT;
        }
        return y_scale;
    },

    draw_element: function(ctx, mode, feature, slot, tile_low, tile_high, w_scale, y_scale, width ) {
        var 
            feature_uid = feature[0],
            feature_start = feature[1],
            // -1 b/c intervals are half-open.
            feature_end = feature[2] - 1, 
            feature_name = feature[3],
            f_start = Math.floor( Math.max(0, (feature_start - tile_low) * w_scale) ),
            f_end   = Math.ceil( Math.min(width, Math.max(0, (feature_end - tile_low) * w_scale)) ),
            y_center = (mode === "Dense" ? 0 : (0 + slot)) * y_scale,
            thickness, y_start, thick_start = null, thick_end = null,
            block_color = this.prefs.block_color,
            label_color = this.prefs.label_color;

        // Dense mode displays the same for all data.
        /*
        if (mode === "Dense") {
            ctx.fillStyle = block_color;
            ctx.fillRect(f_start, y_center, f_end - f_start, DENSE_FEATURE_HEIGHT);
        }
        */
        
        if ( mode == "Dense" ) {
            slot = 1;
        }
        
        if (mode === "no_detail") {
            // No details for feature, so only one way to display.
            ctx.fillStyle = block_color;
            // TODO: what should width be here?
            ctx.fillRect(f_start, y_center + 5, f_end - f_start, NO_DETAIL_FEATURE_HEIGHT);
        } 
        else { // Mode is either Squish or Pack:
            // Feature details.
            var feature_strand = feature[4],
                feature_ts = feature[5],
                feature_te = feature[6],
                feature_blocks = feature[7];
            
            if (feature_ts && feature_te) {
                thick_start = Math.floor( Math.max(0, (feature_ts - tile_low) * w_scale) );
                thick_end = Math.ceil( Math.min(width, Math.max(0, (feature_te - tile_low) * w_scale)) );
            }
            
            // Set vars that depend on mode.
            var thin_height, thick_height;
            if (mode === "Squish" || mode === "Dense" ) {
                thin_height = 1;
                thick_height = SQUISH_FEATURE_HEIGHT;
            } else { // mode === "Pack"
                thin_height = 5;
                thick_height = PACK_FEATURE_HEIGHT;
            }
            
            // Draw feature/feature blocks + connectors.
            if (!feature_blocks) {
                // If there are no blocks, treat the feature as one big exon.
                if ( feature.strand ) {
                    if (feature.strand === "+") {
                        ctx.fillStyle = ctx.canvas.manager.get_pattern( 'right_strand_inv' );
                    } else if (feature.strand === "-") {
                        ctx.fillStyle = ctx.canvas.manager.get_pattern( 'left_strand_inv' );
                    }
                }
                else { // No strand.
                    ctx.fillStyle = block_color;
                }                            
                ctx.fillRect(f_start, y_center, f_end - f_start, thick_height);
            } else { 
                // There are feature blocks and mode is either Squish or Pack.
                //
                // Approach: (a) draw whole feature as connector/intron and (b) draw blocks as 
                // needed. This ensures that whole feature, regardless of whether it starts with
                // a block, is visible.
                //
                
                // Draw whole feature as connector/intron.
                var cur_y_center, cur_height;
                if (mode === "Squish" || mode === "Dense") {
                    ctx.fillStyle = CONNECTOR_COLOR;
                    cur_y_center = y_center + Math.floor(SQUISH_FEATURE_HEIGHT/2) + 1;
                    cur_height = 1;
                }
                else { // mode === "Pack"
                    if (feature_strand) {
                        var cur_y_center = y_center;
                        var cur_height = thick_height;
                        if (feature_strand === "+") {
                            ctx.fillStyle = ctx.canvas.manager.get_pattern( 'right_strand' );
                        } else if (feature_strand === "-") {
                            ctx.fillStyle = ctx.canvas.manager.get_pattern( 'left_strand' );
                        }
                    }
                    else {
                        ctx.fillStyle = CONNECTOR_COLOR;
                        cur_y_center += (SQUISH_FEATURE_HEIGHT/2) + 1;
                        cur_height = 1;
                    }
                }
                ctx.fillRect(f_start, cur_y_center, f_end - f_start, cur_height);
                
                for (var k = 0, k_len = feature_blocks.length; k < k_len; k++) {
                    var block = feature_blocks[k],
                        block_start = Math.floor( Math.max(0, (block[0] - tile_low) * w_scale) ),
                        // -1 b/c intervals are half-open.
                        block_end = Math.ceil( Math.min(width, Math.max((block[1] - 1 - tile_low) * w_scale)) );

                    // Skip drawing if block not on tile.    
                    if (block_start > block_end) { continue; }

                    // Draw thin block.
                    ctx.fillStyle = block_color;
                    ctx.fillRect(block_start, y_center + (thick_height-thin_height)/2 + 1, 
                                 block_end - block_start, thin_height);

                    // If block intersects with thick region, draw block as thick.
                    // - No thick is sometimes encoded as thick_start == thick_end, so don't draw in that case
                    if (thick_start !== undefined && feature_te > feature_ts && !(block_start > thick_end || block_end < thick_start) ) {
                        var block_thick_start = Math.max(block_start, thick_start),
                            block_thick_end = Math.min(block_end, thick_end); 
                        ctx.fillRect(block_thick_start, y_center + 1,
                                     block_thick_end - block_thick_start, thick_height);
                        if ( feature_blocks.length == 1 && mode == "Pack") {
                            // Exactly one block  means we have no introns, but do have a distinct "thick" region,
                            // draw arrows over it if in pack mode
                            if (feature_strand === "+") {
                                ctx.fillStyle = ctx.canvas.manager.get_pattern( 'right_strand_inv' );
                            } else if (feature_strand === "-") {
                                ctx.fillStyle = ctx.canvas.manager.get_pattern( 'left_strand_inv' );
                            }
                            // If region is wide enough in pixels, pad a bit
                            if ( block_thick_start + 14 < block_thick_end ) {
                                block_thick_start += 2;
                                block_thick_end -= 2;
                            }
                            ctx.fillRect( block_thick_start, y_center + 1,
                                          block_thick_end - block_thick_start, thick_height );
                        }   
                    }
                }
            }
            
            // Draw label for Pack mode.
            if (mode === "Pack" && feature_start > tile_low) {
                ctx.fillStyle = label_color;
                // FIXME: assumption here that the entire view starts at 0
                if (tile_low === 0 && f_start - ctx.measureText(feature_name).width < 0) {
                    ctx.textAlign = "left";
                    ctx.fillText(feature_name, f_end + LABEL_SPACING, y_center + 8);
                } else {
                    ctx.textAlign = "right";
                    ctx.fillText(feature_name, f_start - LABEL_SPACING, y_center + 8);
                }
                ctx.fillStyle = block_color;
            }
        }
    }
});


var VariantPainter = function( data, view_start, view_end, prefs, mode ) {
    FeaturePainter.call( this, data, view_start, view_end, prefs, mode );
}

extend( VariantPainter.prototype, FeaturePainter.prototype, {
    draw_element: function(ctx, mode, feature, slot, tile_low, tile_high, w_scale, y_scale, width) {
        var feature = data[i],
            feature_uid = feature[0],
            feature_start = feature[1],
            // -1 b/c intervals are half-open.
            feature_end = feature[2] - 1,
            feature_name = feature[3],
            // All features need a start, end, and vertical center.
            f_start = Math.floor( Math.max(0, (feature_start - tile_low) * w_scale) ),
            f_end   = Math.ceil( Math.min(width, Math.max(0, (feature_end - tile_low) * w_scale)) ),
            y_center = (mode === "Dense" ? 0 : (0 + slot)) * y_scale,
            thickness, y_start, thick_start = null, thick_end = null;
        
        if (no_label) {
            ctx.fillStyle = block_color;
            ctx.fillRect(f_start + left_offset, y_center + 5, f_end - f_start, 1);
        } else { // Show blocks, labels, etc.                        
            // Unpack.
            var ref_base = feature[4], alt_base = feature[5], qual = feature[6];
        
            // Draw block for entry.
            thickness = 9;
            y_start = 1;
            ctx.fillRect(f_start + left_offset, y_center, f_end - f_start, thickness);
        
            // Add label for entry.
            if (mode !== "Dense" && feature_name !== undefined && feature_start > tile_low) {
                // Draw label
                ctx.fillStyle = label_color;
                if (tile_low === 0 && f_start - ctx.measureText(feature_name).width < 0) {
                    ctx.textAlign = "left";
                    ctx.fillText(feature_name, f_end + 2 + left_offset, y_center + 8);
                } else {
                    ctx.textAlign = "right";
                    ctx.fillText(feature_name, f_start - 2 + left_offset, y_center + 8);
                }
                ctx.fillStyle = block_color;
            }
        
            // Show additional data on block.
            var vcf_label = ref_base + " / " + alt_base;
            if (feature_start > tile_low && ctx.measureText(vcf_label).width < (f_end - f_start)) {
                ctx.fillStyle = "white";
                ctx.textAlign = "center";
                ctx.fillText(vcf_label, left_offset + f_start + (f_end-f_start)/2, y_center + 8);
                ctx.fillStyle = block_color;
            }
        }
    }
});

/**
 * Compute the type of overlap between two regions. They are assumed to be on the same chrom/contig.
 * The overlap is computed relative to the second region; hence, OVERLAP_START indicates that the first
 * region overlaps the start (but not the end) of the second region.
 */
var NO_OVERLAP = 1001, CONTAINS = 1002, OVERLAP_START = 1003, OVERLAP_END = 1004, CONTAINED_BY = 1005;
var compute_overlap = function(first_region, second_region) {
    var 
        first_start = first_region[0], first_end = first_region[1],
        second_start = second_region[0], second_end = second_region[1],
        overlap;
    if (first_start < second_start) {
        if (first_end < second_start) {
            overlap = NO_OVERLAP;
        }
        else if (first_end <= second_end) {
            overlap = OVERLAP_START;
        }
        else { // first_end > second_end
            overlap = CONTAINS;
        }
    }
    else { // first_start >= second_start
        if (first_start > second_end) {
            overlap = NO_OVERLAP;
        }
        else if (first_end <= second_end) {
            overlap = CONTAINED_BY;
        }
        else {
            overlap = OVERLAP_END;
        }
    }
    
    return overlap;
}

var ReadPainter = function( data, view_start, view_end, prefs, mode, ref_seq ) {
    FeaturePainter.call( this, data, view_start, view_end, prefs, mode );
    this.ref_seq = ref_seq;
}

extend( ReadPainter.prototype, FeaturePainter.prototype, {
    /**
     * Returns y_scale based on mode.
     */
    get_row_height: function() {
        var y_scale, mode = this.mode;
        if (mode === "Dense") {
            y_scale = DENSE_TRACK_HEIGHT;            
        }
        else if (mode === "Squish") {
            y_scale = SQUISH_TRACK_HEIGHT;
        }
        else { // mode === "Pack"
            y_scale = PACK_TRACK_HEIGHT;
            if (this.prefs.show_insertions) {
                y_scale *= 2;
            }
        }
        return y_scale;
    },
    /**
     * Draw a single read.
     */
    draw_read: function(ctx, mode, w_scale, tile_low, tile_high, feature_start, cigar, orig_seq, y_center) {
        ctx.textAlign = "center";
        var track = this,
            tile_region = [tile_low, tile_high],
            base_offset = 0,
            seq_offset = 0,
            gap = 0
            ref_seq = this.ref_seq,
            char_width_px = ctx.canvas.manager.char_width_px;
            
        // Keep list of items that need to be drawn on top of initial drawing layer.
        var draw_last = [];
        
        // Gap is needed so that read is offset and hence first base can be drawn on read.
        // TODO-FIX: using this gap offsets reads so that their start is not visually in sync with other tracks.
        if ((mode === "Pack" || this.mode === "Auto") && orig_seq !== undefined && w_scale > char_width_px) {
            gap = Math.round(w_scale/2);
        }
        if (!cigar) {
            // If no cigar string, then assume all matches
            cigar = [ [0, orig_seq.length] ]
        }
        for (var cig_id = 0, len = cigar.length; cig_id < len; cig_id++) {
            var cig = cigar[cig_id],
                cig_op = "MIDNSHP=X"[cig[0]],
                cig_len = cig[1];
            
            if (cig_op === "H" || cig_op === "S") {
                // Go left if it clips
                base_offset -= cig_len;
            }
            var seq_start = feature_start + base_offset,
                s_start = Math.floor( Math.max(0, (seq_start - tile_low) * w_scale) ),
                s_end = Math.floor( Math.max(0, (seq_start + cig_len - tile_low) * w_scale) );
                
            switch (cig_op) {
                case "H": // Hard clipping.
                    // TODO: draw anything?
                    // Sequence not present, so do not increment seq_offset.
                    break;
                case "S": // Soft clipping.
                case "M": // Match.
                case "=": // Equals.
                    var seq_tile_overlap = compute_overlap([seq_start, seq_start + cig_len], tile_region);
                    if (seq_tile_overlap !== NO_OVERLAP) {
                        // Draw.
                        var seq = orig_seq.slice(seq_offset, seq_offset + cig_len);
                        if (gap > 0) {
                            ctx.fillStyle = this.prefs.block_color;
                            ctx.fillRect(s_start - gap, y_center + 1, s_end - s_start, 9);
                            ctx.fillStyle = CONNECTOR_COLOR;
                            // TODO: this can be made much more efficient by computing the complete sequence
                            // to draw and then drawing it.
                            for (var c = 0, str_len = seq.length; c < str_len; c++) {
                                if (this.prefs.show_differences && ref_seq) {
                                    var ref_char = ref_seq[seq_start - tile_low + c];
                                    if (!ref_char || ref_char.toLowerCase() === seq[c].toLowerCase()) {
                                        continue;
                                    }
                                }
                                if (seq_start + c >= tile_low && seq_start + c <= tile_high) {
                                    var c_start = Math.floor( Math.max(0, (seq_start + c - tile_low) * w_scale) );
                                    ctx.fillText(seq[c], c_start, y_center + 9);
                                }
                            }
                        } else {
                            ctx.fillStyle = this.prefs.block_color;
                            // TODO: This is a pretty hack-ish way to fill rectangle based on mode.
                            ctx.fillRect(s_start, y_center + 4, s_end - s_start, SQUISH_FEATURE_HEIGHT);
                        }
                    }
                    seq_offset += cig_len;
                    base_offset += cig_len;
                    break;
                case "N": // Skipped bases.
                    ctx.fillStyle = CONNECTOR_COLOR;
                    ctx.fillRect(s_start - gap, y_center + 5, s_end - s_start, 1);
                    //ctx.dashedLine(s_start + this.left_offset, y_center + 5, this.left_offset + s_end, y_center + 5);
                    // No change in seq_offset because sequence not used when skipping.
                    base_offset += cig_len;
                    break;
                case "D": // Deletion.
                    ctx.fillStyle = "red";
                    ctx.fillRect(s_start - gap, y_center + 4, s_end - s_start, 3);
                    // TODO: is this true? No change in seq_offset because sequence not used when skipping.
                    base_offset += cig_len;
                    break;
                case "P": // TODO: No good way to draw insertions/padding right now, so ignore
                    // Sequences not present, so do not increment seq_offset.
                    break;
                case "I": // Insertion.
                    // Check to see if sequence should be drawn at all by looking at the overlap between
                    // the sequence region and the tile region.
                    var 
                        seq_tile_overlap = compute_overlap([seq_start, seq_start + cig_len], tile_region),
                        insert_x_coord = s_start - gap;
                    
                    if (seq_tile_overlap !== NO_OVERLAP) {
                        var seq = orig_seq.slice(seq_offset, seq_offset + cig_len);
                        // Insertion point is between the sequence start and the previous base: (-gap) moves
                        // back from sequence start to insertion point.
                        if (this.prefs.show_insertions) {
                            //
                            // Show inserted sequence above, centered on insertion point.
                            //

                            // Draw sequence.
                            // X center is offset + start - <half_sequence_length>
                            var x_center = s_start - (s_end - s_start)/2;
                            if ( (mode === "Pack" || this.mode === "Auto") && orig_seq !== undefined && w_scale > char_width_px) {
                                // Draw sequence container.
                                ctx.fillStyle = "yellow";
                                ctx.fillRect(x_center - gap, y_center - 9, s_end - s_start, 9);
                                draw_last[draw_last.length] = {type: "triangle", data: [insert_x_coord, y_center + 4, 5]};
                                ctx.fillStyle = CONNECTOR_COLOR;
                                // Based on overlap b/t sequence and tile, get sequence to be drawn.
                                switch(seq_tile_overlap) {
                                    case(OVERLAP_START):
                                        seq = seq.slice(tile_low-seq_start);
                                        break;
                                    case(OVERLAP_END):
                                        seq = seq.slice(0, seq_start-tile_high);
                                        break;
                                    case(CONTAINED_BY):
                                        // All of sequence drawn.
                                        break;
                                    case(CONTAINS):
                                        seq = seq.slice(tile_low-seq_start, seq_start-tile_high);
                                        break;
                                }
                                // Draw sequence.
                                for (var c = 0, str_len = seq.length; c < str_len; c++) {
                                    var c_start = Math.floor( Math.max(0, (seq_start + c -  tile_low) * w_scale) );
                                    ctx.fillText(seq[c], c_start - (s_end - s_start)/2, y_center);
                                }
                            }
                            else {
                                // Draw block.
                                ctx.fillStyle = "yellow";
                                // TODO: This is a pretty hack-ish way to fill rectangle based on mode.
                                ctx.fillRect(x_center, y_center + (this.mode !== "Dense" ? 2 : 5), 
                                             s_end - s_start, (mode !== "Dense" ? SQUISH_FEATURE_HEIGHT : DENSE_FEATURE_HEIGHT));
                            }
                        }
                        else {
                            if ( (mode === "Pack" || this.mode === "Auto") && orig_seq !== undefined && w_scale > char_width_px) {
                                // Show insertions with a single number at the insertion point.
                                draw_last[draw_last.length] = {type: "text", data: [seq.length, insert_x_coord, y_center + 9]};
                            }
                            else {
                                // TODO: probably can merge this case with code above.
                            }
                        }
                    }
                    seq_offset += cig_len;
                    // No change to base offset because insertions are drawn above sequence/read.
                    break;
                case "X":
                    // TODO: draw something?
                    seq_offset += cig_len;
                    break;
            }
        }
        
        //
        // Draw last items.
        //
        ctx.fillStyle = "yellow";
        var item, type, data;
        for (var i = 0; i < draw_last.length; i++) {
            item = draw_last[i];
            type = item["type"];
            data = item["data"];
            if (type === "text") {
                ctx.save();
                ctx.font = "bold " + ctx.font;
                ctx.fillText(data[0], data[1], data[2]);
                ctx.restore();
            }
            else if (type == "triangle") {
                drawDownwardEquilateralTriangle(ctx, data[0], data[1], data[2]);
            }
        }
    },
    /**
     * Draw a complete read pair
     */
    draw_element: function(ctx, mode, feature, slot, tile_low, tile_high, w_scale, y_scale, width ) {
        // All features need a start, end, and vertical center.
        var feature_uid = feature[0],
            feature_start = feature[1],
            feature_end = feature[2],
            feature_name = feature[3],
            f_start = Math.floor( Math.max(0, (feature_start - tile_low) * w_scale) ),
            f_end   = Math.ceil( Math.min(width, Math.max(0, (feature_end - tile_low) * w_scale)) ),
            y_center = (mode === "Dense" ? 0 : (0 + slot)) * y_scale,
            block_color = this.prefs.block_color,
            label_color = this.prefs.label_color,
            // Left-gap for label text since we align chrom text to the position tick.
            gap = 0;

        // TODO: fix gap usage; also see note on gap in draw_read.
        if ((mode === "Pack" || this.mode === "Auto") && w_scale > ctx.canvas.manager.char_width_px) {
            var gap = Math.round(w_scale/2);
        }
        
        // Draw read.
        ctx.fillStyle = block_color;
        if (feature[5] instanceof Array) {
            // Read is paired.
            var b1_start = Math.floor( Math.max(0, (feature[4][0] - tile_low) * w_scale) ),
                b1_end   = Math.ceil( Math.min(width, Math.max(0, (feature[4][1] - tile_low) * w_scale)) ),
                b2_start = Math.floor( Math.max(0, (feature[5][0] - tile_low) * w_scale) ),
                b2_end   = Math.ceil( Math.min(width, Math.max(0, (feature[5][1] - tile_low) * w_scale)) );

            // Draw left/forward read.
            if (feature[4][1] >= tile_low && feature[4][0] <= tile_high && feature[4][2]) {
                this.draw_read(ctx, mode, w_scale, tile_low, tile_high, feature[4][0], feature[4][2], feature[4][3], y_center);
            }
            // Draw right/reverse read.
            if (feature[5][1] >= tile_low && feature[5][0] <= tile_high && feature[5][2]) {
                this.draw_read(ctx, mode, w_scale, tile_low, tile_high, feature[5][0], feature[5][2], feature[5][3], y_center);
            }
            // Draw connector.
            if (b2_start > b1_end) {
                ctx.fillStyle = CONNECTOR_COLOR;
                dashedLine(ctx, b1_end - gap, y_center + 5, b2_start - gap, y_center + 5);
            }
        } else {
            // Read is single.
            ctx.fillStyle = block_color;
            this.draw_read(ctx, mode, w_scale, tile_low, tile_high, feature_start, feature[4], feature[5], y_center);
        }
        if (mode === "Pack" && feature_start > tile_low) {
            // Draw label.
            ctx.fillStyle = this.prefs.label_color;
            // FIXME: eliminate tile_index
            var tile_index = 1;
            if (tile_index === 0 && f_start - ctx.measureText(feature_name).width < 0) {
                ctx.textAlign = "left";
                ctx.fillText(feature_name, f_end + LABEL_SPACING - gap, y_center + 8);
            } else {
                ctx.textAlign = "right";
                ctx.fillText(feature_name, f_start - LABEL_SPACING - gap, y_center + 8);
            }
            ctx.fillStyle = block_color;
        }
    }
});

exports.SummaryTreePainter = SummaryTreePainter;
exports.LinePainter = LinePainter;
exports.LinkedFeaturePainter = LinkedFeaturePainter;
exports.ReadPainter = ReadPainter;
exports.VariantPainter = VariantPainter;

// End painters_module encapsulation
};

// Finally, compose and export trackster module exports into globals
// These will be replaced with require statements in CommonJS
(function(target){
    // Faking up a CommonJS like loader here, each module gets a require and
    // and exports. We avoid resolution problems by just ordering carefully.
    var modules = {};
    // Provide a require function
    var require = function( name ) {
        return modules[name];
    };
    // Run module will run the module_function provided and store in the
    // require dict using key
    var run_module = function( key, module_function ) {
        var exports = {};
        module_function( require, exports );
        modules[key] = exports;
    };
    // Run all modules
    run_module( 'slotting', slotting_module );
    run_module( 'painters', painters_module );
    run_module( 'trackster', trackster_module );
    // Export trackster stuff
    for ( key in modules.trackster ) {
        target[key] = modules.trackster[key];
    }
})(window);