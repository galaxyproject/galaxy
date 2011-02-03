/* Trackster
    2010, James Taylor, Kanwei Li
*/

/**
 * Draw a dashed line on a canvas using filled rectangles. This function is based on:
 * http://vetruvet.blogspot.com/2010/10/drawing-dashed-lines-on-html5-canvas.html
 * However, that approach uses lines, which don't seem to render as well, so use
 * rectangles instead.
 */
CanvasRenderingContext2D.prototype.dashedLine = function(x1, y1, x2, y2, dashLen) {
    if (dashLen == undefined) { dashLen = 4; }
    var dX = x2 - x1;
    var dY = y2 - y1;
    var dashes = Math.floor(Math.sqrt(dX * dX + dY * dY) / dashLen);
    var dashX = dX / dashes;
    var dashY = dY / dashes;
    
    for (var q= 0; q < dashes; q++, x1 += dashX, y1 += dashY) {
        if (q % 2 != 0) {
            continue;
        }
        this.fillRect(x1, y1, dashLen, 1);
    }
};

/** 
 * Make `element` sortable in parent by dragging `handle` (a selector)
 */
function sortable( element, handle ) {
    element.bind( "drag", { handle: handle, relative: true }, function ( e, d ) {
        var parent = $(this).parent();
        var children = parent.children();
        // Determine new position
        for ( var i = 0; i < children.length; i++ ) {
            if ( d.offsetY < $(children.get(i)).position().top ) {
                break;
            }
        }
        // If not already in the right place, move. Need 
        // to handle the end specially since we don't have 
        // insert at index
        if ( i == children.length ) {
            if ( this != children.get( i - 1 ) ) {
                parent.append( this );
            }
        }
        else if ( this != children.get( i ) ) {
            $(this).insertBefore( children.get( i ) );
        }
    });
}

/**
 * Init constants & functions used throughout trackster.
 */
var 
    DENSITY = 200,
    FEATURE_LEVELS = 10,
    MAX_FEATURE_DEPTH = 100,
    DEFAULT_DATA_QUERY_WAIT = 5000,
    CONNECTOR_COLOR = "#ccc",
    DATA_ERROR = "There was an error in indexing this dataset. ",
    DATA_NOCONVERTER = "A converter for this dataset is not installed. Please check your datatypes_conf.xml file.",
    DATA_NONE = "No data for this chrom/contig.",
    DATA_PENDING = "Currently indexing... please wait",
    DATA_CANNOT_RUN_TOOL = "Tool cannot be rerun: ",
    DATA_LOADING = "Loading data...",
    DATA_OK = "Ready for display",
    FILTERABLE_CLASS = "filterable",
    CACHED_TILES_FEATURE = 10,
    CACHED_TILES_LINE = 5,
    CACHED_DATA = 5,
    DUMMY_CANVAS = document.createElement("canvas"),
    RIGHT_STRAND, LEFT_STRAND;

// Get information for rendering canvas elements.    
if (window.G_vmlCanvasManager) {
    G_vmlCanvasManager.initElement(DUMMY_CANVAS);
}
CONTEXT = DUMMY_CANVAS.getContext("2d");
PX_PER_CHAR = CONTEXT.measureText("A").width;
    
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
$.extend(Cache.prototype, {
    get: function(key) {
        var index = this.key_ary.indexOf(key);
        if (index != -1) {
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
 * Data-specific cache.
 */
var DataCache = function(num_elements) {
    Cache.call(this, num_elements);  
};
$.extend(DataCache.prototype, Cache.prototype, {
    get_data: function(low, high, mode) {
        // Debugging:
        //console.log("get_data", low, high, mode);
        /*
        console.log("cache contents:")
        for (var i = 0; i < this.key_ary.length; i++) {
            console.log("\t", this.key_ary[i], this.obj_cache[this.key_ary[i]]);
        }
        */
        
        // Look for key in cache and, if found, return it.
        var entry = this.get(this.gen_key(low, high, mode));
        if (entry) {
            return entry;
        }

        //
        // Look in cache for data that can be used. Data can be reused if it
        // has the requested data and is not summary tree and has details.
        // TODO: this logic could be improved if the visualization knew whether
        // the data was "index" or "data." Also could slice the data so that
        // only data points in request are returned.
        //
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
        
        return undefined;
    },
    set_data: function(low, high, mode, result) {
        //console.log("set_data", low, high, mode, result);
        return this.set(this.gen_key(low, high, mode), result);
    },
    // Generate key for cache.
    gen_key: function(low, high, mode) {
        // TODO: use mode to generate key?
        var key = low + "_" + high;
        /*
        if (no_detail) {
            key += "_" + no_detail
        }
        */
        return key;
    },
    // Split key from cache into array with format [low, high, mode]
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
    this.reset();
};
$.extend( View.prototype, {
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
        this.chrom_form = $("<form/>").attr("action", function() {} ).appendTo(this.nav_controls);
        this.chrom_select = $("<select/>").attr({ "name": "chrom"}).css("width", "15em").addClass("no-autocomplete").append("<option value=''>Loading</option>").appendTo(this.chrom_form);
        var submit_nav = function(e) {
            if (e.type === "focusout" || (e.keyCode || e.which) === 13 || (e.keyCode || e.which) === 27 ) {
                if ((e.keyCode || e.which) !== 27) { // Not escape key
                    view.go_to( $(this).val() );
                }
                $(this).hide();
                view.location_span.show();
                view.chrom_select.show();
                return false;
            }
        };
        this.nav_input = $("<input/>").addClass("nav-input").hide().bind("keypress focusout", submit_nav).appendTo(this.chrom_form);
        this.location_span = $("<span/>").addClass("location").appendTo(this.chrom_form);
        this.location_span.bind("click", function() {
            view.location_span.hide();
            view.chrom_select.hide();
            view.nav_input.css("display", "inline-block");
            view.nav_input.select();
            view.nav_input.focus();
        });
        if (this.vis_id !== undefined) {
            this.hidden_input = $("<input/>").attr("type", "hidden").val(this.vis_id).appendTo(this.chrom_form);
        }
        this.zo_link = $("<a id='zoom-out' />").click(function() { view.zoom_out(); view.redraw(); }).appendTo(this.chrom_form);
        this.zi_link = $("<a id='zoom-in' />").click(function() { view.zoom_in(); view.redraw(); }).appendTo(this.chrom_form);        
        
        $.ajax({
            url: chrom_url, 
            data: (this.vis_id !== undefined ? { vis_id: this.vis_id } : { dbkey: this.dbkey }),
            dataType: "json",
            success: function ( result ) {
                if (result.reference) {
                    view.add_label_track( new ReferenceTrack(view) );
                }
                view.chrom_data = result.chrom_info;
                var chrom_options = '<option value="">Select Chrom/Contig</option>';
                for (var i = 0, len = view.chrom_data.length; i < len; i++) {
                    var chrom = view.chrom_data[i].chrom;
                    chrom_options += '<option value="' + chrom + '">' + chrom + '</option>';
                }
                view.chrom_select.html(chrom_options);
                view.intro_div.show();
                view.chrom_select.bind("change", function() {
                    view.change_chrom(view.chrom_select.val());
                });
                if ( callback ) {
                    callback();
                }
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
        this.viewport_container.bind( "dragstart", function( e, d ) {
            d.original_low = view.low;
            d.current_height = e.clientY;
            d.current_x = d.offsetX;
            // Fix webkit scrollbar
            d.enable_pan = (e.clientX < view.viewport_container.width() - 16) ? true : false; 
        }).bind( "drag", function( e, d ) {
            if (!d.enable_pan) { return; }
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
                "height": view.content_div.height() + view.top_labeltrack.height() + view.nav_labeltrack.height(), 
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
    change_chrom: function(chrom, low, high) {
        var view = this;
        var found = $.grep(view.chrom_data, function(v, i) {
            return v.chrom === chrom;
        })[0];
        if (found === undefined) {
            // Invalid chrom
            return;
        }
        if (chrom !== view.chrom) {
            view.chrom = chrom;
            if (!view.chrom) {
                // No chrom selected
                view.intro_div.show();
            } else {
                view.intro_div.hide();
            }
            view.chrom_select.val(view.chrom);
            view.max_high = found.len;
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
 * Encapsulation of tools that users can apply to tracks/datasets.
 */
var Tool = function(name, params) {
    this.name = name;
    this.params = params;  
};
$.extend(Tool.prototype, {
    // Returns a dictionary of parameter values; key is parameter name, value
    // is parameter value.
    get_param_values_dict: function() {
        var param_dict = {};
        for (var i = 0; i < this.params.length; i++) {
            var param = this.params[i];
            param_dict[param.name] = param.value;
        }
        return param_dict;
    },
    // Returns an array of parameter values.
    get_param_values: function() {
        var param_values = [];
        for (var i = 0; i < this.params.length; i++) {
            param_values[i] = this.params[i].value;
        }
        return param_values;
    }
});

var NumberToolParameter = function(name, label, min, max, init_value) {
    this.name = name;
    this.label = label;
    this.min = min;
    this.max = max;
    this.value = init_value;
}

// Uses a dictionary to construct a tool object.
var get_tool_from_dict = function(tool_dict) {
    if (obj_length(tool_dict) == 0) {
        return undefined;
    }
    
    // Get tool.
    var tool_name = tool_dict.name;
    var params_dict = tool_dict.params;
    var params = Array();
    for (var i = 0; i < params_dict.length; i++) {
        var param_dict = params_dict[i];
        var 
            name = param_dict.name,
            label = param_dict.label,
            type = param_dict.type,
            min = param_dict.min,
            max = param_dict.max,
            value = param_dict.value;
        params[params.length] = new NumberToolParameter(name, label, min, max, value);
    }
    return new Tool(tool_name, params);
};

/**
 * Filters that enable users to show/hide data points dynamically.
 */
var Filter = function(name, index, value) {
    this.name = name;
    this.index = index;
    this.value = value;
};
var NumberFilter = function(name, index) {
    this.name = name;
    // Index into payload to filter.
    this.index = index;
    // Filter low/high. These values are used to filter elements.
    this.low = -Number.MAX_VALUE;
    this.high = Number.MAX_VALUE;
    // Slide min/max. These values are used to set/update slider.
    this.slider_min = Number.MAX_VALUE;
    this.slider_max = -Number.MAX_VALUE;
    // UI Slider element and label that is associated with filter.
    this.slider = null;
    this.slider_label = null;
};
$.extend(NumberFilter.prototype, {
    // Returns true if filter can be applied to element.
    applies_to: function(element) {
        if (element.length > this.index) {
            return true;
        }
        return false;
    },
    // Returns true iff element is in [low, high]; range is inclusive.
    keep: function(element) {
        if ( !this.applies_to( element ) ) {
            // No element to filter on.
            return true;
        }
        return (element[this.index] >= this.low && element[this.index] <= this.high);
    },
    // Update filter's min and max values based on element's values.
    update_attrs: function(element) {
        var updated = false;
        if (!this.applies_to(element) ) {
            return updated;
        }
        
        // Update filter's min, max based on element values.
        if (element[this.index] < this.slider_min) {
            this.slider_min = element[this.index];
            updated = true;
        }
        if (element[this.index] > this.slider_max) {
            this.slider_max = element[this.index];
            updated = false;
        }
        return updated;
    },
    // Update filter's slider.
    update_ui_elt: function () {
        var 
            slider_min = this.slider.slider("option", "min"),
            slider_max = this.slider.slider("option", "max");
        if (this.slider_min < slider_min || this.slider_max > slider_max) {
            // Need to update slider.        
            this.slider.slider("option", "min", this.slider_min);
            this.slider.slider("option", "max", this.slider_max);
            // Refresh slider:
            // TODO: do we want to keep current values or reset to min/max?
            // Currently we reset values:
            this.slider.slider("option", "values", [this.slider_min, this.slider_max]);
            // To use the current values.
            //var values = this.slider.slider( "option", "values" );
            //this.slider.slider( "option", "values", values );
        }
    }
});

// Parse filters dict and return filters.
var get_filters_from_dict = function(filters_dict) {
    var filters = [];
    for (var i = 0; i < filters_dict.length; i++) {
        var filter_dict = filters_dict[i];
        var name = filter_dict.name, type = filter_dict.type, index = filter_dict.index;
        if (type == 'int' || type == 'float') {
            filters[i] = new NumberFilter(name, index);
        } else {
            filters[i] = new Filter(name, index, type);
        }
    }
    return filters;
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
$.extend( Track.prototype, {
    /**
     * Initialize and draw the track.
     */
    init: function() {
        var track = this;
        track.enabled = false;
        track.data_queue = {};
        track.tile_cache.clear();    
        track.data_cache.clear();
        track.initial_canvas = undefined;
        track.content_div.css("height", "auto");
        if (!track.content_div.text()) {
            track.content_div.text(DATA_LOADING);
        }
        track.container_div.removeClass("nodata error pending");
        
        //
        // Tracks with no dataset id are handled differently.
        //
        if (!track.dataset_id) {
            return;
        }
        
        // Get dataset state; if state is fine, enable and draw track. Otherwise, show message 
        // about track status.
        $.getJSON(this.dataset_check_url, { hda_ldda: track.hda_ldda, dataset_id: track.dataset_id, 
                                            chrom: track.view.chrom, low: track.view.max_low, high: track.view.max_high}, 
                 function (result) {
            if (!result || result === "error" || result.kind === "error") {
                track.container_div.addClass("error");
                track.content_div.text(DATA_ERROR);
                if (result.message) {
                    var track_id = track.view.tracks.indexOf(track);
                    var error_link = $(" <a href='javascript:void(0);'></a>").attr("id", track_id + "_error");
                    error_link.text("View error");
                    $("#" + track_id + "_error").live("click", function() {                        
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
            } else if (result === "data") {
                // Only draw in user has selected a chromosome.
                track.content_div.text(DATA_OK);
                if (track.view.chrom) {
                    track.content_div.text("");
                    track.content_div.css( "height", track.height_px + "px" );
                    track.enabled = true;
                    track.predraw_init();
                    track.draw();
                }
            }
        });
    },
    /**
     * Additional initialization required before drawing track for the first time.
     */
    predraw_init: function() {},
    restore_prefs: function(prefs) {
        var that = this;
        $.each(prefs, function(pref, val) {
            if (val !== undefined) {
                that.prefs[pref] = val;
            }
        });
    },
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

var TiledTrack = function(filters, tool, parent_track) {
    var track = this,
        view = track.view;
    
    // Attribute init.
    this.filters = (filters !== undefined ? get_filters_from_dict( filters ) : []);
    this.tool = (tool !== undefined ? get_tool_from_dict( tool ) : undefined);
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
    this.filtering_div = $("<div/>").addClass("track-filters").hide();
    this.header_div.after(this.filtering_div);
    // Disable dragging, double clicking on div so that actions on slider do not impact viz.
    this.filtering_div.bind("drag", function(e) {
        e.stopPropagation();
    }).bind("dblclick", function(e) {
        e.stopPropagation();
    });
    var filters_table = $("<table class='filters'>").appendTo(this.filtering_div);
    $.each(this.filters, function(index, filter) {
        var table_row = $("<tr>").appendTo(filters_table);
        var filter_th = $("<th class='filter-info'>").appendTo(table_row);
        var name_span = $("<span class='name'>").appendTo(filter_th);
        name_span.text(filter.name + "  "); // Extra spacing to separate name and values
        var values_span = $("<span class='values'>").appendTo(filter_th);
        // TODO: generate custom interaction elements based on filter type.
        var table_data = $("<td>").appendTo(table_row);
        filter.control_element = $("<div id='" + filter.name + "-filter-control' style='width: 200px; position: relative'>").appendTo(table_data);
        filter.control_element.slider({
            range: true,
            min: Number.MAX_VALUE,
            max: -Number.MIN_VALUE,
            values: [0, 0],
            slide: function( event, ui ) {
                var values = ui.values;
                // Set new values in UI.
                values_span.text( "[" + values[0] + "-" + values[1] + "]" );
                // Set new values in filter.
                filter.low = values[0];
                filter.high = values[1];                    
                // Redraw track.
                track.draw( true );
            },
            change: function( event, ui ) {
                filter.control_element.slider( "option", "slide" ).call( filter.control_element, event, ui );
            }
        });
        filter.slider = filter.control_element;
        filter.slider_label = values_span;
    });
    
    //
    // Create dynamic tool div.
    //
    if (this.tool) {  
        // Create div elt for tool UI.
        this.dynamic_tool_div = $("<div/>").addClass("dynamic-tool").hide();
        this.header_div.after(this.dynamic_tool_div);
        // Disable dragging, clicking, double clicking on div so that actions on slider do not impact viz.
        this.dynamic_tool_div.bind( "drag", function(e) {
            e.stopPropagation();
        }).bind("click", function( e ) {
            e.stopPropagation();
        }).bind("dblclick", function( e ) {
            e.stopPropagation();
        });
        var name_div = $("<div class='tool-name'>").appendTo(this.dynamic_tool_div).text(this.tool.name);
        var tool_params = this.tool.params;
        var track = this;
        $.each(this.tool.params, function(index, param) {
            var param_div = $("<div>").addClass("param-row").appendTo(track.dynamic_tool_div);
            
            //
            // Slider label.
            //
            var label_div = $("<div>").addClass("slider-label").appendTo(param_div);
            var name_span = $("<span class='param-name'>").text(param.label + "  ").appendTo(label_div);
            var values_span = $("<span/>").text(param.value);
            var values_span_container = $("<span class='param-value'>").appendTo(label_div).append("[").append(values_span).append("]");
            
            //
            // Slider.
            //
            var slider_div = $("<div/>").addClass("slider").appendTo(param_div);
            var slider = $("<div id='" + param.name + "-param-control'>").appendTo(slider_div);
            // Make step reasonable.
            var step = (param.max <= 1 ? 0.01 : (param.max <= 1000 ? 1 : 5));
            slider.slider({
                min: param.min,
                max: param.max,
                step: step,
                value: param.value,
                slide: function(event, ui) {
                    var value = ui.value;
                    param.value = value;
                    // Set new value in UI.
                    if (0 < value && value < 1) {
                        value = parseFloat(value).toFixed(2);
                    }
                    values_span.text(value);
                },
                change: function(event, ui) {
                    param.value = ui.value;
                }   
            });
            
            //
            // Enable users to edit parameter's value via a text box.
            //
            values_span_container.click(function() {
                var span = values_span,
                    cur_value = span.text(),
                    // TODO: is there a better way to handle input size when param max is <= 1?
                    input_size = (param.max <= 1 ? 4 : param.max.length);
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
                    if ( e.keyCode === 27 ) {
                        // Escape key.
                        $(this).trigger("blur");
                    } else if ( e.keyCode === 13 ) {
                        // Enter/return key sets new value.
                        var input = $(this),
                            new_value = parseFloat(input.val());
                        if (isNaN(new_value) || new_value > param.max || new_value < param.min) {
                            // TODO: display popup menu instead of alert?
                            alert("Parameter value must be in the range [" + param.min + "-" + param.max + "]");
                            return $(this);
                        }
                        // Update value in three places; update param value last b/c slider updates param value 
                        // as well and slider may round values depending on its settings.
                        span.text(new_value);
                        slider.slider('value', new_value);
                        param.value = new_value;
                    }
                });
            });
            
            // Added to clear floating layout.
            $("<div style='clear: both;'/>").appendTo(param_div); 
        });
        
        // Add 'Go' button.
        var run_tool_row = $("<div>").addClass("param-row").appendTo(this.dynamic_tool_div);
        var run_tool_button = $("<input type='submit'>").attr("value", "Run").appendTo(run_tool_row);
        var track = this;
        run_tool_button.click( function() {
            track.run_tool(); 
        });
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
            var init_mode = track.display_modes[0];
            track.mode = init_mode;
            track.mode_div.text(init_mode);
        
            var change_mode = function(name) {
                track.mode_div.text(name);
                track.mode = name;
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
    
    //
    // Track dropdown menu.
    //
    var track_dropdown = {};
    track_dropdown["Edit configuration"] = function() {
        var cancel_fn = function() { hide_modal(); $(window).unbind("keypress.check_enter_esc"); },
            ok_fn = function() { track.update_options(track.track_id); hide_modal(); $(window).unbind("keypress.check_enter_esc"); },
            check_enter_esc = function(e) {
                if ((e.keyCode || e.which) === 27) { // Escape key
                    cancel_fn();
                } else if ((e.keyCode || e.which) === 13) { // Enter key
                    ok_fn();
                }
            };

        $(window).bind("keypress.check_enter_esc", check_enter_esc);        
        show_modal("Configure Track", track.gen_options(track.track_id), {
            "Cancel": cancel_fn,
            "OK": ok_fn
        });
    };
    
    track_dropdown["Set as overview"] = function() {
        view.overview_viewport.find("canvas").remove();
        track.is_overview = true;
        track.set_overview();
        for (var track_id in view.tracks) {
            if (view.tracks[track_id] !== track) {
                view.tracks[track_id].is_overview = false;
            }
        }
    };
    
    if (track.filters.length > 0) {
        // Show/hide filters menu item.
        track_dropdown["Show filters"] = function() {
            // Set option text and toggle filtering div.
            var menu_option_text;
            if (!track.filtering_div.is(":visible")) {
                menu_option_text = "Hide filters";
                track.filters_visible = true;
            }
            else {
                menu_option_text = "Show filters";
                track.filters_visible = false;
            }
            // TODO: set menu option name.
            track.filtering_div.toggle();
        };
    }
    if (track.tool) {
        // Show/hide dynamic tool menu item.
        track_dropdown["Toggle Tool"] = function() {
            // Show/hide tool, update/revert name, and set menu text.
            var menu_option_text;
            if (!track.dynamic_tool_div.is(":visible")) {
                menu_option_text = "Hide dynamic tool";
                track.update_name(track.name + track.tool_region_and_parameters_str());
            }
            else {
                menu_option_text = "Show dynamic tool";
                track.revert_name();
            }
            // TODO: set menu option name.
            track.dynamic_tool_div.toggle();
        };
    }
    
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
    track.popup_menu = make_popupmenu(track.name_div, track_dropdown);
    
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
$.extend( TiledTrack.prototype, Track.prototype, {
    draw: function(force) {
        var low = this.view.low,
            high = this.view.high,
            range = high - low,
            resolution = this.view.resolution;

        var parent_element = $("<div style='position: relative;'></div>"),
            w_scale = this.content_div.width() / range;

        this.content_div.append( parent_element );
        this.max_height = 0;
        // Index of first tile that overlaps visible region
        var tile_index = Math.floor( low / resolution / DENSITY );
        // A list of setTimeout() ids used when drawing tiles. Each ID indicates
        // a tile has been requested to be drawn or is being drawn.
        var draw_tile_ids = {};
        while ( ( tile_index * DENSITY * resolution ) < high ) {
            // Check in cache
            var key = this.content_div.width() + '_' + w_scale + '_' + tile_index;
            var cached = this.tile_cache.get(key);
            // console.log(cached, this.tile_cache);
            if ( !force && cached ) {
                var tile_low = tile_index * DENSITY * resolution;
                var left = ( tile_low - low ) * w_scale;
                if (this.left_offset) {
                    left -= this.left_offset;
                }
                cached.css({ left: left });
                this.show_tile( cached, parent_element );
            } else {
                this.delayed_draw(this, key, low, high, tile_index, resolution, parent_element, w_scale, draw_tile_ids);
            }
            tile_index += 1;
        }
                
        //
        // Actions to take after new tiles have been loaded/drawn:
        // (1) remove old tile(s);
        // (2) update filtering UI elements.
        //
        var track = this;
        var intervalId = setInterval(function() {
            // Only do stuff if all tile drawing is complete:
            if (obj_length(draw_tile_ids) === 0) {
                // All drawing has finished; if there is more than one child in the content div, 
                // remove the first one, which is the oldest.
                if ( track.content_div.children().length > 1 ) {
                    track.content_div.children( ":first" ).remove();
                }
                    
                // Update filtering UI.
                for (var f = 0; f < track.filters.length; f++) {
                    track.filters[f].update_ui_elt();
                }
                // Method complete; do not call it again.
                clearInterval(intervalId);
            }
        }, 50);
        
        //
        // Draw child tracks.
        //
        for (var i = 0; i < this.child_tracks.length; i++) {
            this.child_tracks[i].draw(force);
        }
    }, delayed_draw: function(track, key, low, high, tile_index, resolution, parent_element, w_scale, draw_tile_ids) {
        // Put a 50ms delay on drawing so that if the user scrolls fast, we don't load extra data
        var id = setTimeout(function() {
            if (low <= track.view.high && high >= track.view.low) {
                var tile_element = track.draw_tile(resolution, tile_index, parent_element, w_scale);
                if (tile_element) {
                    // Store initial canvas in case we need to use it for overview
                    if (!track.initial_canvas && !window.G_vmlCanvasManager) {
                        track.initial_canvas = $(tile_element).clone();
                        var src_ctx = tile_element.get(0).getContext("2d");
                        var tgt_ctx = track.initial_canvas.get(0).getContext("2d");
                        var data = src_ctx.getImageData(0, 0, src_ctx.canvas.width, src_ctx.canvas.height);
                        tgt_ctx.putImageData(data, 0, 0);
                        track.set_overview();
                    }
                    // Add tile to cache and show tile.
                    track.tile_cache.set(key, tile_element);
                    track.show_tile(tile_element, parent_element);
                }
            }
            // Remove setTimeout id.
            delete draw_tile_ids[id];
        }, 50);
        draw_tile_ids[id] = true;
    }, 
    // Show track tile and perform associated actions.
    show_tile: function( tile_element, parent_element ) {
        // Readability.
        var track = this;
        
        // Setup and show tile element.
        parent_element.append( tile_element );
        track.max_height = Math.max( track.max_height, tile_element.height() );
        track.content_div.css("height", track.max_height + "px");
        
        if (track.hidden) { return; }
        
        // Show/hide filters based on whether tile is filterable.
        if ( tile_element.hasClass(FILTERABLE_CLASS) ) {
            show_hide_popupmenu_options(track.popup_menu, "(Show|Hide) filters");
            if (track.filters_visible) {
                track.filtering_div.show();
            }
        } else {
            show_hide_popupmenu_options(track.popup_menu, "(Show|Hide) filters", false);
            track.filtering_div.hide();
        }
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
    // Run track's tool.
    run_tool: function() {
        // Put together params for running tool.
        var url_params = { 
            dataset_id: this.original_dataset_id,
            chrom: this.view.chrom,
            low: this.view.low,
            high: this.view.high,
            tool_id: this.tool.name
        };
        $.extend(url_params, this.tool.get_param_values_dict());
        
        //
        // Create track for tool's output immediately to provide user feedback.
        //
		var 
		    current_track = this,
            // Set name of track to include tool name, parameters, and region used.
		    track_name = url_params.tool_id +
		                 current_track.tool_region_and_parameters_str(url_params.chrom, url_params.low, url_params.high),
		    new_track;
		    
		// TODO: add support for other kinds of tool data tracks.
	    if (current_track.track_type == 'FeatureTrack') {
	        new_track = new ToolDataFeatureTrack(track_name, view, undefined, {}, {}, current_track);    
	    }
		      
		this.add_track(new_track);
		new_track.content_div.text("Starting job.");
		view.has_changes = true;
		
		// Run tool.
		var json_run_tool = function() {
            $.getJSON(run_tool_url, url_params, function(track_data) {
                if (track_data == "no converter") {
                    // No converter available for input datasets, so cannot run tool.
                    new_track.container_div.addClass("error");
                    new_track.content_div.text(DATA_NOCONVERTER);
                }
                else if (track_data.error) {
                    // General error.
                    new_track.container_div.addClass("error");
                    new_track.content_div.text(DATA_CANNOT_RUN_TOOL + track_data.message);
                }
                else if (track_data == "pending") {
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
    this.hidden = true;
    Track.call( this, null, view, view.top_labeltrack );
    TiledTrack.call( this );
    
    this.left_offset = 200;
    this.height_px = 12;
    this.container_div.addClass( "reference-track" );
    this.data_queue = {};
    this.data_cache = new DataCache(CACHED_DATA);
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
            key = resolution + "_" + tile_index;
        
        var canvas = document.createElement("canvas");
        if (window.G_vmlCanvasManager) { G_vmlCanvasManager.initElement(canvas); } // EXCANVAS HACK
        canvas = $(canvas);
        
        var ctx = canvas.get(0).getContext("2d");
        
        if (w_scale > PX_PER_CHAR) {
            if (this.data_cache.get(key) === undefined) {
                this.get_data( resolution, tile_index );
                return;
            }
            
            var seq = this.data_cache.get(key);
            if (seq === null) {
                this.content_div.css("height", "0px");
                return;
            }
            
            canvas.get(0).width = Math.ceil( tile_length * w_scale + this.left_offset);
            canvas.get(0).height = this.height_px;
            
            canvas.css( {
                position: "absolute",
                top: 0,
                left: ( tile_low - this.view.low ) * w_scale - this.left_offset
            });
            
            for (var c = 0, str_len = seq.length; c < str_len; c++) {
                var c_start = Math.round(c * w_scale),
                    gap = Math.round(w_scale / 2);
                ctx.fillText(seq[c], c_start + this.left_offset + gap, 10);
            }
            parent_element.append(canvas);
            return canvas;
        }
        this.content_div.css("height", "0px");
    }
});

var LineTrack = function ( name, view, hda_ldda, dataset_id, prefs ) {
    this.track_type = "LineTrack";
    this.display_modes = ["Histogram", "Line", "Filled", "Intensity"];
    this.mode = "Histogram";
    Track.call( this, name, view, view.viewport_container );
    TiledTrack.call( this );
   
    this.min_height_px = 12; 
    this.max_height_px = 400; 
    this.height_px = 80;
    this.hda_ldda = hda_ldda;
    this.dataset_id = dataset_id;
    this.original_dataset_id = dataset_id;
    this.data_cache = new DataCache(CACHED_DATA);
    this.tile_cache = new Cache(CACHED_TILES_LINE);
    this.prefs = { 'color': 'black', 'min_value': undefined, 'max_value': undefined, 'mode': this.mode };
    this.restore_prefs(prefs);

    // Add control for resizing
    // Trickery here to deal with the hovering drag handle, can probably be
    // pulled out and reused.
    (function( track ){
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
        }).appendTo( track.container_div );
    })(this);
};
$.extend( LineTrack.prototype, TiledTrack.prototype, {
    predraw_init: function() {
        var track = this,
            track_id = track.view.tracks.indexOf(track);
        
        track.vertical_range = undefined;
        $.getJSON( track.data_url, {  stats: true, chrom: track.view.chrom, low: null, high: null,
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
    get_data: function( resolution, position ) {
        var track = this,
            low = position * DENSITY * resolution,
            high = ( position + 1 ) * DENSITY * resolution,
            key = resolution + "_" + position;
        
        if (!track.data_queue[key]) {
            track.data_queue[key] = true;
            /*$.getJSON( track.data_url, {  "chrom": this.view.chrom, 
                                            "low": low, "high": high, "dataset_id": this.dataset_id,
                                            "resolution": this.view.resolution }, function (data) {
                track.data_cache.set(key, data);
                delete track.data_queue[key];
                track.draw();
            });*/
            $.ajax({ 'url': this.data_url, 'dataType': 'json', 
                     'data': {  chrom: this.view.chrom, low: low, high: high, 
                                hda_ldda: this.hda_ldda, dataset_id: this.dataset_id, resolution: this.view.resolution }, 
                success: function (result) {
                    var data = result.data;
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
            key = resolution + "_" + tile_index;
        
        var canvas = document.createElement("canvas");
        if (window.G_vmlCanvasManager) { G_vmlCanvasManager.initElement(canvas); } // EXCANVAS HACK
        canvas = $(canvas);
        
        if (this.data_cache.get(key) === undefined) {
            this.get_data( resolution, tile_index );
            return;
        }
        
        var data = this.data_cache.get(key);
        if (!data) { return; }
        
        canvas.css( {
            position: "absolute",
            top: 0,
            left: ( tile_low - this.view.low ) * w_scale
        });
        
        canvas.get(0).width = Math.ceil( tile_length * w_scale );
        canvas.get(0).height = this.height_px;
        var ctx = canvas.get(0).getContext("2d"),
            in_path = false,
            min_value = this.prefs.min_value,
            max_value = this.prefs.max_value,
            vertical_range = this.vertical_range,
            total_frequency = this.total_frequency,
            height_px = this.height_px,
            mode = this.mode;

        // Pixel position of 0 on the y axis
        var y_zero = Math.round( height_px + min_value / vertical_range * height_px );

        // Line at 0.0
        ctx.beginPath();
        ctx.moveTo( 0, y_zero );
        ctx.lineTo( tile_length * w_scale, y_zero );
        // ctx.lineWidth = 0.5;
        ctx.fillStyle = "#aaa";
        ctx.stroke();
            
        ctx.beginPath();
        ctx.fillStyle = this.prefs.color;
        var x_scaled, y, delta_x_px;
        if (data.length > 1) {
            delta_x_px = Math.ceil((data[1][0] - data[0][0]) * w_scale);
        } else {
            delta_x_px = 10;
        }
        for (var i = 0, len = data.length; i < len; i++) {
            x_scaled = Math.round((data[i][0] - tile_low) * w_scale);
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
                // console.log(y, this.min_value, this.vertical_range, (y - this.min_value) / this.vertical_range * this.height_px);
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
        parent_element.append(canvas);
        return canvas;
    }, gen_options: function(track_id) {
        var container = $("<div />").addClass("form-row");
        
        var color = 'track_' + track_id + '_color',
            color_label = $('<label />').attr("for", color).text("Color:"),
            color_input = $('<input />').attr("id", color).attr("name", color).val(this.prefs.color),
            minval = 'track_' + track_id + '_minval',
            min_label = $('<label></label>').attr("for", minval).text("Min value:"),
            min_val = (this.prefs.min_value === undefined ? "" : this.prefs.min_value),
            min_input = $('<input></input>').attr("id", minval).val(min_val),
            maxval = 'track_' + track_id + '_maxval',
            max_label = $('<label></label>').attr("for", maxval).text("Max value:"),
            max_val = (this.prefs.max_value === undefined ? "" : this.prefs.max_value),
            max_input = $('<input></input>').attr("id", maxval).val(max_val);

        return container.append(min_label).append(min_input).append(max_label)
                .append(max_input).append(color_label).append(color_input);
    }, update_options: function(track_id) {
        var min_value = $('#track_' + track_id + '_minval').val(),
            max_value = $('#track_' + track_id + '_maxval').val(),
            color = $('#track_' + track_id + '_color').val();
        if ( min_value !== this.prefs.min_value || max_value !== this.prefs.max_value || color !== this.prefs.color ) {
            this.prefs.min_value = parseFloat(min_value);
            this.prefs.max_value = parseFloat(max_value);
            this.prefs.color = color;
            this.vertical_range = this.prefs.max_value - this.prefs.min_value;
            // Update the y-axis
            $('#linetrack_' + track_id + '_minval').text(this.prefs.min_value);
            $('#linetrack_' + track_id + '_maxval').text(this.prefs.max_value);
            this.tile_cache.clear();
            this.draw();
        }
    }
});

var FeatureTrack = function (name, view, hda_ldda, dataset_id, prefs, filters, tool, parent_track) {
    this.track_type = "FeatureTrack";
    this.display_modes = ["Auto", "Dense", "Squish", "Pack"];
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
    this.vertical_detail_px = 10;
    this.vertical_nodetail_px = 3;
    this.summary_draw_height = 30;
    this.default_font = "9px Monaco, Lucida Console, monospace";
    this.inc_slots = {};
    this.data_queue = {};
    this.s_e_by_tile = {};
    this.tile_cache = new Cache(CACHED_TILES_FEATURE);
    this.data_cache = new DataCache(20);
    this.left_offset = 200;
    
    this.prefs = { 'block_color': '#444', 'label_color': 'black', 'show_counts': true };
    this.restore_prefs(prefs);
};
$.extend( FeatureTrack.prototype, TiledTrack.prototype, {
    get_data: function( low, high ) {
        var track = this,
            key = low + '_' + high;
        
        if (!track.data_queue[key]) {
            track.data_queue[key] = true;
            $.getJSON( track.data_url, {  chrom: track.view.chrom, 
                                          low: low, high: high, hda_ldda: track.hda_ldda, dataset_id: track.dataset_id,
                                          resolution: this.view.resolution, mode: this.mode }, function (result) {
                track.data_cache.set_data(low, high, track.mode, result);
                // console.log("datacache", track.data_cache.get(key));
                delete track.data_queue[key];
                track.draw();
            });
        }
    },
    //
    // Place features in slots for drawing (i.e. pack features).
    // this.inc_slots[level] is created in this method. this.inc_slots[level]
    // is a dictionary of slotted features; key is feature uid, value is a dictionary
    // with keys 'slot' and 'text'.
    // Returns the number of slots used to pack features.
    //
    incremental_slots: function(level, features, no_detail, mode) {
        //
        // Get/create incremental slots for level. If display mode changed,
        // need to create new slots.
        //
        var inc_slots = this.inc_slots[level];
        if (!inc_slots || (inc_slots.mode !== mode)) {
            inc_slots = {};
            inc_slots.w_scale = level;
            inc_slots.mode = mode;
            this.inc_slots[level] = inc_slots;
            this.s_e_by_tile[level] = {};
        }
        
        //
        // If feature already exists in slots (from previously seen tiles), use the same slot,
        // otherwise if not seen, add to "undone" list for slot calculation.
        //
        var w_scale = inc_slots.w_scale,
            undone = [], slotted = [],
            highest_slot = 0, // To measure how big to draw canvas
            max_low = this.view.max_low;
        // TODO: Should calculate zoom tile index, which will improve performance
        // by only having to look at a smaller subset
        // if (this.s_e_by_tile[0] === undefined) { this.s_e_by_tile[0] = []; }
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
        
        //
        // Slot unslotted features.
        //
        var s_e_by_tile = this.s_e_by_tile[level];
        
        // Find the first slot s/t current feature doesn't overlap any other features in that slot.
        // Returns -1 if no slot was found.
        var find_slot = function(f_start, f_end) {
            var found;
            for (var slot_num = 0, slot; slot_num <= MAX_FEATURE_DEPTH; slot_num++) {
                found = true;
                slot = s_e_by_tile[slot_num];
                if (slot !== undefined) {
                    // Iterate through features already in slot to see if current feature will fit.
                    for (var k = 0, k_len = slot.length; k < k_len; k++) {
                        var s_e = slot[k];
                        if (f_end > s_e[0] && f_start < s_e[1]) {
                            found = false;
                            break;
                        }
                    }
                }
                if (found) {
                    break;
                }
            }
            
            if (found) {
                return slot_num;
            }
            else {
                return -1;
            }
        };
        
        // Do slotting.
        for (var i = 0, len = undone.length; i < len; i++) {
            var feature = features[undone[i]],
                feature_uid = feature[0],
                feature_start = feature[1],
                feature_end = feature[2],
                feature_name = feature[3],
                // Where to start, end drawing on screen.
                f_start = Math.floor( (feature_start - max_low) * w_scale ),
                f_end = Math.ceil( (feature_end - max_low) * w_scale ),
                text_len = CONTEXT.measureText(feature_name).width,
                text_align;
            
            // Update start, end drawing locations to include feature name.
            // Try to put the name on the left, if not, put on right.
            if (feature_name !== undefined && !no_detail) {
                if (f_start - text_len < 0) {
                    f_end += text_len;
                    text_align = "left";
                } else {
                    f_start -= text_len;
                    text_align = "right";
                }
            }
                        
            // Find slot.
            var slot_num = find_slot(f_start, f_end);
            if (slot_num < 0) {
                /*
                TODO: this is not yet working --
                console.log(feature_uid, "looking for slot with text on the right");
                // Slot not found. If text was on left, try on right and see
                // if slot can be found.
                // TODO: are there any checks we need to do to ensure that text
                // will fit on tile?
                if (text_align == "left") {
                    f_start -= text_len;
                    f_end -= text_len;
                    text_align = "right";
                    slot_num = find_slot(f_start, f_end);
                }
                if (slot_num >= 0) {
                    console.log(feature_uid, "found slot with text on the right");
                }
                */
            }
            
            // Do slotting.
            if (slot_num >= 0) {
                // Add current feature to slot.
                slot = s_e_by_tile[slot_num];
                if (slot === undefined) { 
                    slot = s_e_by_tile[slot_num] = [];
                }
                slot.push([f_start, f_end]);
                inc_slots[feature_uid] = slot_num;
                highest_slot = Math.max(highest_slot, slot_num);
            }
            else {
                // TODO: remove this warning when skipped features are handled.
                // Show warning for skipped feature.
                // console.log("WARNING: not displaying feature"); // , feature_uid, f_start, f_end);
            }
        }
        
        // Debugging: view slots data.
        /*
        for (var i = 0; i < MAX_FEATURE_DEPTH; i++) {
            var slot = s_e_by_tile[i];
            if (slot !== undefined) {
                console.log(i, "*************");
                for (var k = 0, k_len = slot.length; k < k_len; k++) {
                    console.log("\t", slot[k][0], slot[k][1]);
                }
            }
        }
        */
        return highest_slot;
    },
    // Right now this function is used only for rendering BAM reads.
    rect_or_text: function( ctx, w_scale, tile_low, tile_high, feature_start, cigar, orig_seq, y_center ) {
        ctx.textAlign = "center";
        var draw_offset = 0, 
            seq_offset = 0,
            gap = Math.round(w_scale / 2);
        
        for (var cig_id = 0, len = cigar.length; cig_id < len; cig_id++) {
            var cig = cigar[cig_id],
                cig_op = "MIDNSHP=X"[cig[0]],
                cig_len = cig[1];
            
            if (cig_op === "H" || cig_op === "S") {
                // Go left if it clips
                draw_offset -= cig_len;
            }
            var seq_start = feature_start + draw_offset,
                s_start = Math.floor( Math.max(0, (seq_start - tile_low) * w_scale) ),
                s_end = Math.floor( Math.max(0, (seq_start + cig_len - tile_low) * w_scale) );
                
            switch (cig_op) {
                case "H": // Hard clipping
                    // TODO: draw anything?
                    // Sequence not present, so do not increment seq_offset.
                    break;
                case "S": // Soft clipping
                case "M": // Match
                case "=":
                    var seq = orig_seq.slice(seq_offset, seq_offset + cig_len);
                    if ( (this.mode === "Pack" || this.mode === "Auto") && orig_seq !== undefined && w_scale > PX_PER_CHAR) {
                        ctx.fillStyle = this.prefs.block_color;
                        ctx.fillRect(s_start + this.left_offset, y_center + 1, s_end - s_start, 9);
                        ctx.fillStyle = CONNECTOR_COLOR;
                        for (var c = 0, str_len = seq.length; c < str_len; c++) {
                            if (seq_start + c >= tile_low && seq_start + c <= tile_high) {
                                var c_start = Math.floor( Math.max(0, (seq_start + c - tile_low) * w_scale) );
                                ctx.fillText(seq[c], c_start + this.left_offset + gap, y_center + 9);
                            }
                        }
                    } else {
                        ctx.fillStyle = this.prefs.block_color;
                        // TODO: This is a pretty hack-ish way to fill rectangle based on mode.
                        ctx.fillRect(s_start + this.left_offset, y_center + (this.mode != "Dense" ? 4 : 5), s_end - s_start, (this.mode != "Dense" ? 3 : 1) );
                    }
                    seq_offset += cig_len;
                    break;
                case "N": // Skipped bases
                    ctx.fillStyle = CONNECTOR_COLOR;
                    ctx.fillRect(s_start + this.left_offset, y_center + 5, s_end - s_start, 1);
                    //ctx.dashedLine(s_start + this.left_offset, y_center + 5, this.left_offset + s_end, y_center + 5);
                    break;
                case "D": // Deletion
                    ctx.fillStyle = "red";
                    ctx.fillRect(s_start + this.left_offset, y_center + 4, s_end - s_start, 3);
                    break;
                case "P": // TODO: No good way to draw insertions/padding right now, so ignore
                    // Sequences not present, so do not increment seq_offset.
                    break;
                case "I":
                    seq_offset += cig_len;
                    break;
                case "X":
                    // TODO: draw something?
                    seq_offset += cig_len;
                    break;
            }
            draw_offset += cig_len;
        }
    },
    draw_tile: function( resolution, tile_index, parent_element, w_scale ) {
        var tile_low = tile_index * DENSITY * resolution,
            tile_high = ( tile_index + 1 ) * DENSITY * resolution,
            tile_span = tile_high - tile_low;
        // console.log("drawing " + tile_low + " to " + tile_high);

        /*for (var k in this.data_cache.obj_cache) {
            var k_split = k.split("_"), k_low = k_split[0], k_high = k_split[1];
            if (k_low <= tile_low && k_high >= tile_high) {
                data = this.data_cache.get(k);
                break;
            }
        }*/
        var result = this.data_cache.get_data(tile_low, tile_high, this.mode);
        
        if (result === undefined || result === "pending" || 
            (this.mode !== "Auto" && result.dataset_type === "summary_tree")) {
            this.data_queue[ [tile_low, tile_high] ] = true;
            this.get_data(tile_low, tile_high);
            return;
        }
        
        var width = Math.ceil( tile_span * w_scale ),
            label_color = this.prefs.label_color,
            block_color = this.prefs.block_color,
            mode = this.mode,
            min_height = 25,
            no_detail = (mode === "Squish") || (mode === "Dense") && (mode !== "Pack") || (mode === "Auto" && (result.extra_info === "no_detail")),
            left_offset = this.left_offset,
            slots, required_height, y_scale;
        
        var canvas = document.createElement("canvas");
        if (window.G_vmlCanvasManager) { G_vmlCanvasManager.initElement(canvas); } // EXCANVAS HACK
        canvas = $(canvas);
        
        if (result.dataset_type === "summary_tree") {
            required_height = this.summary_draw_height;
        } else if (mode === "Dense") {
            required_height = min_height;
            y_scale = 10;
        } else {
            // Calculate new slots incrementally for this new chunk of data and update height if necessary
            y_scale = ( no_detail ? this.vertical_nodetail_px : this.vertical_detail_px );
            var inc_scale = (w_scale < 0.0001 ? 1/this.view.zoom_res : w_scale);
            required_height = this.incremental_slots( inc_scale, result.data, no_detail, mode ) * y_scale + min_height;
            slots = this.inc_slots[inc_scale];
        }
        
        canvas.css({
            position: "absolute",
            top: 0,
            left: ( tile_low - this.view.low ) * w_scale - left_offset
        });
        canvas.get(0).width = width + left_offset;
        canvas.get(0).height = required_height;
        parent_element.parent().css("height", Math.max(this.height_px, required_height) + "px");
        // console.log(( tile_low - this.view.low ) * w_scale, tile_index, w_scale);
        var ctx = canvas.get(0).getContext("2d");
        ctx.fillStyle = block_color;
        ctx.font = this.default_font;
        ctx.textAlign = "right";
        this.container_div.find(".yaxislabel").remove();
        
        //
        // Draw summary tree. If tree is drawn, canvas is returned.
        //
        if (result.dataset_type == "summary_tree") {            
            var points = result.data,
                max = result.max,
                delta_x_px = Math.ceil(result.delta * w_scale);
            
            var max_label = $("<div />").addClass('yaxislabel');
            max_label.text(max);
            
            max_label.css({ position: "absolute", top: "22px", left: "10px" });
            max_label.prependTo(this.container_div);
                
            for ( var i = 0, len = points.length; i < len; i++ ) {
                var x = Math.floor( (points[i][0] - tile_low) * w_scale );
                var y = points[i][1];
                
                if (!y) { continue; }
                var y_px = y / max * this.summary_draw_height;
                
                ctx.fillStyle = "black";
                ctx.fillRect(x + left_offset, this.summary_draw_height - y_px, delta_x_px, y_px);
                
                if (this.prefs.show_counts && ctx.measureText(y).width < delta_x_px) {
                    ctx.fillStyle = "#bbb";
                    ctx.textAlign = "center";
                    ctx.fillText(y, x + left_offset + (delta_x_px/2), this.summary_draw_height - 5);
                }
            }
            parent_element.append( canvas );
            return canvas;
        }
        
        //
        // Show message. If there is a message, return canvas.
        //
        if (result.message) {
            canvas.css({
                border: "solid red",
                "border-width": "2px 2px 2px 0px"            
            });
            ctx.fillStyle = "red";
            ctx.textAlign = "left";
            ctx.fillText(result.message, 100 + left_offset, y_scale);
            return canvas;
        }
        
        //        
        // If tile is filterable, add class to canvas.
        //
        for (var f = 0; f < this.filters.length; f++) {
            if (this.filters[f].applies_to(result.data[0])) {
                canvas.addClass(FILTERABLE_CLASS);
                break;
            }
        }
        
        //
        // Draw data points.
        //
        var data = result.data;
        var j = 0;
        for (var i = 0, len = data.length; i < len; i++) {
            var feature = data[i],
                feature_uid = feature[0],
                feature_start = feature[1],
                feature_end = feature[2],
                feature_name = feature[3];
            
            // TODO: why is this necessary? Without explicitly short-circuiting it, it prevents dense mode from rendering.
            if (this.mode != "Dense" && slots[feature_uid] === undefined) {
                continue;
            }
                
            // Apply filters to feature.
            var hide_feature = false;
            var filter;
            for (var f = 0; f < this.filters.length; f++) {
                filter = this.filters[f];
                filter.update_attrs( feature );
                if ( !filter.keep( feature ) ) {
                    hide_feature = true;
                    break;
                }
            }
            if (hide_feature) {
                continue;
            }
                
            if (feature_start <= tile_high && feature_end >= tile_low) {
                // All features need a start, end, and vertical center.
                var f_start = Math.floor( Math.max(0, (feature_start - tile_low) * w_scale) ),
                    f_end   = Math.ceil( Math.min(width, Math.max(0, (feature_end - tile_low) * w_scale)) ),
                    y_center = (mode === "Dense" ? 1 : (1 + slots[feature_uid])) * y_scale;                
                var thickness, y_start, thick_start = null, thick_end = null;
                
                // BAM/read drawing.
                if (result.dataset_type === "bai") {
                    ctx.fillStyle = block_color;
                    if (feature[5] instanceof Array) {
                        // Read is paired.
                        var b1_start = Math.floor( Math.max(0, (feature[4][0] - tile_low) * w_scale) ),
                            b1_end   = Math.ceil( Math.min(width, Math.max(0, (feature[4][1] - tile_low) * w_scale)) ),
                            b2_start = Math.floor( Math.max(0, (feature[5][0] - tile_low) * w_scale) ),
                            b2_end   = Math.ceil( Math.min(width, Math.max(0, (feature[5][1] - tile_low) * w_scale)) );

                        // Draw left/forward read.
                        if (feature[4][1] >= tile_low && feature[4][0] <= tile_high && feature[4][2]) {
                            this.rect_or_text(ctx, w_scale, tile_low, tile_high, feature[4][0], feature[4][2], feature[4][3], y_center);
                        }
                        // Draw right/reverse read.
                        if (feature[5][1] >= tile_low && feature[5][0] <= tile_high && feature[5][2]) {
                            this.rect_or_text(ctx, w_scale, tile_low, tile_high, feature[5][0], feature[5][2], feature[5][3], y_center);
                        }
                        // Draw connector.
                        if (b2_start > b1_end) {
                            ctx.fillStyle = CONNECTOR_COLOR;
                            //ctx.fillRect(b1_end + left_offset, y_center + 5, b2_start - b1_end, 1);
                            ctx.dashedLine(b1_end + left_offset, y_center + 5, left_offset + b2_start, y_center + 5);
                        }
                    } else {
                        // Read is single.
                        ctx.fillStyle = block_color;
                        this.rect_or_text(ctx, w_scale, tile_low, tile_high, feature_start, feature[4], feature[5], y_center);
                    }
                    if (mode !== "Dense" && !no_detail && feature_start > tile_low) {
                        // Draw label.
                        ctx.fillStyle = this.prefs.label_color;
                        if (tile_index === 0 && f_start - ctx.measureText(feature_name).width < 0) {
                            ctx.textAlign = "left";
                            ctx.fillText(feature_name, f_end + 2 + left_offset, y_center + 8);
                        } else {
                            ctx.textAlign = "right";
                            ctx.fillText(feature_name, f_start - 2 + left_offset, y_center + 8);
                        }
                        ctx.fillStyle = block_color;
                    }
                }
                // Interval index drawing.
                else if (result.dataset_type === "interval_index") {
                    // console.log(feature_uid, feature_start, feature_end, f_start, f_end, y_center);
                    if (no_detail) {
                        ctx.fillStyle = block_color;
                        ctx.fillRect(f_start + left_offset, y_center + 5, f_end - f_start, 1);
                    } else {
                        // Showing labels, blocks, details.
                        var feature_strand = feature[5],
                            feature_ts = feature[6],
                            feature_te = feature[7],
                            feature_blocks = feature[8];
                        
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
                                ctx.fillStyle = block_color;
                            }                            
                        }                        
                    }
                } else if (result.dataset_type === 'vcf') {
                    // VCF track.
                    if (no_detail) {
                        ctx.fillStyle = block_color;
                        ctx.fillRect(f_start + left_offset, y_center + 5, f_end - f_start, 1);
                    }
                    else { // Show blocks, labels, etc.                        
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
                            if (tile_index === 0 && f_start - ctx.measureText(feature_name).width < 0) {
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
                j++;
            }
        }
        return canvas;
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

var ReadTrack = function (name, view, hda_ldda, dataset_id, prefs, filters) {
    FeatureTrack.call(this, name, view, hda_ldda, dataset_id, prefs, filters);
    this.track_type = "ReadTrack";
    this.vertical_detail_px = 10;
    this.vertical_nodetail_px = 5;
};
$.extend( ReadTrack.prototype, TiledTrack.prototype, FeatureTrack.prototype, {});

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

$.extend( ToolDataFeatureTrack.prototype, TiledTrack.prototype, FeatureTrack.prototype, {
    /**
     * For this track type, the predraw init sets up postdraw init. 
     */
    predraw_init: function() {        
        // Postdraw init: once data has been fetched, reset data url, wait time and start indexing.
        var track = this; 
        var post_init = function() {
            if (track.data_cache.size() == 0) {
                // Track still drawing initial data, so do nothing.
                setTimeout(post_init, 300);
            }
            else {
                // Track drawing done: reset dataset check, data URL, wait time and get dataset state to start
                // indexing.
                track.data_url = default_data_url;
                track.data_query_wait = DEFAULT_DATA_QUERY_WAIT;
                track.dataset_state_url = converted_datasets_state_url;
                $.getJSON(track.dataset_state_url, { dataset_id : track.dataset_id }, function(track_data) {});
            }
        };
        post_init();
    }
});


