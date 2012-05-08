/* Trackster
    2010-2011: James Taylor, Kanwei Li, Jeremy Goecks
*/

var class_module = function(require, exports) {
    
// Module is a placeholder for a more complete inheritence approach
    
/** Simple extend function for inheritence */
var extend = function() {
    var target = arguments[0];
    for ( var i = 1; i < arguments.length; i++ ) {
        var other = arguments[i];
        for ( key in other ) {
            target[key] = other[key];
        }
    }
    return target;
};

exports.extend = extend;

// end class_module encapsulation
};

/**
 * Provides support for server-state based deferred. Server is repeatedly polled, and when
 * condition is met, deferred is resolved.
 */
var server_state_deferred = function(url, url_params, interval, success_fn) {
    var deferred = $.Deferred(),
        go = function() {
            $.getJSON(url, url_params, function(result) {
                if (success_fn(result)) {
                    // Result is good, so resolve.
                    deferred.resolve(result);
                }
                else {
                    // Result not good, try again.
                    setTimeout(go, interval);
                }
            });
        };
    go();
    return deferred;
};

/**
 * Find browser's requestAnimationFrame method or fallback on a setTimeout 
 */
var requestAnimationFrame = (function(){
    return  window.requestAnimationFrame       || 
            window.webkitRequestAnimationFrame || 
            window.mozRequestAnimationFrame    || 
            window.oRequestAnimationFrame      || 
            window.msRequestAnimationFrame     || 
            function( callback, element ) {
                window.setTimeout(callback, 1000 / 60);
            };
})();

/**
 * Compute the type of overlap between two regions. They are assumed to be on the same chrom/contig.
 * The overlap is computed relative to the second region; hence, OVERLAP_START indicates that the first
 * region overlaps the start (but not the end) of the second region.
 */
var BEFORE = 1001, CONTAINS = 1002, OVERLAP_START = 1003, OVERLAP_END = 1004, CONTAINED_BY = 1005, AFTER = 1006;
var compute_overlap = function(first_region, second_region) {
    var 
        first_start = first_region[0], first_end = first_region[1],
        second_start = second_region[0], second_end = second_region[1],
        overlap;
    if (first_start < second_start) {
        if (first_end < second_start) {
            overlap = BEFORE;
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
            overlap = AFTER;
        }
        else if (first_end <= second_end) {
            overlap = CONTAINED_BY;
        }
        else {
            overlap = OVERLAP_END;
        }
    }
    
    return overlap;
};

/**
 * Returns true if regions overlap.
 */
var is_overlap = function(first_region, second_region) {
    var overlap = compute_overlap(first_region, second_region);
    return (overlap !== BEFORE && overlap !== AFTER);
};

/**
 * Helper to determine if object is jQuery deferred.
 */
var is_deferred = function ( d ) {
    return ( 'isResolved' in d );
};

/**
 * Returns a random color in hexadecimal format that is sufficiently different from a single color
 * or set of colors.
 * @param colors a color or list of colors in the format '#RRGGBB'
 */
var get_random_color = function(colors) {
    // Default for colors is white.
    if (!colors) { colors = "#ffffff" };
    
    // If needed, create list of colors.
    if ( typeof(colors) === "string" ) {
        colors = [ colors ];
    }
    
    // Convert colors to numbers.
    for (var i = 0; i < colors.length; i++) {
        colors[i] = parseInt( colors[i].slice(1), 16 );
    }
    
    // -- Perceived brightness and difference formulas are from 
    // -- http://www.w3.org/WAI/ER/WD-AERT/#color-contrast
    
    // Compute perceived color brightness (based on RGB-YIQ transformation):
    var brightness = function(r, g, b) {
        return ( (r * 299) + (g * 587) + (b * 114) ) / 1000;
    };
    
    // Compute color difference:
    var difference = function(r1, g1, b1, r2, g2, b2) {
        return ( Math.max(r1, r2) - Math.min(r1, r2) ) + 
               ( Math.max(g1, g2) - Math.min(g1, g2) ) + 
               ( Math.max(b1, b2) - Math.min(b1, b2) );
    };
    
    // Create new random color.
    var new_color, nr, ng, nb,
        other_color, or, og, ob,
        n_brightness, o_brightness,
        diff, ok = false,
        num_tries = 0;
    do {
        // New color is never white b/c random in [0,1)
        new_color = Math.round( Math.random() * 0xffffff );
        nr = ( new_color & 0xff0000 ) >> 16;
        ng = ( new_color & 0x00ff00 ) >> 8;
        nb = new_color & 0x0000ff;
        n_brightness = brightness(nr, ng, nb);
        ok = true;
        for (var i = 0; i < colors.length; i++) {
            other_color = colors[i];
            or = ( other_color & 0xff0000 ) >> 16;
            og = ( other_color & 0x00ff00 ) >> 8;
            ob = other_color & 0x0000ff;
            o_brightness = brightness(or, og, ob);
            diff = difference(nr, ng, nb, or, og, ob);
            // These thresholds may need to be adjusted. Brightness difference range is 125; 
            // color difference range is 500.
            if ( ( Math.abs(n_brightness - o_brightness) < 40 ) ||
                 ( diff < 200 ) ) {
                ok = false;
                break;         
            }
        }
        
        num_tries++
    } while (!ok && num_tries <= 10 );
    
    // Add 0x1000000 to left pad number with 0s.
    return '#' + ( 0x1000000 + new_color ).toString(16).substr(1,6);
};

/**
 * Creates an action icon.
 */
var create_action_icon =  function(title, css_class, on_click_fn) {
    return $("<a/>").attr("href", "javascript:void(0);").attr("title", title)
                    .addClass("icon-button").addClass(css_class).tipsy( {gravity: 's'} )
                    .click(on_click_fn);
};

// Encapsulate -- anything to be availabe outside this block is added to exports
var trackster_module = function(require, exports) {

var extend = require('class').extend,
    slotting = require('slotting'),
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
        image.src = galaxy_paths.attributes.image_path + path;
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
 * Dictionary of HTML element-JavaScript object relationships.
 */
// TODO: probably should separate moveable objects from containers.
var html_elt_js_obj_dict = {};

/**
 * Designates an HTML as a container.
 */
var is_container = function(element, obj) {
    html_elt_js_obj_dict[element.attr("id")] = obj;
};

/** 
 * Make `element` moveable within parent and sibling elements by dragging `handle` (a selector).
 * Function manages JS objects, containers as well.
 *
 * @param element HTML element to make moveable
 * @param handle_class classname that denotes HTML element to be used as handle
 * @param container_selector selector used to identify possible containers for this element
 * @param element_js_obj JavaScript object associated with element; used 
 */
var moveable = function(element, handle_class, container_selector, element_js_obj) {
    // HACK: set default value for container selector.
    container_selector = ".group";
    var css_border_props = {};

    // Register element with its object.
    html_elt_js_obj_dict[element.attr("id")] = element_js_obj;
    
    // Need to provide selector for handle, not class.
    element.bind( "drag", { handle: "." + handle_class, relative: true }, function ( e, d ) {
        var element = $(this);
        var 
            parent = $(this).parent(),
            children = parent.children(),
            this_obj = html_elt_js_obj_dict[$(this).attr("id")],
            child,
            container,
            top,
            bottom,
            i;
            
        //
        // Enable three types of dragging: (a) out of container; (b) into container; 
        // (c) sibling movement, aka sorting. Handle in this order for simplicity.
        //
        
        // Handle dragging out of container.
        container = $(this).parents(container_selector);
        if (container.length !== 0) {
            top = container.position().top;
            bottom = top + container.outerHeight();
            if (d.offsetY < top) {
                // Moving above container.
                $(this).insertBefore(container);
                var cur_container = html_elt_js_obj_dict[container.attr("id")];
                cur_container.remove_drawable(this_obj);
                cur_container.container.add_drawable_before(this_obj, cur_container);
                return;
            }
            else if (d.offsetY > bottom) {
                // Moving below container.
                $(this).insertAfter(container);
                var cur_container = html_elt_js_obj_dict[container.attr("id")];
                cur_container.remove_drawable(this_obj);
                cur_container.container.add_drawable(this_obj);
                return;
            }            
        }
        
        // Handle dragging into container. Child is appended to container's content_div.
        container = null;
        for ( i = 0; i < children.length; i++ ) {
            child = $(children.get(i));
            top = child.position().top;
            bottom = top + child.outerHeight();
            // Dragging into container if child is a container and offset is inside container.
            if ( child.is(container_selector) && this !== child.get(0) && 
                 d.offsetY >= top && d.offsetY <= bottom ) {
                // Append/prepend based on where offsetY is closest to and return.
                if (d.offsetY - top < bottom - d.offsetY) {
                    child.find(".content-div").prepend(this);
                }
                else {
                    child.find(".content-div").append(this);
                }
                // Update containers. Object may not have container if it is being moved quickly.
                if (this_obj.container) {
                    this_obj.container.remove_drawable(this_obj);                    
                }
                html_elt_js_obj_dict[child.attr("id")].add_drawable(this_obj);
                return;
            }
        }

        // Handle sibling movement, aka sorting.
        
        // Determine new position
        var child;
        for ( i = 0; i < children.length; i++ ) {
            child = $(children.get(i));
            if ( d.offsetY < child.position().top &&
                 // Cannot move tracks above reference track or intro div.
                 !(child.hasClass("reference-track") || child.hasClass("intro")) ) {
                break;
            }
        }
                
        // If not already in the right place, move. Need 
        // to handle the end specially since we don't have 
        // insert at index
        if ( i === children.length ) {
            if ( this !== children.get(i - 1) ) {
                parent.append(this);
                html_elt_js_obj_dict[parent.attr("id")].move_drawable(this_obj, i);
            }
        }
        else if ( this !== children.get(i) ) {
            $(this).insertBefore( children.get(i) );
            // Need to adjust insert position if moving down because move is changing 
            // indices of all list items.
            html_elt_js_obj_dict[parent.attr("id")].move_drawable(this_obj, (d.deltaY > 0 ? i-1 : i) );
        }
    }).bind("dragstart", function() {
        css_border_props["border-top"] = element.css("border-top");
        css_border_props["border-bottom"] = element.css("border-bottom");
        $(this).css({
            "border-top": "1px solid blue",
            "border-bottom": "1px solid blue"
        });
    }).bind("dragend", function() {
        $(this).css(css_border_props);
    });
};

// TODO: do we need to export?
exports.moveable = moveable;

/**
 * Init constants & functions used throughout trackster.
 */
var 
    // Minimum height of a track's contents; this must correspond to the .track-content's minimum height.
    MIN_TRACK_HEIGHT = 16,
    // FIXME: font size may not be static
    CHAR_HEIGHT_PX = 9,
    // Padding at the top of tracks for error messages
    ERROR_PADDING = 20,
    // Maximum number of rows un a slotted track
    MAX_FEATURE_DEPTH = 100,
    // Minimum width for window for squish to be used.
    MIN_SQUISH_VIEW_WIDTH = 12000,
    
    // Other constants.
    
    // Number of pixels per tile, not including left offset.
    TILE_SIZE = 400,
    DEFAULT_DATA_QUERY_WAIT = 5000,
    // Maximum number of chromosomes that are selectable at any one time.
    MAX_CHROMS_SELECTABLE = 100,
    DATA_ERROR = "There was an error in indexing this dataset. ",
    DATA_NOCONVERTER = "A converter for this dataset is not installed. Please check your datatypes_conf.xml file.",
    DATA_NONE = "No data for this chrom/contig.",
    DATA_PENDING = "Preparing data. This is very fast for a small dataset but can take a long time for a large dataset. \
                    If visualization is saved and closed, preparation will continue in the background.",
    DATA_CANNOT_RUN_TOOL = "Tool cannot be rerun: ",
    DATA_LOADING = "Loading data...",
    DATA_OK = "Ready for display",
    TILE_CACHE_SIZE = 10,
    DATA_CACHE_SIZE = 20;
    
/**
 * Round a number to a given number of decimal places.
 */
function round(num, places) {
    // Default rounding is to integer.
    if (!places) {
        places = 0;
    }
    
    var val = Math.pow(10, places);
    return Math.round(num * val) / val;
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
            if (this.obj_cache[key].stale) {
                // Object is stale, so remove key and object.
                this.key_ary.splice(index, 1);
                delete this.obj_cache[key];
            }
            else {
                this.move_key_to_end(key, index);
            }
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
var DataManager = function(num_elements, track) {
    Cache.call(this, num_elements);
    this.track = track;
};
extend(DataManager.prototype, Cache.prototype, {
    /**
     * Load data from server; returns AJAX object so that use of Deferred is possible.
     */
    load_data: function(low, high, mode, resolution, extra_params) {
        // Setup data request params.
        var 
            chrom = this.track.view.chrom,
            params = {"chrom": chrom, "low": low, "high": high, "mode": mode, 
                      "resolution": resolution, "dataset_id" : this.track.dataset_id, 
                      "hda_ldda": this.track.hda_ldda};
        $.extend(params, extra_params);
        
        // Add track filters to params.
        if (this.track.filters_manager) {
            var filter_names = [];
            var filters = this.track.filters_manager.filters;
            for (var i = 0; i < filters.length; i++) {
                filter_names.push(filters[i].name);
            }
            params.filter_cols = JSON.stringify(filter_names);
        }
                        
        // Do request.
        var manager = this;
        return $.getJSON(this.track.data_url, params, function (result) {
            manager.set_data(low, high, result);
        });
    },
    /**
     * Get track data.
     */
    get_data: function(low, high, mode, resolution, extra_params) {
        // Debugging:
        //console.log("get_data", low, high, mode);
        /*
        console.log("cache contents:")
        for (var i = 0; i < this.key_ary.length; i++) {
            console.log("\t", this.key_ary[i], this.obj_cache[this.key_ary[i]]);
        }
        */
                
        // Look for entry and return if it's a deferred or if data available is compatible with mode.
        var entry = this.get(low, high);
        if ( entry && 
             ( is_deferred(entry) || this.track.data_and_mode_compatible(entry, mode) ) ) {
            return entry; 
        }

        //
        // Look in cache for data that can be used. Data can be reused if it
        // has the requested data and is not summary tree and has details.
        // TODO: this logic could be improved if the visualization knew whether
        // the data was "index" or "data."
        //        
        var key, split_key, entry_low, entry_high, mode, entry;
        for (var i = 0; i < this.key_ary.length; i++) {
            key = this.key_ary[i];
            split_key = this.split_key(key);
            entry_low = split_key[0];
            entry_high = split_key[1];
        
            if (low >= entry_low && high <= entry_high) {
                // This entry has data in the requested range. Return if data
                // is compatible and can be subsetted.
                var entry = this.obj_cache[key];
                if ( is_deferred(entry) || 
                    ( this.track.data_and_mode_compatible(entry, mode) && this.track.can_subset(entry) ) ) {
                    this.move_key_to_end(key, i);
                    return entry;
                }
            }
        }
                
        // Load data from server. The deferred is immediately saved until the
        // data is ready, it then replaces itself with the actual data.
        entry = this.load_data(low, high, mode, resolution, extra_params);
        this.set_data(low, high, entry);
        return entry;
    },
    /** "Deep" data request; used as a parameter for DataManager.get_more_data() */
    DEEP_DATA_REQ: "deep",
    /** "Broad" data request; used as a parameter for DataManager.get_more_data() */
    BROAD_DATA_REQ: "breadth",
    /**
     * Gets more data for a region using either a depth-first or a breadth-first approach.
     */
    get_more_data: function(low, high, mode, resolution, extra_params, req_type) {
        //
        // Get current data from cache and mark as stale.
        //
        var cur_data = this.get(low, high);
        if ( !(cur_data && this.track.data_and_mode_compatible(cur_data, mode)) ) {
            console.log("ERROR: no current data for: ", this.track, low, high, mode, resolution, extra_params);
            return;
        }
        cur_data.stale = true;
        
        //
        // Set parameters based on request type.
        //
        var query_low = low;
        if (req_type === this.DEEP_DATA_REQ) {
            // Use same interval but set start_val to skip data that's already in cur_data.
            $.extend(extra_params, {start_val: cur_data.data.length + 1});
        }
        else if (req_type === this.BROAD_DATA_REQ) {
            // To get past an area of extreme feature depth, set query low to be after either
            // (a) the maximum high or HACK/FIXME (b) the end of the last feature returned.
            query_low = (cur_data.max_high ? cur_data.max_high : cur_data.data[cur_data.data.length - 1][2]) + 1;
        }
        
        //
        // Get additional data, append to current data, and set new data. Use a custom deferred object
        // to signal when new data is available.
        //
        var 
            data_manager = this,
            new_data_request = this.load_data(query_low, high, mode, resolution, extra_params)
            new_data_available = $.Deferred();
        // load_data sets cache to new_data_request, but use custom deferred object so that signal and data
        // is all data, not just new data.
        this.set_data(low, high, new_data_available);
        $.when(new_data_request).then(function(result) {
            // Update data and message.
            if (result.data) {
                result.data = cur_data.data.concat(result.data);
                if (result.max_low) {
                    result.max_low = cur_data.max_low;
                }
                if (result.message) {
                    // HACK: replace number in message with current data length. Works but is ugly.
                    result.message = result.message.replace(/[0-9]+/, result.data.length);
                }
            }
            data_manager.set_data(low, high, result);
            new_data_available.resolve(result);
        });
        return new_data_available;
    },
    /**
     * Get data from the cache.
     */
    get: function(low, high) {
        return Cache.prototype.get.call( this, this.gen_key(low, high) );
    },
    /**
     * Sets data in the cache.
     */
    set_data: function(low, high, result) {
        return this.set(this.gen_key(low, high), result);
    },
    /**
     * Generate key for cache.
     */
    // TODO: use chrom in key so that (a) data is not thrown away when changing chroms and (b)
    // manager does not need to be cleared when changing chroms.
    // TODO: use resolution in key b/c summary tree data is dependent on resolution -- is this 
    // necessary, i.e. will resolution change but not low/high/mode?
    gen_key: function(low, high) {
        var key = low + "_" + high;
        return key;
    },
    /**
     * Split key from cache into array with format [low, high]
     */
    split_key: function(key) {
        return key.split("_");
    }
});

var ReferenceTrackDataManager = function(num_elements, track, subset) {
    DataManager.call(this, num_elements, track, subset);
};
extend(ReferenceTrackDataManager.prototype, DataManager.prototype, Cache.prototype, {
    get: DataManager.prototype.get,
    load_data: function(low, high, mode, resolution, extra_params) {
        if (resolution > 1) {
            // Now that data is pre-fetched before draw, we don't load reference tracks
            // unless it's at the bottom level.
            return { data: null };
        }
        return DataManager.prototype.load_data.call(this, low, high, mode, resolution, extra_params);
    }
});

/**
 * Drawables hierarchy:
 *
 * Drawable
 *    --> DrawableCollection
 *        --> DrawableGroup
 *        --> View
 *    --> Track
 */

/**
 * Base class for all drawable objects. Drawable objects are associated with a view and live in a 
 * container. They have the following HTML elements and structure:
 *  <container_div>
 *      <header_div>
 *      <content_div>
 *
 * They optionally have a drag handle class. 
 */
var Drawable = function(view, container, obj_dict) {
    if (!Drawable.id_counter) { Drawable.id_counter = 0; }
    this.id = Drawable.id_counter++;
    this.name = obj_dict.name;
    this.view = view;
    this.container = container;
    this.config = new DrawableConfig({
        track: this,
        params: [ 
            { key: 'name', label: 'Name', type: 'text', default_value: this.name }
        ],
        saved_values: obj_dict.prefs,
        onchange: function() {
            this.track.set_name(this.track.config.values.name);
        }
    });
    this.prefs = this.config.values;
    this.drag_handle_class = obj_dict.drag_handle_class;
    this.is_overview = false;
    this.action_icons = {};
    
    // FIXME: this should be a saved setting
    this.content_visible = true;
    
    // Build Drawable HTML and behaviors.
    this.container_div = this.build_container_div();
    this.header_div = this.build_header_div();
    
    if (this.header_div) { 
        this.container_div.append(this.header_div);
        
        // Icons container.
        this.icons_div = $("<div/>").css("float", "left").hide().appendTo(this.header_div);
        this.build_action_icons(this.action_icons_def);
                
        this.header_div.append( $("<div style='clear: both'/>") );
        
        // Suppress double clicks in header so that they do not impact viz.
        this.header_div.dblclick( function(e) { e.stopPropagation(); } );
        
        // Show icons when users is hovering over track.
        var drawable = this;
        this.container_div.hover(
            function() { drawable.icons_div.show(); }, function() { drawable.icons_div.hide(); }
        );
        
        // Needed for floating elts in header.
        $("<div style='clear: both'/>").appendTo(this.container_div);
    }
};

Drawable.prototype.action_icons_def = [
    // Hide/show drawable content.
    // FIXME: make this an odict for easier lookup.
    {
        name: "toggle_icon",
        title: "Hide/show content",
        css_class: "toggle",
        on_click_fn: function(drawable) {
            if ( drawable.content_visible ) {
                drawable.action_icons.toggle_icon.addClass("toggle-expand").removeClass("toggle");
                drawable.hide_contents();
                drawable.content_visible = false;
            } else {
                drawable.action_icons.toggle_icon.addClass("toggle").removeClass("toggle-expand");
                drawable.content_visible = true;
                drawable.show_contents();
            }
        }
    },
    // Edit settings.
    {
        name: "settings_icon",
        title: "Edit settings",
        css_class: "settings-icon",
        on_click_fn: function(drawable) {
            var cancel_fn = function() { hide_modal(); $(window).unbind("keypress.check_enter_esc"); },
                ok_fn = function() { 
                    drawable.config.update_from_form( $(".dialog-box") );
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
            show_modal("Configure", drawable.config.build_form(), {
                "Cancel": cancel_fn,
                "OK": ok_fn
            });
        }
    },
    // Remove.
    {
        name: "remove_icon",
        title: "Remove",
        css_class: "remove-icon",
        on_click_fn: function(drawable) {
            // Tipsy for remove icon must be deleted when drawable is deleted.
            $(".tipsy").remove();
            drawable.remove();
        }
    }
];

extend(Drawable.prototype, {
    init: function() {},
    changed: function() {
        this.view.changed();
    },
    can_draw: function() {
        if (this.enabled && this.content_visible) { 
            return true;
        }
        
        return false;
    },
    request_draw: function() {},
    _draw: function() {},
    /** 
     * Returns representation of object in a dictionary for easy saving. 
     * Use from_dict to recreate object.
     */
    to_dict: function() {},
    update_icons: function() {},
    /**
     * Set drawable name.
     */ 
    set_name: function(new_name) {
        this.old_name = this.name;
        this.name = new_name;
        this.name_div.text(this.name);
    },
    /**
     * Revert track name; currently name can be reverted only once.
     */
    revert_name: function() {
        if (this.old_name) {
            this.name = this.old_name;
            this.name_div.text(this.name);
        }
    },
    /**
     * Remove drawable (a) from its container and (b) from the HTML.
     */
    remove: function() {
        this.changed();
        
        this.container.remove_drawable(this);
        var view = this.view;
        this.container_div.hide(0, function() { 
            $(this).remove();
            // HACK: is there a better way to update the view?
            view.update_intro_div();
        });
    },
    /**
     * Build drawable's container div; this is the parent div for all drawable's elements.
     */ 
    build_container_div: function() {},
    /**
     * Build drawable's header div.
     */
    build_header_div: function() {},
    /**
     * Add an action icon to this object. Appends icon unless prepend flag is specified.
     */
    add_action_icon: function(name, title, css_class, on_click_fn, prepend, hide) {
        var drawable = this;
        this.action_icons[name] = $("<a/>").attr("href", "javascript:void(0);").attr("title", title)
                                           .addClass("icon-button").addClass(css_class).tipsy( {gravity: 's'} )
                                           .click( function() { on_click_fn(drawable); } )
                                           .appendTo(this.icons_div);
        if (hide) {
            this.action_icons[name].hide();
        }
    },
    /**
     * Build drawable's icons div from object's icons_dict.
     */
    build_action_icons: function(action_icons_def) {        
        // Create icons.
        var icon_dict;
        for (var i = 0; i < action_icons_def.length; i++) {
            icon_dict = action_icons_def[i];
            this.add_action_icon(icon_dict.name, icon_dict.title, icon_dict.css_class, 
                                 icon_dict.on_click_fn, icon_dict.prepend, icon_dict.hide);
        }
    },
    /**
     * Update icons.
     */
    update_icons: function() {},
    /**
     * Hide drawable's contents.
     */
    hide_contents: function () {},
    /**
     * Show drawable's contents.
     */
    show_contents: function() {}
});

/**
 * A collection of drawable objects.
 */
var DrawableCollection = function(view, container, obj_dict) {
    Drawable.call(this, view, container, obj_dict);
    
    // Attribute init.
    this.obj_type = obj_dict.obj_type;
    this.drawables = [];
};
extend(DrawableCollection.prototype, Drawable.prototype, {
    /**
     * Unpack and add drawables to the collection.
     */
    unpack_drawables: function(drawables_array) {
        // Add drawables to collection.
        this.drawables = [];
        var drawable;
        for (var i = 0; i < drawables_array.length; i++) {
            drawable = object_from_template(drawables_array[i], this);
            this.add_drawable(drawable);
        }
    },
    /**
     * Init each drawable in the collection.
     */
    init: function() {
        for (var i = 0; i < this.drawables.length; i++) {
            this.drawables[i].init();
        }
    },    
    /**
     * Draw each drawable in the collection.
     */
    _draw: function() {
        for (var i = 0; i < this.drawables.length; i++) {
            this.drawables[i]._draw();
        }
    },
    /** 
     * Returns representation of object in a dictionary for easy saving. 
     * Use from_dict to recreate object.
     */
    to_dict: function() {
        var dictified_drawables = [];
        for (var i = 0; i < this.drawables.length; i++) {
            dictified_drawables.push(this.drawables[i].to_dict());
        }
        return {
            name: this.name,
            prefs: this.prefs,
            obj_type: this.obj_type,
            drawables: dictified_drawables
        };
    },
    /**
     * Add a drawable to the end of the collection.
     */
    add_drawable: function(drawable) {
        this.drawables.push(drawable);
        drawable.container = this;
        this.changed();
    },
    /**
     * Add a drawable before another drawable.
     */
    add_drawable_before: function(drawable, other) {
        this.changed();
        var index = this.drawables.indexOf(other);
        if (index !== -1) {
            this.drawables.splice(index, 0, drawable);
            return true;
        }
        return false;
    },
    /**
     * Replace one drawable with another.
     */
    replace_drawable: function(old_drawable, new_drawable, update_html) {
        var index = this.drawables.indexOf(old_drawable);
        if (index !== -1) {
            this.drawables[index] = new_drawable;
            if (update_html) {
                old_drawable.container_div.replaceWith(new_drawable.container_div);
            }
            this.changed();
        }
        return index;
    },
    /**
     * Remove drawable from this collection.
     */
    remove_drawable: function(drawable) {
        var index = this.drawables.indexOf(drawable);
        if (index !== -1) {
            // Found drawable to remove.
            this.drawables.splice(index, 1);
            drawable.container = null;
            this.changed();
            return true;        
        }
        return false;
    },
    /**
     * Move drawable to another location in collection.
     */
    move_drawable: function(drawable, new_position) {
        var index = this.drawables.indexOf(drawable);
        if (index !== -1) {
            // Remove from current position:
            this.drawables.splice(index, 1);
            // insert into new position:
            this.drawables.splice(new_position, 0, drawable);
            this.changed();
            return true;
        }
        return false;
    }
});

/**
 * A group of drawables that are moveable, visible.
 */
var DrawableGroup = function(view, container, obj_dict) {
    extend(obj_dict, {
        obj_type: "DrawableGroup",
        drag_handle_class: "group-handle" 
    });
    DrawableCollection.call(this, view, container, obj_dict);
        
    // Set up containers/moving for group: register both container_div and content div as container
    // because both are used as containers (container div to recognize container, content_div to 
    // store elements). Group can be moved.
    this.content_div = $("<div/>").addClass("content-div").attr("id", "group_" + this.id + "_content_div").appendTo(this.container_div);
    is_container(this.container_div, this);
    is_container(this.content_div, this);
    moveable(this.container_div, this.drag_handle_class, ".group", this);
    
    // Set up filters.
    this.filters_manager = new FiltersManager(this);
    this.header_div.after(this.filters_manager.parent_div);
    // For saving drawables' filter managers when group-level filtering is done:
    this.saved_filters_managers = [];
    
    // Add drawables.
    if ('drawables' in obj_dict) {
        this.unpack_drawables(obj_dict.drawables);
    }
    
    // Restore filters.
    if ('filters' in obj_dict) {
        // FIXME: Pass collection_dict to DrawableCollection/Drawable will make this easier.
        var old_manager = this.filters_manager;
        this.filters_manager = new FiltersManager(this, obj_dict['filters']);
        old_manager.parent_div.replaceWith(this.filters_manager.parent_div);
    
        if (obj_dict.filters.visible) {
            this.setup_multitrack_filtering();
        }
    }
};

extend(DrawableGroup.prototype, Drawable.prototype, DrawableCollection.prototype, {
    action_icons_def: [
        Drawable.prototype.action_icons_def[0],
        Drawable.prototype.action_icons_def[1],
        // Replace group with composite track.
        {
            name: "composite_icon",
            title: "Show composite track",
            css_class: "layers-stack",
            on_click_fn: function(group) {
                $(".tipsy").remove();
                group.show_composite_track();
            }
        },
        // Toggle track filters.
        {
            name: "filters_icon",
            title: "Filters",
            css_class: "filters-icon",
            on_click_fn: function(group) {
                // TODO: update tipsy text.
                if (group.filters_manager.visible()) {
                    // Hiding filters.
                    group.filters_manager.clear_filters();
                    group._restore_filter_managers();
                    // TODO: maintain current filter by restoring and setting saved manager's 
                    // settings to current/shared manager's settings.
                    // TODO: need to restore filter managers when moving drawable outside group.             
                }
                else {
                    // Showing filters.
                    group.setup_multitrack_filtering();
                    group.request_draw(true);
                }
                group.filters_manager.toggle();
            }
        },
        Drawable.prototype.action_icons_def[2]
    ],
    build_container_div: function() {
        var container_div = $("<div/>").addClass("group").attr("id", "group_" + this.id);
        if (this.container) {
            this.container.content_div.append(container_div);
        }
        return container_div;
    },
    build_header_div: function() {
        var header_div = $("<div/>").addClass("track-header");
        header_div.append($("<div/>").addClass(this.drag_handle_class));
        this.name_div = $("<div/>").addClass("track-name").text(this.name).appendTo(header_div);
        return header_div;
    },
    hide_contents: function () {
        this.tiles_div.hide();
    },
    show_contents: function() {
        // Show the contents div and labels (if present)
        this.tiles_div.show();
        // Request a redraw of the content
        this.request_draw();
    },
    update_icons: function() {
        //
        // Handle update when there are no tracks.
        //
        var num_drawables = this.drawables.length
        if (num_drawables === 0) {
            this.action_icons.composite_icon.hide();
            this.action_icons.filters_icon.hide();
        }
        else if (num_drawables === 1) {
            if (this.drawables[0] instanceof CompositeTrack) {
                this.action_icons.composite_icon.show();
            }
            this.action_icons.filters_icon.hide();
        }
        else { // There are 2 or more tracks.
            //
            // Determine if a composite track can be created. Current criteria:
            // (a) all tracks are the same;
            //      OR
            // (b) there is a single FeatureTrack.
            //

            /// All tracks the same?
            var drawable,
                same_type = true,
                a_type = this.drawables[0].get_type(),
                num_feature_tracks = 0;
            for (var i = 0; i < num_drawables; i++) {
                drawable = this.drawables[i]
                if (drawable.get_type() !== a_type) {
                    can_composite = false;
                    break;
                }
                if (drawable instanceof FeatureTrack) {
                    num_feature_tracks++;
                }
            }
        
            if (same_type || num_feature_tracks === 1) {
                this.action_icons.composite_icon.show();
            }
            else {
                this.action_icons.composite_icon.hide();
                $(".tipsy").remove();
            }
        
            //
            // Set up group-level filtering and update filter icon.
            //
            if (num_feature_tracks > 1 && num_feature_tracks === this.drawables.length) {
                //
                // Find shared filters.
                //
                var 
                    shared_filters = {},
                    filter;
            
                // Init shared filters with filters from first drawable.
                drawable = this.drawables[0];
                for (var j = 0; j < drawable.filters_manager.filters.length; j++) {
                    filter = drawable.filters_manager.filters[j];
                    shared_filters[filter.name] = [filter];
                }
            
                // Create lists of shared filters.
                for (var i = 1; i < this.drawables.length; i++) {
                    drawable = this.drawables[i];
                    for (var j = 0; j < drawable.filters_manager.filters.length; j++) {
                        filter = drawable.filters_manager.filters[j];
                        if (filter.name in shared_filters) {
                            shared_filters[filter.name].push(filter);
                        }
                    }
                }
            
                //
                // Create filters for shared filters manager. Shared filters manager is group's
                // manager.
                //
                this.filters_manager.remove_all();
                var 
                    filters,
                    new_filter,
                    min,
                    max;
                for (var filter_name in shared_filters) {
                    filters = shared_filters[filter_name];
                    if (filters.length === num_feature_tracks) {
                        // Add new filter.
                        // FIXME: can filter.copy() be used?
                        new_filter = new NumberFilter( {
                                        name: filters[0].name, 
                                        index: filters[0].index
                                        } );
                        this.filters_manager.add_filter(new_filter);
                    }
                }
            
                // Show/hide icon based on filter availability.
                if (this.filters_manager.filters.length > 0) {   
                    this.action_icons.filters_icon.show();
                }
                else {
                    this.action_icons.filters_icon.hide();
                }
            }
            else {
                this.action_icons.filters_icon.hide();
            }
        }
    },
    /**
     * Restore individual track filter managers.
     */
    _restore_filter_managers: function() {
        for (var i = 0; i < this.drawables.length; i++) {
            this.drawables[i].filters_manager = this.saved_filters_managers[i];
        }
        this.saved_filters_managers = [];
    },
    /**
     *
     */
    setup_multitrack_filtering: function() {
        // Save tracks' managers and set up shared manager.
        if (this.filters_manager.filters.length > 0) {
            // For all tracks, save current filter manager and set manager to shared (this object's) manager.
            this.saved_filters_managers = [];
            for (var i = 0; i < this.drawables.length; i++) {
                drawable = this.drawables[i];
                this.saved_filters_managers.push(drawable.filters_manager);
                drawable.filters_manager = this.filters_manager;
            }

            //TODO: hide filters icons for each drawable?
        }
        this.filters_manager.init_filters();
    },
    /**
     * Replace group with a single composite track that includes all group's tracks.
     */
    show_composite_track: function() {
        // Create composite track name.
        var drawables_names = [];
        for (var i = 0; i < this.drawables.length; i++) {
            drawables_names.push(this.drawables[i].name);
        }
        var new_track_name = "Composite Track of " + this.drawables.length + " tracks (" + drawables_names.join(", ") + ")";
        
        // Replace this group with composite track.
        var composite_track = new CompositeTrack(this.view, this.view, {
            name: new_track_name,
            drawables: this.drawables
        });
        var index = this.container.replace_drawable(this, composite_track, true);
        composite_track.request_draw();
    },
    add_drawable: function(drawable) {
        DrawableCollection.prototype.add_drawable.call(this, drawable);
        this.update_icons();
    },
    remove_drawable: function(drawable) {
        DrawableCollection.prototype.remove_drawable.call(this, drawable);
        this.update_icons();
    },
    to_dict: function() {
        // If filters are visible, need to restore original filter managers before converting to dict.        
        if (this.filters_manager.visible()) {
            this._restore_filter_managers();
        }

        var obj_dict = extend(DrawableCollection.prototype.to_dict.call(this), { "filters": this.filters_manager.to_dict() });
        
        // Setup multi-track filtering again.
        if (this.filters_manager.visible()) {
            this.setup_multitrack_filtering();
        }
        
        return obj_dict;
    },
    request_draw: function(clear_after, force) {
        for (var i = 0; i < this.drawables.length; i++) {
            this.drawables[i].request_draw(clear_after, force);
        }
    }
});

/**
 * View object manages complete viz view, including tracks and user interactions.
 * Events triggered:
 *      navigate: when browser view changes to a new locations
 */
var View = function(obj_dict) {
    extend(obj_dict, {
        obj_type: "View" 
    });
    DrawableCollection.call(this, "View", obj_dict.container, obj_dict);
    this.chrom = null;
    this.vis_id = obj_dict.vis_id;
    this.dbkey = obj_dict.dbkey;
    this.label_tracks = [];
    this.tracks_to_be_redrawn = [];
    this.max_low = 0;
    this.max_high = 0;
    this.zoom_factor = 3;
    this.min_separation = 30;
    this.has_changes = false;
    // Deferred object that indicates when view's chrom data has been loaded.
    this.load_chroms_deferred = null;
    this.init();
    this.canvas_manager = new CanvasManager( this.container.get(0).ownerDocument );
    this.reset();
};
_.extend( View.prototype, Backbone.Events);
extend( View.prototype, DrawableCollection.prototype, {
    init: function() {
        // Attribute init.
        this.requested_redraw = false;
        
        // Create DOM elements
        var parent_element = this.container,
            view = this;
        // Top container for things that are fixed at the top
        this.top_container = $("<div/>").addClass("top-container").appendTo(parent_element);
        // Browser content, primary tracks are contained in here
        this.browser_content_div = $("<div/>").addClass("content").css("position", "relative").appendTo(parent_element);
        // Bottom container for things that are fixed at the bottom
        this.bottom_container = $("<div/>").addClass("bottom-container").appendTo(parent_element);
        // Label track fixed at top 
        this.top_labeltrack = $("<div/>").addClass("top-labeltrack").appendTo(this.top_container);        
        // Viewport for dragging tracks in center    
        this.viewport_container = $("<div/>").addClass("viewport-container").attr("id", "viewport-container").appendTo(this.browser_content_div);
        // Alias viewport_container as content_div so that it matches function of DrawableCollection/Group content_div.
        this.content_div = this.viewport_container;
        is_container(this.viewport_container, view);
        // Introduction div shown when there are no tracks.
        this.intro_div = $("<div/>").addClass("intro").appendTo(this.viewport_container).hide();
        var add_tracks_button = $("<div/>").text("Add Datasets to Visualization").addClass("action-button").appendTo(this.intro_div).click(function () {
            add_tracks();
        });
        // Another label track at bottom
        this.nav_labeltrack = $("<div/>").addClass("nav-labeltrack").appendTo(this.bottom_container);
        // Navigation at top
        this.nav_container = $("<div/>").addClass("trackster-nav-container").prependTo(this.top_container);
        this.nav = $("<div/>").addClass("trackster-nav").appendTo(this.nav_container);
        // Overview (scrollbar and overview plot) at bottom
        this.overview = $("<div/>").addClass("overview").appendTo(this.bottom_container);
        this.overview_viewport = $("<div/>").addClass("overview-viewport").appendTo(this.overview);
        this.overview_close = $("<a/>").attr("href", "javascript:void(0);").attr("title", "Close overview").addClass("icon-button overview-close tooltip").hide().appendTo(this.overview_viewport);
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
        this.location_span = $("<span/>").addClass("location").attr('original-title', 'Click to change location').tipsy( { gravity: 'n' } ).appendTo(this.nav_controls);
        this.location_span.click(function() {
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
        
        this.zo_link = $("<a/>").attr("id", "zoom-out").attr("title", "Zoom out").tipsy( {gravity: 'n'} )
                                .click(function() { view.zoom_out(); view.request_redraw(); }).appendTo(this.nav_controls);
        this.zi_link = $("<a/>").attr("id", "zoom-in").attr("title", "Zoom in").tipsy( {gravity: 'n'} )
                                .click(function() { view.zoom_in(); view.request_redraw(); }).appendTo(this.nav_controls);      
        
        // Get initial set of chroms.
        this.load_chroms_deferred = this.load_chroms({low: 0});
        this.chrom_select.bind("change", function() {
            view.change_chrom(view.chrom_select.val());
        });
                
        /*
        this.browser_content_div.bind("mousewheel", function( e, delta ) {
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
        this.browser_content_div.click(function( e ) {
            $(this).find("input").trigger("blur"); 
        });

        // Double clicking zooms in
        this.browser_content_div.bind("dblclick", function( e ) {
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
        
        this.overview_close.click(function() {
            view.reset_overview();
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
                dx *= 50;
                var delta_chrom = Math.round( - dx / view.viewport_container.width() * (view.high - view.low) );
                view.move_delta( delta_chrom );
            }
        });
       
        // Dragging in the top label track allows selecting a region
        // to zoom in 
        this.top_labeltrack.bind( "dragstart", function( e, d ) {
            return $("<div />").css( { 
                "height": view.browser_content_div.height() + view.top_labeltrack.height() 
                            + view.nav_labeltrack.height() + 1, 
                "top": "0px", 
                "position": "absolute", 
                "background-color": "#ccf", 
                "opacity": 0.5, 
                 "z-index": 1000
            } ).appendTo( $(this) );
        }).bind( "drag", function( e, d ) {
            $( d.proxy ).css({ left: Math.min( e.pageX, d.startX ) - view.container.offset().left, width: Math.abs( e.pageX - d.startX ) });
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
            view.request_redraw();
        });
        
        this.add_label_track( new LabelTrack( this, { content_div: this.top_labeltrack } ) );
        this.add_label_track( new LabelTrack( this, { content_div: this.nav_labeltrack } ) );
        
        $(window).bind("resize", function() {
            // Stop previous timer.
            if (this.resize_timer) {
                clearTimeout(this.resize_timer);
            }
            
            // When function activated, resize window and redraw.
            this.resize_timer = setTimeout(function () {
                view.resize_window();
            }, 500 );
        });
        $(document).bind("redraw", function() { view.redraw(); });
        
        this.reset();
        $(window).trigger("resize");
    },
    changed: function() {
        this.has_changes = true;  
    },
    /** Add or remove intro div depending on view state. */
    update_intro_div: function() {
        if (this.drawables.length === 0) {
            this.intro_div.show();
        }
        else {
            this.intro_div.hide();
        }
    },
    /**
     * Triggers navigate events as needed. If there is a delay,
     * then event is triggered only after navigation has stopped.
     */
    trigger_navigate: function(new_chrom, new_low, new_high, delay) {
        // Stop previous timer.
        if (this.timer) {
            clearTimeout(this.timer);
        }
        
        if (delay) {
            // To aggregate calls, use timer and only navigate once
            // location has stabilized.
            var self = this;
            this.timer = setTimeout(function () {
                self.trigger("navigate", new_chrom + ":" + new_low + "-" + new_high);
            }, 500 );
        }
        else {
            view.trigger("navigate", new_chrom + ":" + new_low + "-" + new_high);
        }
    },
    update_location: function(low, high) {
        this.location_span.text( commatize(low) + ' - ' + commatize(high) );
        this.nav_input.val( this.chrom + ':' + commatize(low) + '-' + commatize(high) );
        
        // Update location. Only update when there is a valid chrom; when loading vis, there may 
        // not be a valid chrom.
        var chrom = view.chrom_select.val();
        if (chrom !== "") {
            this.trigger_navigate(chrom, view.low, view.high, true);
        }
    },
    /**
     * Load chrom data for the view. Returns a jQuery Deferred.
     */
    load_chroms: function(url_parms) {
        url_parms['num'] = MAX_CHROMS_SELECTABLE;
        url_parms['dbkey'] = this.dbkey;

        var 
            view = this,
            chrom_data = $.Deferred();
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
                view.chrom_start_index = result.start_index;
                
                chrom_data.resolve(result);
            },
            error: function() {
                alert("Could not load chroms for this dbkey:", view.dbkey);
            }
        });
        
        return chrom_data;
    },
    change_chrom: function(chrom, low, high) {
        var view = this;
        // If chrom data is still loading, wait for it.
        if (!view.chrom_data) {
            view.load_chroms_deferred.then(function() {
                view.change_chrom(chrom, low, high);
            });
            return;
        }
        
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
                view.chrom_select.val(view.chrom);
                view.max_high = found.len-1; // -1 because we're using 0-based indexing.
                view.reset();
                view.request_redraw(true);

                for (var i = 0, len = view.drawables.length; i < len; i++) {
                    var drawable = view.drawables[i];
                    if (drawable.init) {
                        drawable.init();
                    }
                }
                if (view.reference_track) {
                    view.reference_track.init();
                }
            }
            if (low !== undefined && high !== undefined) {
                view.low = Math.max(low, 0);
                view.high = Math.min(high, view.max_high);
            }
            else {
                // Low and high undefined, so view is whole chome.
                view.low = 0;
                view.high = view.max_high;
            }
            view.reset_overview();
            view.request_redraw();
        }
    },
    go_to: function(str) {
        // Preprocess str to remove spaces and commas.
        str = str.replace(/ |,/g, "");
        
        // Go to new location.
        var view = this,
            new_low, 
            new_high,
            chrom_pos = str.split(":"),
            chrom = chrom_pos[0],
            pos = chrom_pos[1];
        
        if (pos !== undefined) {
            try {
                var pos_split = pos.split("-");
                new_low = parseInt(pos_split[0], 10);
                new_high = parseInt(pos_split[1], 10);
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
        // Update low, high.
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
                
        view.request_redraw();
        
        // Navigate.
        var chrom = view.chrom_select.val();
        this.trigger_navigate(chrom, view.low, view.high, true);
    },
    /**
     * Add a drawable to the view.
     */
    add_drawable: function(drawable) {
        DrawableCollection.prototype.add_drawable.call(this, drawable);
        drawable.init();
        this.changed();
        this.update_intro_div();
    },
    add_label_track: function (label_track) {
        label_track.view = this;
        label_track.init();
        this.label_tracks.push(label_track);
    },
    /**
     * Remove drawable from the view.
     */
    remove_drawable: function(drawable, hide) {
        DrawableCollection.prototype.remove_drawable.call(this, drawable);
        if (hide) {
            var view = this;
            drawable.container_div.hide(0, function() { 
                $(this).remove();
                view.update_intro_div(); 
            });
        }
    },
    reset: function() {
        this.low = this.max_low;
        this.high = this.max_high;
        this.viewport_container.find(".yaxislabel").remove();
    },
    /**
     * Request that view redraw some or all tracks. If a track is not specificied, redraw all tracks.
     */
    // FIXME: change method call so that track is first and additional parameters are optional.
    // FIXME: is nodraw parameter needed?
    request_redraw: function(nodraw, force, clear_after, track) {
        var 
            view = this,
            // Either redrawing a single drawable or all view's drawables.
            track_list = (track ? [track] : view.drawables),
            track_index;
            
        // Add/update tracks in track list to redraw list.
        var track;
        for (var i = 0; i < track_list.length; i++) {
            track = track_list[i];
            
            // Because list elements are arrays, need to look for track index manually.
            track_index = -1;
            for (var j = 0; j < view.tracks_to_be_redrawn.length; j++) {
                if (view.tracks_to_be_redrawn[j][0] === track) {
                    track_index = j;
                    break;
                }
            }
            
            // Add track to list or update draw parameters.
            if (track_index < 0) {
                // Track not in list yet.
                view.tracks_to_be_redrawn.push([track, force, clear_after]);
            }
            else {
                // Track already in list; update force and clear_after.
                view.tracks_to_be_redrawn[i][1] = force;
                view.tracks_to_be_redrawn[i][2] = clear_after;
            }
        }

        // Set up redraw if it has not been requested since last redraw.
        if (!this.requested_redraw) {
            requestAnimationFrame(function() { view._redraw(nodraw) });
            this.requested_redraw = true;
        }
    },
    /**
     * Redraws view and tracks.
     * NOTE: this method should never be called directly; request_redraw() should be used so
     * that requestAnimationFrame can manage redrawing.
     */
    _redraw: function(nodraw) {
        // TODO: move this code to function that does location setting.
        
        // Clear because requested redraw is being handled now.
        this.requested_redraw = false;
        
        var low = this.low,
            high = this.high;
        
        if (low < this.max_low) {
            low = this.max_low;
        }
        if (high > this.max_high) {
            high = this.max_high;
        }
        var span = this.high - this.low;
        if (this.high !== 0 && span < this.min_separation) {
            high = low + this.min_separation;
        }
        this.low = Math.floor(low);
        this.high = Math.ceil(high);
        
        this.update_location(this.low, this.high);
        
        // -- Drawing code --
        
        // Calculate resolution in both pixels/base and bases/pixel; round bases/pixels for tile calculations.
        // TODO: require minimum difference in new resolution to update?
        this.resolution_b_px = (this.high - this.low) / this.viewport_container.width();
        this.resolution_px_b = this.viewport_container.width() / (this.high - this.low);
                    
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
        
        if (!nodraw) {
            var track, force, clear_after;
            for (var i = 0, len = this.tracks_to_be_redrawn.length; i < len; i++) {
                track = this.tracks_to_be_redrawn[i][0];
                force = this.tracks_to_be_redrawn[i][1];
                clear_after = this.tracks_to_be_redrawn[i][2];
                if (track) {
                    track._draw(force, clear_after);
                }
            }
            this.tracks_to_be_redrawn = [];
            for (i = 0, len = this.label_tracks.length; i < len; i++) {
                this.label_tracks[i]._draw();
            }
        }
    },
    zoom_in: function (point, container) {
        if (this.max_high === 0 || this.high - this.low <= this.min_separation) {
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
        this.changed();
        this.request_redraw();
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
        this.changed();
        this.request_redraw();
    },
    resize_window: function() {
        this.viewport_container.height( this.container.height() - this.top_container.height() - this.bottom_container.height() );
        this.request_redraw();
    },
    /** Show a Drawable in the overview. */
    set_overview: function(drawable) {
        if (this.overview_drawable) {
            // If drawable to be set as overview is already in overview, do nothing.
            // Otherwise, remove overview.
            if (this.overview_drawable.dataset_id === drawable.dataset_id) {
                return;
            }
            this.overview_viewport.find(".track").remove();
        }
        
        // Set new overview.
        var 
            overview_drawable = drawable.copy( { content_div: this.overview_viewport } ),
            view = this;
        overview_drawable.header_div.hide();
        overview_drawable.is_overview = true;
        view.overview_drawable = overview_drawable;
        this.overview_drawable.postdraw_actions = function() {
            view.overview_highlight.show().height(view.overview_drawable.content_div.height());
            view.overview_viewport.height(view.overview_drawable.content_div.height() + view.overview_box.outerHeight());
            view.overview_close.show();
            view.resize_window();
        };
        view.overview_drawable.request_draw();
        this.changed();
    },
    /** Close and reset overview. */
    reset_overview: function() {
        // Update UI.
        $(".tipsy").remove();
        this.overview_viewport.find(".track-tile").remove();
        this.overview_viewport.height(this.default_overview_height);
        this.overview_box.height(this.default_overview_height);
        this.overview_close.hide();
        this.overview_highlight.hide();
        view.resize_window();
        view.overview_drawable = null;
    }
});

/**
 * Encapsulation of a tool that users can apply to tracks/datasets.
 */
var Tool = function(track, tool_dict, tool_state_dict) {    
    //
    // Unpack tool information from dictionary.
    //
    this.track = track;
    this.name = tool_dict.name;
    this.params = [];
    var params_dict = tool_dict.params;
    for (var i = 0; i < params_dict.length; i++) {
        // FIXME: use dict for creating parameters.
        var param_dict = params_dict[i],
            name = param_dict.name,
            label = param_dict.label,
            html = unescape(param_dict.html),
            value = param_dict.value,
            type = param_dict.type;
        if (type === "number") {
            this.params.push(
                new NumberParameter(name, label, html, 
                                    (name in tool_state_dict ? tool_state_dict[name] : value),
                                    param_dict.min, param_dict.max)
                            );
        }
        else if (type === "select") {
            this.params.push(
                new ToolParameter(name, label, html, 
                                  (name in tool_state_dict ? tool_state_dict[name] : value))
                            );
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
    }).click(function(e) {
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
        var html_div = $("<div/>").addClass("param-input").html(param.html).appendTo(param_div);
        // Set initial value.
        html_div.find(":input").val(param.value);
        
        // Add to clear floating layout.
        $("<div style='clear: both;'/>").appendTo(param_div);
    });
    
    // Highlight value for inputs for easy replacement.
    this.parent_div.find("input").click(function() { $(this).select() });
    
    // Add buttons for running on dataset, region.
    var run_tool_row = $("<div>").addClass("param-row").appendTo(this.parent_div);
    var run_on_dataset_button = $("<input type='submit'>").attr("value", "Run on complete dataset").appendTo(run_tool_row);
    var run_on_region_button = $("<input type='submit'>").attr("value", "Run on visible region").css("margin-left", "3em").appendTo(run_tool_row);
    var tool = this;
    run_on_region_button.click( function() {
        // Run tool to create new track.
        tool.run_on_region();
    });
    run_on_dataset_button.click( function() {
        tool.run_on_dataset();
    });
    
    if ('visible' in tool_state_dict && tool_state_dict.visible) {
        this.parent_div.show();
    }
};
extend(Tool.prototype, {
    /**
     * Update tool parameters.
     */
    update_params: function() {
        for (var i = 0; i < this.params.length; i++) {
            this.params[i].update_value();
        }
    },
    /**
     * Returns a dict with tool state information.
     */
    state_dict: function() {
        // Save parameter values.
        var tool_state = {};
        for (var i = 0; i < this.params.length; i++) {
            tool_state[this.params[i].name] = this.params[i].value;
        }
        
        // Save visibility.
        tool_state.visible = this.parent_div.is(":visible");
        
        return tool_state;
    },
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
     * Run tool on dataset. Output is placed in dataset's history and no changes to viz are made.
     */
    run_on_dataset: function() {
        var tool = this;
        tool.run(
                 // URL params.
                 { 
                     dataset_id: this.track.original_dataset_id,
                     tool_id: tool.name
                 },
                 null,
                 // Success callback.
                 function(track_data) {
                     show_modal(tool.name + " is Running", 
                                tool.name + " is running on the complete dataset. Tool outputs are in dataset's history.", 
                                { "Close" : hide_modal } );
                 }
                );
        
    },
    /**
     * Run dataset on visible region. This creates a new track and sets the track's contents
     * to the tool's output.
     */
    run_on_region: function() {
        //
        // Create track for tool's output immediately to provide user feedback.
        //
        var 
            url_params = 
            { 
                dataset_id: this.track.original_dataset_id,
                chrom: this.track.view.chrom,
                low: this.track.view.low,
                high: this.track.view.high,
                tool_id: this.name
            },
            current_track = this.track,
            // Set name of track to include tool name, parameters, and region used.
            track_name = url_params.tool_id +
                         current_track.tool_region_and_parameters_str(url_params.chrom, url_params.low, url_params.high),
            container;
            
        // If track not in a group, create a group for it and add new track to group. If track 
        // already in group, add track to group.
        if (current_track.container === view) {
            // Create new group.
            var group = new DrawableGroup(view, view, { name: this.name })
            
            // Replace track with group.
            var index = current_track.container.replace_drawable(current_track, group, false);
            
            // Update HTML.
            // FIXME: this is ugly way to replace a track with a group -- make this easier via
            // a Drawable or DrawableCollection function.
            group.container_div.insertBefore(current_track.view.content_div.children()[index]);
            group.add_drawable(current_track);
            current_track.container_div.appendTo(group.content_div);
            container = group;
        }
        else {
            // Use current group.
            container = current_track.container;
        }
        
        // Create and init new track.
        var new_track = new current_track.constructor(view, container, {
            name: track_name,
            hda_ldda: "hda"
        });
        new_track.init_for_tool_data();
        new_track.change_mode(current_track.mode);
        new_track.set_filters_manager(current_track.filters_manager.copy(new_track));
        new_track.update_icons();
        container.add_drawable(new_track);
        new_track.tiles_div.text("Starting job.");
        
        // Run tool.
        this.update_params();
        this.run(url_params, new_track,
                 // Success callback.
                 function(track_data) {
                     new_track.dataset_id = track_data.dataset_id;
                     new_track.tiles_div.text("Running job.");
                     new_track.init();
                 }
                );
    },
    /**
     * Run tool using a set of URL params and a success callback.
     */
    run: function(url_params, new_track, success_callback) {
        // Add tool params to URL params.
        $.extend(url_params, this.get_param_values_dict());
        
        // Run tool.
        // TODO: rewrite to use server state deferred.
        var json_run_tool = function() {
            $.getJSON(rerun_tool_url, url_params, function(response) {
                if (response === "no converter") {
                    // No converter available for input datasets, so cannot run tool.
                    new_track.container_div.addClass("error");
                    new_track.content_div.text(DATA_NOCONVERTER);
                }
                else if (response.error) {
                    // General error.
                    new_track.container_div.addClass("error");
                    new_track.content_div.text(DATA_CANNOT_RUN_TOOL + response.message);
                }
                else if (response === "pending") {
                    // Converting/indexing input datasets; show message and try again.
                    new_track.container_div.addClass("pending");
                    new_track.content_div.text("Converting input data so that it can be used quickly with tool.");
                    setTimeout(json_run_tool, 2000);
                }
                else {
                    // Job submitted and running.
                    success_callback(response);
                }
            });
        };
        json_run_tool();
    }
});

/**
 * Tool parameters.
 */
var ToolParameter = function(name, label, html, value) {
    this.name = name;
    this.label = label;
    // Need to use jQuery for HTML so that value can be queried and updated dynamically.
    this.html = $(html);
    this.value = value;
};

extend(ToolParameter.prototype, {
    update_value: function() {
        this.value = $(this.html).val();
    } 
});

var NumberParameter = function(name, label, html, value, min, max) {
    ToolParameter.call(this, name, label, html, value)
    this.min = min;
    this.max = max;
};

extend(NumberParameter.prototype, ToolParameter.prototype, {
    update_value: function() {
        ToolParameter.prototype.update_value.call(this);
        this.value = parseFloat(this.value);
    }
});

/**
 * Filters that enable users to show/hide data points dynamically.
 */
var Filter = function(obj_dict) {
    this.manager = null;
    this.name = obj_dict.name;
    // Index into payload to filter.
    this.index = obj_dict.index;
    this.tool_id = obj_dict.tool_id;
    // Name to use for filter when building expression for tool.
    this.tool_exp_name = obj_dict.tool_exp_name;
};

extend(Filter.prototype, {
    /**
     * Convert filter to dictionary.
     */
    to_dict: function() {
        return {
            name: this.name,
            index: this.index,
            tool_id: this.tool_id,
            tool_exp_name: this.tool_exp_name
        };
    } 
});

/**
 * Number filters have a min, max as well as a low, high; low and high are used 
 */
var NumberFilter = function(obj_dict) {
    //
    // Attribute init.
    //
    Filter.call(this, obj_dict);
    // Filter low/high. These values are used to filter elements.
    this.low = ('low' in obj_dict ? obj_dict.low : -Number.MAX_VALUE);
    this.high = ('high' in obj_dict ? obj_dict.high : Number.MAX_VALUE);
    // Slide min/max. These values are used to set/update slider.
    this.min = ('min' in obj_dict ? obj_dict.min : Number.MAX_VALUE);
    this.max = ('max' in obj_dict ? obj_dict.max : -Number.MAX_VALUE)
    // UI elements associated with filter.
    this.container = null;
    this.slider = null;
    this.slider_label = null;
    
    //
    // Create HTML.
    //
    
    // Function that supports inline text editing of slider values.
    // Enable users to edit parameter's value via a text box.
    var edit_slider_values = function(container, span, slider) {
        container.click(function() {
            var cur_value = span.text(),
                max = parseFloat(slider.slider("option", "max")),
                input_size = (max <= 1 ? 4 : max <= 1000000 ? max.toString().length : 6),
                multi_value = false,
                slider_row = $(this).parents(".slider-row");
                
            // Row now has input.
            slider_row.addClass("input");
                
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
                slider_row.removeClass("input");
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
                    
                    // Updating the slider also updates slider values and removes input. 
                    slider.slider((multi_value ? "values" : "value"), new_value);
                    slider_row.removeClass("input");
                }
            });
        });
    };
    
    var filter = this;
    
    filter.parent_div = $("<div/>").addClass("filter-row slider-row");
    
    // Set up filter label (name, values).
    var filter_label = $("<div/>").addClass("elt-label").appendTo(filter.parent_div),
        name_span = $("<span/>").addClass("slider-name").text(filter.name + "  ").appendTo(filter_label),
        values_span = $("<span/>").text(this.low + "-" + this.high),
        values_span_container = $("<span/>").addClass("slider-value").appendTo(filter_label).append("[").append(values_span).append("]");
    filter.values_span = values_span;
            
    // Set up slider for filter.
    var slider_div = $("<div/>").addClass("slider").appendTo(filter.parent_div);
    filter.control_element = $("<div/>").attr("id", filter.name + "-filter-control").appendTo(slider_div);
    var prev_values = [0,0];
    filter.control_element.slider({
        range: true,
        min: this.min,
        max: this.max,
        step: this.get_slider_step(this.min, this.max),
        values: [this.low, this.high],
        slide: function(event, ui) { 
            filter.slide(event, ui); 
        },
        change: function(event, ui) {
            filter.control_element.slider("option", "slide").call(filter.control_element, event, ui);
        }
    });
    filter.slider = filter.control_element;
    filter.slider_label = values_span;
    
    // Enable users to edit slider values via text box.
    edit_slider_values(values_span_container, values_span, filter.control_element);
    
    // Set up filter display controls.
    var display_controls_div = $("<div/>").addClass("display-controls").appendTo(filter.parent_div);
    this.transparency_icon = create_action_icon("Use filter for data transparency", "layer-transparent", 
                                                function() {
                                                    if (filter.manager.alpha_filter !== filter) {
                                                        // Setting this filter as the alpha filter.
                                                        filter.manager.alpha_filter = filter;
                                                        // Update UI for new filter.
                                                        filter.manager.parent_div.find(".layer-transparent").removeClass("active").hide();
                                                        filter.transparency_icon.addClass("active").show();
                                                    }
                                                    else {
                                                        // Clearing filter as alpha filter.
                                                        filter.manager.alpha_filter = null;
                                                        filter.transparency_icon.removeClass("active");
                                                    }
                                                    filter.manager.track.request_draw(true, true);
                                                } )
                                                .appendTo(display_controls_div).hide();
    this.height_icon = create_action_icon("Use filter for data height", "arrow-resize-090", 
                                                function() {
                                                    if (filter.manager.height_filter !== filter) {
                                                        // Setting this filter as the height filter.
                                                        filter.manager.height_filter = filter;
                                                        // Update UI for new filter.
                                                        filter.manager.parent_div.find(".arrow-resize-090").removeClass("active").hide();
                                                        filter.height_icon.addClass("active").show();
                                                    }
                                                    else {
                                                        // Clearing filter as alpha filter.
                                                        filter.manager.height_filter = null;
                                                        filter.height_icon.removeClass("active");
                                                    }
                                                    filter.manager.track.request_draw(true, true);
                                                } )
                                                .appendTo(display_controls_div).hide();
    filter.parent_div.hover( function() { 
                                filter.transparency_icon.show();
                                filter.height_icon.show(); 
                            },
                            function() {
                                if (filter.manager.alpha_filter !== filter) {
                                    filter.transparency_icon.hide();
                                }
                                if (filter.manager.height_filter !== filter) {
                                    filter.height_icon.hide();
                                }
                            } );
    
    // Add to clear floating layout.
    $("<div style='clear: both;'/>").appendTo(filter.parent_div);
};
extend(NumberFilter.prototype, {
    /**
     * Convert filter to dictionary.
     */
    to_dict: function() {
        var obj_dict = Filter.prototype.to_dict.call(this);
        return extend(obj_dict, {
            type: 'number',
            min: this.min,
            max: this.max,
            low: this.low,
            high: this.high
        });
    },
    /**
     * Return a copy of filter.
     */
    copy: function() {
        return new NumberFilter( 
            {
                name: this.name, 
                index: this.index, 
                tool_id: this.tool_id, 
                tool_exp_name: this.tool_exp_name
            });
    },
    /**
     * Get step for slider.
     */
    // FIXME: make this a "static" function.
    get_slider_step: function(min, max) {
        var range = max - min;
        return (range <= 2 ? 0.01 : 1);
    },
    /**
     * Handle slide events.
     */
    slide: function(event, ui) {
         var values = ui.values;
         
         // Set new values in UI.
         this.values_span.text(values[0] + "-" + values[1]);
         
         // Set new values in filter.
         this.low = values[0];
         this.high = values[1];
         
         // Redraw track.
         this.manager.track.request_draw(true, true);
     },
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
     * Helper function: returns true if value in in filter's [low, high] range.
     */
    _keep_val: function(val) {
        return (isNaN(val) || (val >= this.low && val <= this.high));
    },    
    /**
     * Returns true if (a) element's value(s) is in [low, high] (range is inclusive) 
     * or (b) if value is non-numeric and hence unfilterable.
     */
    keep: function(element) {
        if ( !this.applies_to( element ) ) {
            // No element to filter on.
            return true;
        }

        // Keep value function.
        var filter = this;

        // Do filtering.
        var to_filter = element[this.index];
        if (to_filter instanceof Array) {
            var returnVal = true;
            for (var i = 0; i < to_filter.length; i++) {
                if (!this._keep_val(to_filter[i])) {
                    // Exclude element.
                    returnVal = false;
                    break;
                }
            }
            return returnVal;
        }
        else {
            return this._keep_val(element[this.index]);
        }
    },
    /**
     * Update filter's min and max values based on element's values.
     */
    update_attrs: function(element) {
        var updated = false;
        if (!this.applies_to(element) ) {
            return updated;
        }
        
        //
        // Update filter's min, max based on element values.
        //
        
        // Make value(s) into an Array.
        var values = element[this.index];
        if (!(values instanceof Array)) {
            values = [values];
        }
        
        // Loop through values and update min, max.
        for (var i = 0; i < values.length; i++) {
            var value = values[i];
            if (value < this.min) {
                this.min = Math.floor(value);
                updated = true;
            }
            if (value > this.max) {
                this.max = Math.ceil(value);
                updated = true;
            }
        }
        return updated;
    },
    /**
     * Update filter's slider.
     */
    update_ui_elt: function () {
        // Only show filter if min != max because filter is not useful otherwise.
        if (this.min !== this.max) {
            this.parent_div.show();
        }
        else {
            this.parent_div.hide();
        }
        
        var 
            slider_min = this.slider.slider("option", "min"),
            slider_max = this.slider.slider("option", "max");
        if (this.min < slider_min || this.max > slider_max) {
            // Update slider min, max, step.
            this.slider.slider("option", "min", this.min);
            this.slider.slider("option", "max", this.max);
            this.slider.slider("option", "step", this.get_slider_step(this.min, this.max));
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
 * Manages a set of filters.
 */
var FiltersManager = function(track, obj_dict) {
    this.track = track;
    this.alpha_filter = null;
    this.height_filter = null;
    this.filters = [];
    
    //
    // Create HTML.
    //
        
    //
    // Create parent div.
    //
    this.parent_div = $("<div/>").addClass("filters").hide();
    // Disable dragging, double clicking, keys on div so that actions on slider do not impact viz.
    this.parent_div.bind("drag", function(e) {
        e.stopPropagation();
    }).click(function(e) {
        e.stopPropagation();
    }).bind("dblclick", function(e) {
        e.stopPropagation();
    }).bind("keydown", function(e) {
        e.stopPropagation();
    });
    
    //
    // Restore state from dict.
    //
    if (obj_dict && 'filters' in obj_dict) { // Second condition needed for backward compatibility.
        var 
            alpha_filter_name = ('alpha_filter' in obj_dict ? obj_dict.alpha_filter : null),
            height_filter_name = ('height_filter' in obj_dict ? obj_dict.height_filter : null),            
            filters_dict = obj_dict.filters,
            filter;
        for (var i = 0; i < filters_dict.length; i++) {
            if (filters_dict[i].type === 'number') {
                filter = new NumberFilter(filters_dict[i]);
                this.add_filter(filter);
                if (filter.name === alpha_filter_name) {
                    this.alpha_filter = filter;
                    filter.transparency_icon.addClass("active").show();
                }
                if (filter.name === height_filter_name) {
                    this.height_filter = filter;
                    filter.height_icon.addClass("active").show();
                }
            } 
            else {
                console.log("ERROR: unsupported filter: ", name, type)
            }
        }
        
        
        if ('visible' in obj_dict && obj_dict.visible) {
            this.parent_div.show();
        }
    }
    
    // Add button to filter complete dataset.
    if (this.filters.length !== 0) {
        var run_buttons_row = $("<div/>").addClass("param-row").appendTo(this.parent_div);
        var run_on_dataset_button = $("<input type='submit'/>").attr("value", "Run on complete dataset").appendTo(run_buttons_row);
        var filter_manager = this;
        run_on_dataset_button.click( function() {
            filter_manager.run_on_dataset();
        });
    }
        
};

extend(FiltersManager.prototype, {
    // HTML manipulation and inspection.
    show: function() { this.parent_div.show(); },
    hide: function() { this.parent_div.hide(); },
    toggle: function() { this.parent_div.toggle(); },
    visible: function() { return this.parent_div.is(":visible"); },
    /**
     * Returns dictionary for manager.
     */
    to_dict: function() {
        var obj_dict = {},
            filter_dicts = [],
            filter;
            
        // Include individual filter states.
        for (var i = 0; i < this.filters.length; i++) {
            filter = this.filters[i];
            filter_dicts.push(filter.to_dict());
        }
        obj_dict['filters'] = filter_dicts;
        
        // Include transparency, height filters.
        obj_dict['alpha_filter'] = (this.alpha_filter ? this.alpha_filter.name : null);
        obj_dict['height_filter'] = (this.height_filter ? this.height_filter.name : null);
        
        // Include visibility.
        obj_dict['visible'] = this.parent_div.is(":visible");
        
        return obj_dict;
    },
    /**
     * Return a copy of the manager.
     */
    copy: function(new_track) {
        var copy = new FiltersManager(new_track);
        for (var i = 0; i < this.filters.length; i++) {
            copy.add_filter(this.filters[i].copy());
        }
        return copy;
    },
    /**
     * Add a filter to the manager.
     */
    add_filter: function(filter) {
        filter.manager = this;
        this.parent_div.append(filter.parent_div);
        this.filters.push(filter);  
    },
    /**
     * Remove all filters from manager.
     */
    remove_all: function() {
        this.filters = [];
        this.parent_div.children().remove();
    },
    /**
     * Initialize filters.
     */ 
    init_filters: function() {
        for (var i = 0; i < this.filters.length; i++) {
            var filter = this.filters[i];
            filter.update_ui_elt();
        }
    },
    /**
     * Clear filters so that they do not impact track display.
     */
    clear_filters: function() {
        for (var i = 0; i < this.filters.length; i++) {
            var filter = this.filters[i];
            filter.slider.slider("option", "values", [filter.min, filter.max]);
        }
        this.alpha_filter = null;
        this.height_filter = null;
        
        // Hide icons for setting filters.
        this.parent_div.find(".icon-button").hide();
    },
    run_on_dataset: function() {
        // Get or create dictionary item.
        var get_or_create_dict_item = function(dict, key, new_item) {
            // Add new item to dict if 
            if (!(key in dict)) {
                dict[key] = new_item;
            }
            return dict[key];
        };
        
        //
        // Find and group active filters. Active filters are those being used to hide data.
        // Filters with the same tool id are grouped.
        //
        var active_filters = {},
            filter, 
            tool_filter_conditions,
            operation;
        for (var i = 0; i < this.filters.length; i++) {
            filter = this.filters[i];
            if (filter.tool_id) {
                // Add filtering conditions if filter low/high are set.
                if (filter.min !== filter.low) {
                    tool_filter_conditions = get_or_create_dict_item(active_filters, filter.tool_id, []);
                    tool_filter_conditions[tool_filter_conditions.length] = filter.tool_exp_name + " >= " + filter.low;
                }
                if (filter.max !== filter.high) {
                    tool_filter_conditions = get_or_create_dict_item(active_filters, filter.tool_id, []);
                    tool_filter_conditions[tool_filter_conditions.length] = filter.tool_exp_name + " <= " + filter.high;
                }
            }
        }
        
        //
        // Use tools to run filters.
        //
        
        // Create list of (tool_id, tool_filters) tuples.
        var active_filters_list = [];
        for (var tool_id in active_filters) {
            active_filters_list[active_filters_list.length] = [tool_id, active_filters[tool_id]];
        }
        
        // Invoke recursive function to run filters; this enables chaining of filters via
        // iteratively application.
        var num_filters = active_filters_list.length;
        (function run_filter(input_dataset_id, filters) {
            var 
                // Set up filtering info and params.
                filter_tuple = filters[0],
                tool_id = filter_tuple[0],
                tool_filters = filter_tuple[1],
                tool_filter_str = "(" + tool_filters.join(") and (") + ")",
                url_params = {
                    cond: tool_filter_str,
                    input: input_dataset_id,
                    target_dataset_id: input_dataset_id,
                    tool_id: tool_id
                },
                // Remove current filter.
                filters = filters.slice(1);
                
            $.getJSON(run_tool_url, url_params, function(response) {
                if (response.error) {
                    // General error.
                    show_modal("Filter Dataset",
                               "Error running tool " + tool_id,
                               { "Close" : hide_modal } );
                }
                else if (filters.length === 0) {
                    // No more filters to run.
                    show_modal("Filtering Dataset", 
                               "Filter(s) are running on the complete dataset. Outputs are in dataset's history.", 
                               { "Close" : hide_modal } );
                }
                else {
                    // More filters to run.
                    run_filter(response.dataset_id, filters);
                }
            });
              
        })(this.track.dataset_id, active_filters_list);        
    }
});

/**
 * Generates scale values based on filter and feature's value for filter.
 */
var FilterScaler = function(filter, default_val) {
    painters.Scaler.call(this, default_val);
    this.filter = filter;
};

FilterScaler.prototype.gen_val = function(feature_data) {
    // If filter is not initalized yet, return default val.
    if (this.filter.high === Number.MAX_VALUE || this.filter.low === -Number.MAX_VALUE || this.filter.low === this.filter.high) {
        return this.default_val;
    }
    
    // Scaling value is ratio of (filter's value compared to low) to (complete filter range).
    return ( ( parseFloat(feature_data[this.filter.index]) - this.filter.low ) / ( this.filter.high - this.filter.low ) );
};

/**
 * Container for Drawable configuration data.
 */
var DrawableConfig = function( options ) {
    this.track = options.track;
    this.params = options.params;
    this.values = {}
    this.restore_values( (options.saved_values ? options.saved_values : {}) );
    this.onchange = options.onchange
};

extend(DrawableConfig.prototype, {
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
        var param;
        // Function to process parameters recursively
        function handle_params( params, container ) {
            for ( var index = 0; index < params.length; index++ ) {
                param = params[index];
                // Hidden params have no representation in the form
                if ( param.hidden ) { continue; }
                // Build row for param
                var id = 'param_' + index;
                var value = track_config.values[ param.key ];
                var row = $("<div class='form-row' />").appendTo( container );
                row.append( $('<label />').attr("for", id ).text( param.label + ":" ) );
                // Draw parameter as checkbox
                if ( param.type === 'bool' ) {
                    row.append( $('<input type="checkbox" />').attr("id", id ).attr("name", id ).attr( 'checked', value ) );
                // Draw parameter as textbox
                } else if ( param.type === 'text' ) {
                    row.append( $('<input type="text"/>').attr("id", id ).val(value).click( function() { $(this).select() }));
                // Draw paramter as select area
                } else if ( param.type === 'select' ) {
                    var select = $('<select />').attr("id", id);
                    for ( var i = 0; i < param.options.length; i++ ) {
                        $("<option/>").text( param.options[i].label ).attr( "value", param.options[i].value ).appendTo( select );
                    }
                    select.val( value );
                    row.append( select );
                // Draw parameter as color picker
                } else if ( param.type === 'color' ) {
                    var 
                        container_div = $("<div/>").appendTo(row),
                        input = $('<input />').attr("id", id ).attr("name", id ).val( value ).css("float", "left")                  
                            .appendTo(container_div).click(function(e) {
                            // Hide other pickers.
                            $(".tipsy").hide();
                            
                            // Show input's color picker.
                            var tip = $(this).siblings(".tipsy");
                            tip.css( { 
                                // left: $(this).position().left + ( $(input).width() / 2 ) - 60,
                                // top: $(this).position().top + $(this.height) 
                                left: $(this).position().left + $(this).width() + 5,
                                top: $(this).position().top - ( $(tip).height() / 2 ) + ( $(this).height() / 2 )
                                } ).show();
                                
                            // Click management: 
                            
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
                        // Icon for setting a new random color; behavior set below.
                        new_color_icon = $("<a href='javascript:void(0)'/>").addClass("icon-button arrow-circle").appendTo(container_div)
                                         .attr("title", "Set new random color").tipsy({ gravity: 's' }),
                        // Color picker in tool tip style.
                        tip = $( "<div class='tipsy tipsy-west' style='position: absolute;' />" ).appendTo(container_div).hide(),
                        // Inner div for padding purposes
                        tip_inner = $("<div style='background-color: black; padding: 10px;'></div>").appendTo(tip),
                        farb_container = $("<div/>").appendTo(tip_inner),
                        farb_obj = $.farbtastic(farb_container, { width: 100, height: 100, callback: input, color: value });
                    
                    // Clear floating.
                    container_div.append( $("<div/>").css("clear", "both"));
                    
                    // Use function to fix farb_obj value.
                    (function(fixed_farb_obj) {
                        new_color_icon.click(function() {
                            fixed_farb_obj.setColor(get_random_color());
                        });  
                    })(farb_obj);
                      
                } 
                else {
                    row.append( $('<input />').attr("id", id ).attr("name", id ).val( value ) ); 
                }
                // Help text
                if ( param.help ) {
                    row.append( $("<div class='help'/>").text( param.help ) );
                }
            }
        }
        // Handle top level parameters in order
        handle_params( this.params, container );
        // Return element containing constructed form
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
            this.track.changed();
        }
    }
});

/**
 * Tiles drawn by tracks.
 */
var Tile = function(track, index, resolution, canvas, data) {
    this.track = track;
    this.index = index;
    var tile_bounds = this.track._get_tile_bounds(index, resolution);
    this.low = tile_bounds[0];
    this.high = tile_bounds[1];
    this.resolution = resolution;
    // Wrap element in div for background.
    this.html_elt = $("<div class='track-tile'/>").append(canvas);
    this.data = data;
    this.stale = false;
};

/**
 * Perform pre-display actions.
 */
Tile.prototype.predisplay_actions = function() {};

var SummaryTreeTile = function(track, index, resolution, canvas, data, max_val) {
    Tile.call(this, track, index, resolution, canvas, data);
    this.max_val = max_val;
};
extend(SummaryTreeTile.prototype, Tile.prototype);

var FeatureTrackTile = function(track, index, resolution, canvas, data, w_scale, mode, message, all_slotted, feature_mapper) {
    // Attribute init.
    Tile.call(this, track, index, resolution, canvas, data);
    this.mode = mode;
    this.all_slotted = all_slotted;
    this.feature_mapper = feature_mapper;
    this.has_icons = false;
    
    // Add message + action icons to tile's html.
    if (message) {
        this.has_icons = true;
        
        var 
            tile = this;
            canvas = this.html_elt.children()[0],
            message_div = $("<div/>").addClass("tile-message")
                            // -1 to account for border.
                            .css({'height': ERROR_PADDING-1, 'width': canvas.width}).prependTo(this.html_elt);
                                                        
        // Handle message; only message currently is that only the first N elements are displayed.
        var 
            num_features = data.length,
            more_down_icon = $("<a href='javascript:void(0);'/>").addClass("icon more-down")
                                .attr("title", "For speed, only the first " + num_features + " features in this region were obtained from server. Click to get more data including depth")
                                .tipsy( {gravity: 's'} ).appendTo(message_div),
            more_across_icon = $("<a href='javascript:void(0);'/>").addClass("icon more-across")
                                .attr("title", "For speed, only the first " + num_features + " features in this region were obtained from server. Click to get more data excluding depth")
                                .tipsy( {gravity: 's'} ).appendTo(message_div);

        // Set up actions for icons.
        more_down_icon.click(function() {
            // Mark tile as stale, request more data, and redraw track.
            tile.stale = true;
            track.data_manager.get_more_data(tile.low, tile.high, track.mode, tile.resolution, {}, track.data_manager.DEEP_DATA_REQ);
            $(".tipsy").hide();
            track.request_draw();
        }).dblclick(function(e) {
            // Do not propogate as this would normally zoom in.
            e.stopPropagation();
        });

        more_across_icon.click(function() {
            // Mark tile as stale, request more data, and redraw track.
            tile.stale = true;
            track.data_manager.get_more_data(tile.low, tile.high, track.mode, tile.resolution, {}, track.data_manager.BROAD_DATA_REQ);
            $(".tipsy").hide();
            track.request_draw();
        }).dblclick(function(e) {
            // Do not propogate as this would normally zoom in.
            e.stopPropagation();
        });
    }
};
extend(FeatureTrackTile.prototype, Tile.prototype);

/**
 * Sets up support for popups.
 */
FeatureTrackTile.prototype.predisplay_actions = function() {
    //
    // Add support for popups.
    //
    var tile = this,
        popups = {};
        
    // Only show popups in Pack mode.
    if (tile.mode !== "Pack") { return; }
    
    $(this.html_elt).hover( function() { 
        this.hovered = true; 
        $(this).mousemove();
    }, function() { 
        this.hovered = false; 
        // Clear popup if it is still hanging around (this is probably not needed) 
        $(this).parents(".track-content").children(".overlay").children(".feature-popup").remove();
    } ).mousemove(function (e) {
        // Use the hover plugin to get a delay before showing popup
        if ( !this.hovered ) { return; }
        // Get feature data for position.
        var 
            this_offset = $(this).offset(),
            offsetX = e.pageX - this_offset.left,
            offsetY = e.pageY - this_offset.top,
            feature_data = tile.feature_mapper.get_feature_data(offsetX, offsetY),
            feature_uid = (feature_data ? feature_data[0] : null);
        // Hide visible popup if not over a feature or over a different feature.
        $(this).parents(".track-content").children(".overlay").children(".feature-popup").each(function() {
            if ( !feature_uid || 
                 $(this).attr("id") !== feature_uid.toString() ) {
                $(this).remove();
            }
        });
            
        if (feature_data) {
            // Get or create popup.
            var popup = popups[feature_uid];
            if (!popup) {
                // Create feature's popup element.            
                var 
                    feature_uid = feature_data[0],
                    feature_dict = {
                        name: feature_data[3],
                        start: feature_data[1],
                        end: feature_data[2],
                        strand: feature_data[4]
                    },
                    filters = tile.track.filters_manager.filters,
                    filter;
                
                // Add filter values to feature dict.   
                for (var i = 0; i < filters.length; i++) {
                    filter = filters[i];
                    feature_dict[filter.name] = feature_data[filter.index];
                }
                
                // Build popup.
                
                var popup = $("<div/>").attr("id", feature_uid).addClass("feature-popup"),
                    table = $("<table/>"),
                    key, value, row;
                for (key in feature_dict) {
                    value = feature_dict[key];
                    row = $("<tr/>").appendTo(table);
                    $("<th/>").appendTo(row).text(key);
                    $("<td/>").attr("align", "left").appendTo(row)
                              .text(typeof(value) === 'number' ? round(value, 2) : value);
                }
                popup.append( $("<div class='feature-popup-inner'>").append( table ) ); 
                popups[feature_uid] = popup;
            }
            
            // Attach popup to track's overlay.
            popup.appendTo( $(this).parents(".track-content").children(".overlay") );
            
            // Offsets are within canvas, but popup must be positioned relative to parent element.
            // parseInt strips "px" from left, top measurements. +7 so that mouse pointer does not
            // overlap popup.
            var 
                popupX = offsetX + parseInt( tile.html_elt.css("left") ) - popup.width() / 2,
                popupY = offsetY + parseInt( tile.html_elt.css("top") ) + 7;
            popup.css("left", popupX + "px").css("top", popupY + "px")
        }
        else if (!e.isPropagationStopped()) {
            // Propogate event to other tiles because overlapping tiles prevent mousemove from being 
            // called on tiles under this tile.
            e.stopPropagation();
            $(this).siblings().each(function() {
                $(this).trigger(e);
            });
        }
    })
    .mouseleave(function() {
        $(this).parents(".track-content").children(".overlay").children(".feature-popup").remove();
    });
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
 * -------> VcfTrack
 */
var Track = function(view, container, obj_dict) {
    // For now, track's container is always view.
    extend(obj_dict, {
        drag_handle_class: "draghandle"
    });
    Drawable.call(this, view, container, obj_dict);
    
    //
    // Attribute init.
    //
    this.data_url = ('data_url' in obj_dict ? obj_dict.data_url : default_data_url);
    this.data_url_extra_params = {}
    this.data_query_wait = ('data_query_wait' in obj_dict ? obj_dict.data_query_wait : DEFAULT_DATA_QUERY_WAIT);
    this.dataset_check_url = converted_datasets_state_url;
    this.data_manager = ('data_manager' in obj_dict ? obj_dict.data_manager : new DataManager(DATA_CACHE_SIZE, this));
    
    // Height attributes: min height, max height, and visible height.
    this.min_height_px = 16;
    this.max_height_px = 800;
    this.visible_height_px = 0;
            
    //
    // Create content div, which is where track is displayed, and add to container if available.
    //
    this.content_div = $("<div class='track-content'>").appendTo(this.container_div);
    if (this.container) { 
        this.container.content_div.append(this.container_div);
        if ( !("resize" in obj_dict) || obj_dict.resize ) {
            this.add_resize_handle();
        }
    }
};

extend(Track.prototype, Drawable.prototype, {
    action_icons_def: [
        // Change track mode.
        {
            name: "mode_icon",
            title: "Set display mode",
            css_class: "chevron-expand",
            on_click_fn: function() {}
        },
        // Hide/show content.
        Drawable.prototype.action_icons_def[0],
        // Set track as overview.
        {
            name: "overview_icon",
            title: "Set as overview",
            css_class: "overview-icon",
            on_click_fn: function(track) {
                track.view.set_overview(track);
            }
        },
        // Edit config.
        Drawable.prototype.action_icons_def[1],
        // Toggle track filters.
        {
            name: "filters_icon",
            title: "Filters",
            css_class: "filters-icon",
            on_click_fn: function(drawable) {
                // TODO: update tipsy text.
                if (drawable.filters_manager.visible()) {
                    drawable.filters_manager.clear_filters();    
                }
                else {
                    drawable.filters_manager.init_filters();
                }
                drawable.filters_manager.toggle();
            }
        },
        // Toggle track tool.
        {
            name: "tools_icon",
            title: "Tool",
            css_class: "hammer",
            on_click_fn: function(track) {
                // TODO: update tipsy text.

                track.dynamic_tool_div.toggle();

                // Update track name.
                if (track.dynamic_tool_div.is(":visible")) {
                    track.set_name(track.name + track.tool_region_and_parameters_str());
                }
                else {
                    track.revert_name();
                }
                // HACK: name change modifies icon placement, which leaves tooltip incorrectly placed.
                $(".tipsy").remove();
            }
        },
        // Remove track.
        Drawable.prototype.action_icons_def[2]
    ],
    can_draw: function() {        
        if ( this.dataset_id && Drawable.prototype.can_draw.call(this) ) { 
            return true;
        }
        return false;
    },
    build_container_div: function () {
        return $("<div/>").addClass('track').attr("id", "track_" + this.id).css("position", "relative");
    },
    build_header_div: function() {
        var header_div = $("<div class='track-header'/>");
        if (this.view.editor) { this.drag_div = $("<div/>").addClass(this.drag_handle_class).appendTo(header_div); }
        this.name_div = $("<div/>").addClass("track-name").appendTo(header_div).text(this.name)
                        .attr( "id", this.name.replace(/\s+/g,'-').replace(/[^a-zA-Z0-9\-]/g,'').toLowerCase() );
        return header_div;
    },
    /**
     * Action to take during resize.
     */
    on_resize: function() {},
    /**
     * Add resizing handle to drawable's container_div.
     */
    add_resize_handle: function () {
        var track = this;
        var in_handle = false;
        var in_drag = false;
        var drag_control = $( "<div class='track-resize'>" )
        // Control shows on hover over track, stays while dragging
        $(track.container_div).hover( function() { 
            if ( track.content_visible ) {
                in_handle = true;
                drag_control.show(); 
            }
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
            $(track.tiles_div).css( 'height', new_height );
            track.visible_height_px = (track.max_height_px === new_height ? 0 : new_height);
            track.on_resize();
        }).bind( "dragend", function( e, d ) {
            track.tile_cache.clear();    
            in_drag = false;
            if (!in_handle) { drag_control.hide(); }
            track.config.values.height = track.visible_height_px;
            track.changed();
        }).appendTo(track.container_div);
    },
    /**
     * Set track's modes and update mode icon popup.
     */
    set_display_modes: function(new_modes, init_mode) {
        // Set modes, init mode.
        this.display_modes = new_modes;
        this.mode = (init_mode ? init_mode : 
                     (this.config && this.config.values['mode'] ? 
                      this.config.values['mode'] : this.display_modes[0])
                    );
        
        this.action_icons.mode_icon.attr("title", "Set display mode (now: " + this.mode + ")");

        // Setup popup menu for changing modes.
        var 
            track = this,
            mode_mapping = {};
        for (var i = 0, len = track.display_modes.length; i < len; i++) {
            var mode = track.display_modes[i];
            mode_mapping[mode] = function(mode) {
                return function() { 
                    track.change_mode(mode);
                    // HACK: the popup menu messes with the track's hover event, so manually show/hide
                    // icons div for now.
                    track.icons_div.show(); 
                    track.container_div.mouseleave(function() { track.icons_div.hide(); } ); };
            }(mode);
        }

        make_popupmenu(this.action_icons.mode_icon, mode_mapping);
    },
    build_action_icons: function() {
        Drawable.prototype.build_action_icons.call(this, this.action_icons_def);
        
        // Set up behavior for modes popup.
        if (this.display_modes !== undefined) {
            this.set_display_modes(this.display_modes);
        }
    },
    /**
     * Hide any elements that are part of the tracks contents area. Should
     * remove as approprite, the track will be redrawn by show_contents.
     */
    hide_contents: function () {
        // Hide tiles.
        this.tiles_div.hide();
        // Hide any y axis labels (common to several track types)
        this.container_div.find(".yaxislabel, .track-resize").hide()
    },
    show_contents: function() {
        // Show the contents div and labels (if present)
        this.tiles_div.show();
        this.container_div.find(".yaxislabel, .track-resize").show()
        // Request a redraw of the content
        this.request_draw();
    },
    /** 
     * Returns track type. 
     */
    get_type: function() {
        // Order is important: start with most-specific classes and go up the track hierarchy.
        if (this instanceof LabelTrack) {
            return "LabelTrack";
        }
        else if (this instanceof ReferenceTrack) {
            return "ReferenceTrack";
        }
        else if (this instanceof LineTrack) {
            return "LineTrack";
        }
        else if (this instanceof ReadTrack) {
            return "ReadTrack";
        }
        else if (this instanceof VcfTrack) {
            return "VcfTrack";
        }
        else if (this instanceof CompositeTrack) {
            return "CompositeTrack";
        }
        else if (this instanceof FeatureTrack) {
            return "FeatureTrack";
        }
        return "";
    },
    /**
     * Initialize and draw the track.
     */
    init: function() {
        var track = this;
        track.enabled = false;
        track.tile_cache.clear();    
        track.data_manager.clear();
        track.content_div.css("height", "auto");
        /*
        if (!track.content_div.text()) {
            track.content_div.text(DATA_LOADING);
        }
        */
        // Remove old track content (e.g. tiles, messages).
        track.tiles_div.children().remove();
        track.container_div.removeClass("nodata error pending");
        
        //
        // Tracks with no dataset id are handled differently.
        // FIXME: is this really necessary?
        //
        if (!track.dataset_id) {
            return;
        }
       
        // Get dataset state; if state is fine, enable and draw track. Otherwise, show message 
        // about track status.
        var init_deferred = $.Deferred();
        $.getJSON(this.dataset_check_url, { hda_ldda: track.hda_ldda, dataset_id: track.dataset_id, chrom: track.view.chrom}, 
                 function (result) {
            if (!result || result === "error" || result.kind === "error") {
                track.container_div.addClass("error");
                track.tiles_div.text(DATA_ERROR);
                if (result.message) {
                    var error_link = $(" <a href='javascript:void(0);'></a>").text("View error").click(function() {
                        show_modal( "Trackster Error", "<pre>" + result.message + "</pre>", { "Close" : hide_modal } );
                    });
                    track.tiles_div.append(error_link);
                }
            } else if (result === "no converter") {
                track.container_div.addClass("error");
                track.tiles_div.text(DATA_NOCONVERTER);
            } else if (result === "no data" || (result.data !== undefined && (result.data === null || result.data.length === 0))) {
                track.container_div.addClass("nodata");
                track.tiles_div.text(DATA_NONE);
            } else if (result === "pending") {
                track.container_div.addClass("pending");
                track.tiles_div.html(DATA_PENDING);
                //$("<img/>").attr("src", image_path + "/yui/rel_interstitial_loading.gif").appendTo(track.tiles_div);
                setTimeout(function() { track.init(); }, track.data_query_wait);
            } else if (result === "data" || result['status'] === "data") {
                if (result['valid_chroms']) {
                    track.valid_chroms = result['valid_chroms'];
                    track.update_icons();
                }
                track.tiles_div.text(DATA_OK);
                if (track.view.chrom) {
                    track.tiles_div.text("");
                    track.tiles_div.css( "height", track.visible_height_px + "px" );
                    track.enabled = true;
                    // predraw_init may be asynchronous, wait for it and then draw
                    $.when(track.predraw_init()).done(function() {
                        init_deferred.resolve();
                        track.container_div.removeClass("nodata error pending");
                        track.request_draw();
                    });
                }
                else {
                    init_deferred.resolve();
                }
            }
        });
        
        this.update_icons();
        return init_deferred;
    },
    /**
     * Additional initialization required before drawing track for the first time.
     */
    predraw_init: function() {}
});

var TiledTrack = function(view, container, obj_dict) {    
    Track.call(this, view, container, obj_dict);

    var track = this,
        view = track.view;
        
    // Make track moveable.
    moveable(track.container_div, track.drag_handle_class, ".group", track);
    
    // Attribute init.
    this.filters_manager = new FiltersManager(this, ('filters' in obj_dict ? obj_dict.filters : null));
    this.filters_available = false;
    this.tool = ('tool' in obj_dict && obj_dict.tool ? new Tool(this, obj_dict.tool, obj_dict.tool_state) : null);
    this.tile_cache = new Cache(TILE_CACHE_SIZE);
    
    if (this.header_div) {
        //
        // Setup filters.
        //
        this.set_filters_manager(this.filters_manager);
        
        //
        // Create dynamic tool div.
        //
        if (this.tool) {  
            this.dynamic_tool_div = this.tool.parent_div;
            this.header_div.after(this.dynamic_tool_div);
        }
    }
    
    // Add tiles_div, overlay_div to content_div.
    this.tiles_div = $("<div/>").addClass("tiles").appendTo(this.content_div);
    this.overlay_div = $("<div/>").addClass("overlay").appendTo(this.content_div);
    
    if (obj_dict.mode) {
        this.change_mode(obj_dict.mode);
    }
};
extend(TiledTrack.prototype, Drawable.prototype, Track.prototype, {
    action_icons_def: Track.prototype.action_icons_def.concat( [
        // Show more rows when all features are not slotted.
        {
            name: "show_more_rows_icon",
            title: "To minimize track height, not all feature rows are displayed. Click to display more rows.",
            css_class: "exclamation",
            on_click_fn: function(track) {
                $(".tipsy").remove();
                // HACKish: is it always reasonble to use view to get w_scale/current resolution?
                track.slotters[ track.view.resolution_px_b ].max_rows *= 2;
                track.request_draw(true);
            },
            hide: true
        }
    ] ),
    /**
     * Returns a copy of the track. The copy uses the same data manager so that the tracks can share data.
     */
    copy: function(container) {
        // Create copy.
        var obj_dict = this.to_dict();
        extend(obj_dict, {
            data_manager: this.data_manager
        });
        var new_track = new this.constructor(this.view, container, obj_dict);
        // Misc. init and return.
        new_track.change_mode(this.mode);
        new_track.enabled = this.enabled;
        return new_track;
    },
    /**
     * Set filters manager + HTML elements.
     */
    set_filters_manager: function(filters_manager) {
        this.filters_manager = filters_manager;
        this.header_div.after(this.filters_manager.parent_div);
    },
    /** 
     * Returns representation of object in a dictionary for easy saving. 
     * Use from_dict to recreate object.
     */
    to_dict: function() {
        return {
            "track_type": this.get_type(),
            "name": this.name,
            "hda_ldda": this.hda_ldda,
            "dataset_id": this.dataset_id,
            "prefs": this.prefs,
            "mode": this.mode,
            "filters": this.filters_manager.to_dict(),
            "tool_state": (this.tool ? this.tool.state_dict() : {})
        };
    },
    /**
     * Change track's mode.
     */
    change_mode: function(new_mode) {
        var track = this;
        // TODO: is it necessary to store the mode in two places (.mode and track_config)?
        track.mode = new_mode;
        track.config.values['mode'] = new_mode;
        track.tile_cache.clear();
        track.request_draw();
        this.action_icons.mode_icon.attr("title", "Set display mode (now: " + track.mode + ")");
        return track;
     },
    /**
     * Update track's buttons.
     */
    update_icons: function() {
        var track = this;
        
        //
        // Show/hide filter icon.
        //
        if (track.filters_available) {
            track.action_icons.filters_icon.show();
        }
        else {
            track.action_icons.filters_icon.hide();
        }
        
        //
        // Show/hide tool icon.
        //
        if (track.tool) {
            track.action_icons.tools_icon.show();
        }
        else {
            track.action_icons.tools_icon.hide();
        }
                        
        //
        // List chrom/contigs with data option.
        //
        /*
        if (track.valid_chroms) {
            track_dropdown["List chrom/contigs with data"] = function() {
                show_modal("Chrom/contigs with data", "<p>" + track.valid_chroms.join("<br/>") + "</p>", { "Close": function() { hide_modal(); } });
            };
        }
        */
    },
    /**
     * Generate a key for the tile cache.
     * TODO: create a TileCache object (like DataCache) and generate key internally.
     */
    _gen_tile_cache_key: function(width, w_scale, tile_index) { 
        return width + '_' + w_scale + '_' + tile_index;
    },
    /**
     * Request that track be drawn.
     */
    request_draw: function(force, clear_after) {
        this.view.request_redraw(false, force, clear_after, this);
    },
    /**
     * Actions to be taken before drawing.
     */
    before_draw: function() {},
    /**
     * Draw track. It is possible to force a redraw rather than use cached tiles and/or clear old 
     * tiles after drawing new tiles.
     * NOTE: this function should never be called directly; use request_draw() so that requestAnimationFrame 
     * can manage drawing.
     */
    _draw: function(force, clear_after) {
        if ( !this.can_draw() ) { return; }
        
        var low = this.view.low,
            high = this.view.high,
            range = high - low,
            width = this.view.container.width(),
            w_scale = this.view.resolution_px_b,
            resolution = this.view.resolution_b_px;

        // For overview, adjust high, low, resolution, and w_scale.
        if (this.is_overview) {
            low = this.view.max_low;
            high = this.view.max_high;
            resolution = Math.pow(RESOLUTION, Math.ceil( Math.log( (view.max_high - view.max_low) / TILE_SIZE ) / Math.log(RESOLUTION) ));
            w_scale = width / (view.max_high - view.max_low);
        }
        
        this.before_draw();

        //
        // Method for moving and/or removing tiles:
        // (a) mark all elements for removal using class 'remove'
        // (b) during tile drawing/placement, remove class for elements that are moved; 
        //     this occurs in show_tile()
        // (c) after drawing tiles, remove elements still marked for removal 
        //     (i.e. that still have class 'remove').
        //
        
        // Step (a) for (re)moving tiles.
        this.tiles_div.children().addClass("remove");

        var 
            // Index of first tile that overlaps visible region.
            tile_index = Math.floor( low / (resolution * TILE_SIZE) ),
            // If any tile could not be drawn yet, this will be set to false.
            all_tiles_drawn = true,
            drawn_tiles = [],
            is_tile = function(o) { return (o && 'track' in o) };
        // Draw tiles.
        while ( ( tile_index * TILE_SIZE * resolution ) < high ) {
            var draw_result = this.draw_helper( force, width, tile_index, resolution, this.tiles_div, w_scale );
            if ( is_tile(draw_result) ) {
                drawn_tiles.push( draw_result );
            } else {
                all_tiles_drawn = false;
            }
            tile_index += 1;
        }
        
        // Step (c) for (re)moving tiles when clear_after is false.
        if (!clear_after) { this.tiles_div.children(".remove").remove(); }
                
        // Use interval to check if tiles have been drawn. When all tiles are drawn, call post-draw actions.
        var track = this;
        if (all_tiles_drawn) {
            // Step (c) for (re)moving tiles when clear_after is true:
            this.tiles_div.children(".remove").remove();
            track.postdraw_actions(drawn_tiles, width, w_scale, clear_after);
        } 
    },
    /**
     * Actions to be taken after draw has been completed. Draw is completed when all tiles have been 
     * drawn/fetched and shown.
     */
    postdraw_actions: function(tiles, width, w_scale, clear_after) {
        var track = this;
                                
        //
        // If some tiles have icons, set padding of tiles without icons so features and rows align.
        //
        var icons_present = false;
        for (var tile_index = 0; tile_index < tiles.length; tile_index++) {
            if (tiles[tile_index].has_icons) {
                icons_present = true;
                break;
            }
        }
        if (icons_present) {
            for (var tile_index = 0; tile_index < tiles.length; tile_index++) {
                tile = tiles[tile_index];
                if (!tile.has_icons) {
                    // Need to align with other tile(s) that have icons.
                    tile.html_elt.css("padding-top", ERROR_PADDING);
                }
            }
        }        
    },
    /**
     * Retrieves from cache, draws, or sets up drawing for a single tile. Returns either a Tile object or a 
     * jQuery.Deferred object that is fulfilled when tile can be drawn again.
     */ 
    draw_helper: function(force, width, tile_index, resolution, parent_element, w_scale, kwargs) {
        var track = this,
            key = this._gen_tile_cache_key(width, w_scale, tile_index),
            tile_bounds = this._get_tile_bounds(tile_index, resolution),
            tile_low = tile_bounds[0],
            tile_high = tile_bounds[1];
            
        // Init kwargs if necessary to avoid having to check if kwargs defined.
        if (!kwargs) { kwargs = {}; }
                       
        // Check tile cache, if found show existing tile in correct position
        var tile = (force ? undefined : track.tile_cache.get(key));
        if (tile) { 
            track.show_tile(tile, parent_element, w_scale);
            return tile;
        }
                
        // Flag to track whether we can draw everything now 
        var can_draw_now = true
        
        // Get the track data, maybe a deferred
        var tile_data = track.data_manager.get_data( tile_low, tile_high, track.mode, resolution, track.data_url_extra_params );
        if ( is_deferred( tile_data ) ) {
            can_draw_now = false;
        }
        
        // Get seq data if needed, maybe a deferred
        var seq_data;
        if ( view.reference_track && w_scale > view.canvas_manager.char_width_px ) {
            seq_data = view.reference_track.data_manager.get_data(tile_low, tile_high, track.mode, resolution, view.reference_track.data_url_extra_params)
            if ( is_deferred( seq_data ) ) {
                can_draw_now = false;
            }
        }
                
        // If we can draw now, do so.
        if ( can_draw_now ) {
            // Set up and draw tile.
            extend(tile_data, kwargs[ 'more_tile_data' ] );
            
            // HACK: this is FeatureTrack-specific.
            // If track mode is Auto, determine mode and update.
            var mode = track.mode;
            if (mode === "Auto") {
                mode = track.get_mode(tile_data);
                track.update_auto_mode(mode);
            }
            
            // Draw canvas.
            var 
                canvas = track.view.canvas_manager.new_canvas(),
                tile_bounds = track._get_tile_bounds(tile_index, resolution),
                tile_low = tile_bounds[0],
                tile_high = tile_bounds[1],
                width = Math.ceil( (tile_high - tile_low) * w_scale ) + track.left_offset,
                height = track.get_canvas_height(tile_data, mode, w_scale, width);
            
            canvas.width = width;
            canvas.height = height;
            var ctx = canvas.getContext('2d');
            ctx.translate(this.left_offset, 0);
            var tile = track.draw_tile(tile_data, ctx, mode, resolution, tile_index, w_scale, seq_data);
            
            // Don't cache, show if no tile.
            if (tile !== undefined) {
                track.tile_cache.set(key, tile);
                track.show_tile(tile, parent_element, w_scale);
            }
            return tile;
        }
         
        // Can't draw now, so trigger another redraw when the data is ready
        var can_draw = $.Deferred();
        $.when( tile_data, seq_data ).then( function() {
            view.request_redraw(false, false, false, track);
            can_draw.resolve();
        });
        
        // Returned Deferred is resolved when tile can be drawn.
        return can_draw;
    },
    /**
     * Returns canvas height needed to display data; return value is an integer that denotes the
     * number of pixels required.
     */
    get_canvas_height: function(result, mode, w_scale, canvas_width) {
        return this.visible_height_px;
    },
    /**
     * Draw a track tile.
     * @param result result from server
     * @param ctx canvas context to draw on
     * @param mode mode to draw in
     * @param resolution view resolution
     * @param tile_index index of tile to be drawn
     * @param w_scale pixels per base
     * @param ref_seq reference sequence data
     */
    draw_tile: function(result, ctx, mode, resolution, tile_index, w_scale, ref_seq) {
        console.log("Warning: TiledTrack.draw_tile() not implemented.");
    },
    /**
     * Show track tile and perform associated actions. Showing tile may actually move
     * an existing tile rather than reshowing it.
     */
    show_tile: function(tile, parent_element, w_scale) {
        var 
            track = this,
            tile_element = tile.html_elt;
        
        //
        // Show/move tile element.
        //
        
        tile.predisplay_actions();
      
        // Position tile element based on current viewport.
        var left = ( tile.low - (this.is_overview? this.view.max_low : this.view.low) ) * w_scale;
        if (this.left_offset) {
            left -= this.left_offset;
        }
        tile_element.css({ position: 'absolute', top: 0, left: left, height: '' });
        
        if ( tile_element.hasClass("remove") ) {
            // Step (b) for (re)moving tiles. See _draw() function for description of algorithm
            // for removing tiles.
            tile_element.removeClass("remove");
        }
        else {
            // Showing new tile.
            parent_element.append(tile_element);
        }
        
        track.after_show_tile(tile);
    },
    /**
     * Actions to be taken after showing tile.
     */
    after_show_tile: function(tile) {},
    /**
     * Returns tile bounds--tile low and tile high--based on a tile index. Return value is an array 
     * with values tile_low and tile_high.
     */ 
    _get_tile_bounds: function(tile_index, resolution) {
        var tile_low = Math.floor( tile_index * TILE_SIZE * resolution ),
            tile_length = Math.ceil( TILE_SIZE * resolution ),
            // Tile high cannot be larger than view.max_high, which the chromosome length.
            tile_high = (tile_low + tile_length <= this.view.max_high ? tile_low + tile_length : this.view.max_high);
        return [tile_low, tile_high];
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
     * Returns true if data is compatible with a given mode. Defaults to true because, for many tracks,
     * all data is compatible with all modes.
     */
    data_and_mode_compatible: function(data, mode) {
        return true;
    },
    /**
     * Returns true if data can be subsetted. Defaults to false to ensure data is fetched when needed.
     */
    can_subset: function(data) {
        return false;  
    },
    /**
     * Set up track to receive tool data.
     */
    init_for_tool_data: function() {
        // Set up track to fetch initial data from raw data URL when the dataset--not the converted datasets--
        // is ready.
        this.data_url = raw_data_url;
        this.data_query_wait = 1000;
        this.dataset_check_url = dataset_state_url;
        
        //
        // Set up one-time, post-draw to clear tool execution settings.
        //
        this.normal_postdraw_actions = this.postdraw_actions;
        this.postdraw_actions = function(tiles, width, w_scale, clear_after) {
            var self = this;
            
            // Do normal postdraw init.
            self.normal_postdraw_actions(tiles, width, w_scale, clear_after);
            
            // Tool-execution specific post-draw init:
            
            // Reset dataset state, wait time.
            self.dataset_state_url = converted_datasets_state_url;
            self.data_query_wait = DEFAULT_DATA_QUERY_WAIT;

            // Reset data URL when dataset indexing has completed/when not pending.
            $.when(
                // Set up deferred to check dataset state until it is not pending.
                server_state_deferred(self.dataset_state_url,
                                      {dataset_id : self.dataset_id, hda_ldda: self.hda_ldda},
                                      self.data_query_wait,
                                      function(result) { return result !== "pending" })
            ).then(function() {
                // Dataset is indexed, so use default data URL.
                self.data_url = default_data_url;
            });
                        
            // Reset post-draw actions function.
            self.postdraw_actions = self.normal_postdraw_actions;
        };
    }
});

var LabelTrack = function (view, container) {
    var obj_dict = {
        resize: false
    };
    Track.call(this, view, container, obj_dict);
    this.container_div.addClass( "label-track" );
};
extend(LabelTrack.prototype, Track.prototype, {
    build_header_div: function() {},
    init: function() {
        // Enable by default because there should always be data when drawing track.
        this.enabled = true;  
    },
    _draw: function() {
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

/**
 * A tiled track composed of multiple other tracks.
 */
var CompositeTrack = function(view, container, obj_dict) {
    TiledTrack.call(this, view, container, obj_dict);
    
    // Init drawables; each drawable is a copy so that config/preferences 
    // are independent of each other. Also init left offset.
    this.drawables = [];
    this.left_offset = 0;
    if ('drawables' in obj_dict) {
        var drawable;
        for (var i = 0; i < obj_dict.drawables.length; i++) {
            drawable = obj_dict.drawables[i];
            this.drawables[i] = object_from_template(drawable);
            
            // Track's left offset is the max of all tracks.
            if (drawable.left_offset > this.left_offset) {
                this.left_offset = drawable.left_offset;
            }
        }
        this.enabled = true;
    }
    
    // HACK: modes should be static class vars for most tracks and should update as
    // needed for CompositeTracks
    if (this.drawables.length !== 0) {
        this.set_display_modes(this.drawables[0].display_modes, this.drawables[0].mode);
    }
    
    this.update_icons();
    
    // HACK: needed for saving object for now. Need to generalize get_type() to all Drawables and use
    // that for object type.
    this.obj_type = "CompositeTrack";
};

extend(CompositeTrack.prototype, TiledTrack.prototype, {
    action_icons_def:
    [
        // Create composite track from group's tracks.
        {
            name: "composite_icon",
            title: "Show individual tracks",
            css_class: "layers-stack",
            on_click_fn: function(track) {
                $(".tipsy").remove();
                track.show_group();
            }
        }
    ].concat(TiledTrack.prototype.action_icons_def),
    // HACK: CompositeTrack should inherit from DrawableCollection as well.
    /** 
     * Returns representation of object in a dictionary for easy saving. 
     * Use from_dict to recreate object.
     */
    to_dict: DrawableCollection.prototype.to_dict,
    add_drawable: DrawableCollection.prototype.add_drawable,
    unpack_drawables: DrawableCollection.prototype.unpack_drawables,
    change_mode: function(new_mode) {
        TiledTrack.prototype.change_mode.call(this, new_mode);
        for (var i = 0; i < this.drawables.length; i++) {
            this.drawables[i].change_mode(new_mode);
        }
    },
    /**
     * Initialize component tracks and draw composite track when all components are initialized.
     */
    init: function() {
        // Init components.
        var init_deferreds = [];
        for (var i = 0; i < this.drawables.length; i++) {
            init_deferreds.push(this.drawables[i].init());
        }
        
        // Draw composite when all tracks available.
        var track = this;
        $.when.apply($, init_deferreds).then(function() {
            track.enabled = true;
            track.request_draw();
        });
    },
    update_icons: function() {
        // For now, hide filters and tool.
        this.action_icons.filters_icon.hide();
        this.action_icons.tools_icon.hide();  
    },
    can_draw: Drawable.prototype.can_draw,
    draw_helper: function(force, width, tile_index, resolution, parent_element, w_scale, kwargs) {
        // FIXME: this function is similar to TiledTrack.draw_helper -- can the two be merged/refactored?
        var track = this,
            key = this._gen_tile_cache_key(width, w_scale, tile_index),
            tile_bounds = this._get_tile_bounds(tile_index, resolution),
            tile_low = tile_bounds[0],
            tile_high = tile_bounds[1];
            
        // Init kwargs if necessary to avoid having to check if kwargs defined.
        if (!kwargs) { kwargs = {}; }
                       
        // Check tile cache, if found show existing tile in correct position
        var tile = (force ? undefined : track.tile_cache.get(key));
        if (tile) { 
            track.show_tile(tile, parent_element, w_scale);
            return tile;
        }
                
        // Try to get drawables' data.
        var all_data = [],
            track,
            // Flag to track whether we can draw everything now 
            can_draw_now = true,
            tile_data,
            seq_data;
        for (var i = 0; i < this.drawables.length; i++) {
            track = this.drawables[i];
            // Get the track data, maybe a deferred.
            tile_data = track.data_manager.get_data( tile_low, tile_high, track.mode, resolution, track.data_url_extra_params );
            if ( is_deferred( tile_data ) ) {
                can_draw_now = false;
            }
            all_data.push(tile_data);

            // Get seq data if needed, maybe a deferred.
            seq_data = null;
            if ( view.reference_track && w_scale > view.canvas_manager.char_width_px ) {
                seq_data = view.reference_track.data_manager.get_data(tile_low, tile_high, track.mode, resolution, view.reference_track.data_url_extra_params)
                if ( is_deferred( seq_data ) ) {
                    can_draw_now = false;
                }
            }
            all_data.push(seq_data);
        }
                
        // If we can draw now, do so.
        if ( can_draw_now ) {
            // Set up and draw tile.
            extend(tile_data, kwargs[ 'more_tile_data' ] );
            
            this.tile_predraw_init();
            
            var 
                canvas = track.view.canvas_manager.new_canvas(),
                tile_bounds = track._get_tile_bounds(tile_index, resolution),
                tile_low = tile_bounds[0],
                tile_high = tile_bounds[1],
                all_data_index = 0,
                width = Math.ceil( (tile_high - tile_low) * w_scale ) + this.left_offset,
                height = 0,
                track_modes = [];
                
            // Get max height for all tracks and record track modes.
            var track_canvas_height = 0;
            for (var i = 0; i < this.drawables.length; i++, all_data_index += 2) {
                track = this.drawables[i];
                tile_data = all_data[ all_data_index ];

                // HACK: this is FeatureTrack-specific.
                // If track mode is Auto, determine mode and update.
                var mode = track.mode;
                if (mode === "Auto") {
                    mode = track.get_mode(tile_data);
                    track.update_auto_mode(mode);
                }
                track_modes.push(mode)

                track_canvas_height = track.get_canvas_height(tile_data, mode, w_scale, width);
                if (track_canvas_height > height) { height = track_canvas_height; }
            }
            
            //
            // Draw all tracks on a single tile.
            //
            canvas.width = width;
            // Height is specified in kwargs or is the height found above.
            canvas.height = (kwargs['height'] ? kwargs['height'] : height);
            all_data_index = 0;
            var ctx = canvas.getContext('2d');
            ctx.translate(this.left_offset, 0);
            ctx.globalAlpha = 0.5;
            ctx.globalCompositeOperation = "source-over";
            for (var i = 0; i < this.drawables.length; i++, all_data_index += 2) {
                track = this.drawables[i];
                tile_data = all_data[ all_data_index ];
                seq_data = all_data[ all_data_index + 1 ];
                tile = track.draw_tile(tile_data, ctx, track_modes[i], resolution, tile_index, w_scale, seq_data);
            }
            
            // Don't cache, show if no tile.
            this.tile_cache.set(key, tile);
            this.show_tile(tile, parent_element, w_scale);
            return tile;
        }
         
        // Can't draw now, so trigger another redraw when the data is ready
        var can_draw = $.Deferred(),
            track = this;
        $.when.apply($, all_data).then(function() {
            view.request_redraw(false, false, false, track);
            can_draw.resolve();
        });
        
        // Returned Deferred that is resolved when tile can be drawn.
        return can_draw;
    },
    /**
     * Replace this track with group that includes individual tracks.
     */
    show_group: function() {
        // Create group with individual tracks.
        var 
            group = new DrawableGroup(this.view, this.container, {
                name: this.name
            }),
            track;
        for (var i = 0; i < this.drawables.length; i++) {
            track = this.drawables[i]
            group.add_drawable(track);
            track.container = group;
            group.content_div.append(track.container_div);
        }
        
        // Replace track with group.
        var index = this.container.replace_drawable(this, group, true);
        group.request_draw();
    },
    /**
     * Actions taken before drawing a tile.
     */
    tile_predraw_init: function() {
        //
        // Set min, max for LineTracks to be largest min, max.
        //
        
        // Get smallest min, biggest max.
        var 
            min = Number.MAX_VALUE,
            max = -min,
            track;
        for (var i = 0; i < this.drawables.length; i++) {
            track = this.drawables[i];
            if (track instanceof LineTrack) {
                if (track.prefs.min_value < min) {
                    min = track.prefs.min_value
                }
                if (track.prefs.max_value > max) {
                    max = track.prefs.max_value
                }
            }
        }
        
        // Set all tracks to smallest min, biggest max.
        for (var i = 0; i < this.drawables.length; i++) {
            track = this.drawables[i];
            track.prefs.min_value = min;
            track.prefs.max_value = max;
        }
    },
    /**
     * Actions to be taken after draw has been completed. Draw is completed when all tiles have been 
     * drawn/fetched and shown.
     */
    postdraw_actions: function(tiles, width, w_scale, clear_after) {
        TiledTrack.prototype.postdraw_actions.call(this, tiles, width, w_scale, clear_after);
        
        // All tiles must be the same height in order to draw LineTracks, so redraw tiles as needed.
        var max_height = -1;
        for (var i = 0; i < tiles.length; i++) {
            var height = tiles[i].html_elt.find("canvas").height();
            if (height > max_height) {
                max_height = height;
            }
        }
        
        for (var i = 0; i < tiles.length; i++) {
            var tile = tiles[i];
            if (tile.html_elt.find("canvas").height() !== max_height) {
                this.draw_helper(true, width, tile.index, tile.resolution, tile.html_elt.parent(), w_scale, { height: max_height } );
                tile.html_elt.remove();
            }
        }        
    }
});

var ReferenceTrack = function (view) {
    TiledTrack.call(this, view, { content_div: view.top_labeltrack, resize: false }, {});
    
    view.reference_track = this;
    this.left_offset = 200;
    this.visible_height_px = 12;
    this.container_div.addClass("reference-track");
    this.content_div.css("background", "none");
    this.content_div.css("min-height", "0px");
    this.content_div.css("border", "none");
    this.data_url = reference_url;
    this.data_url_extra_params = {dbkey: view.dbkey};
    this.data_manager = new ReferenceTrackDataManager(DATA_CACHE_SIZE, this, false);
    this.hide_contents();
};
extend(ReferenceTrack.prototype, Drawable.prototype, TiledTrack.prototype, {
    build_header_div: function() {},
    init: function() {
        this.data_manager.clear();
        // Enable by default because there should always be data when drawing track.
        this.enabled = true;
    },
    can_draw: Drawable.prototype.can_draw,
    /**
     * Draw ReferenceTrack tile.
     */
    draw_tile: function(seq, ctx, mode, resolution, tile_index, w_scale) {
        var track = this;        
        
        if (w_scale > this.view.canvas_manager.char_width_px) {
            if (seq.data === null) {
                this.hide_contents();
                return;
            }
            var canvas = ctx.canvas;
            ctx.font = ctx.canvas.manager.default_font;
            ctx.textAlign = "center";
            seq = seq.data;
            for (var c = 0, str_len = seq.length; c < str_len; c++) {
                var c_start = Math.floor(c * w_scale);
                ctx.fillText(seq[c], c_start, 10);
            }
            this.show_contents();
            return new Tile(track, tile_index, resolution, canvas, seq);
        }
        this.hide_contents();
    }
});

var LineTrack = function (view, container, obj_dict) {
    var track = this;
    this.display_modes = ["Histogram", "Line", "Filled", "Intensity"];
    this.mode = "Histogram";
    TiledTrack.call(this, view, container, obj_dict);
       
    this.hda_ldda = obj_dict.hda_ldda;
    this.dataset_id = obj_dict.dataset_id;
    this.original_dataset_id = this.dataset_id;
    this.left_offset = 0;

    // Define track configuration
    this.config = new DrawableConfig( {
        track: this,
        params: [
            { key: 'name', label: 'Name', type: 'text', default_value: this.name },
            { key: 'color', label: 'Color', type: 'color', default_value: get_random_color() },
            { key: 'min_value', label: 'Min Value', type: 'float', default_value: undefined },
            { key: 'max_value', label: 'Max Value', type: 'float', default_value: undefined },
            { key: 'mode', type: 'string', default_value: this.mode, hidden: true },
            { key: 'height', type: 'int', default_value: 32, hidden: true }
        ], 
        saved_values: obj_dict.prefs,
        onchange: function() {
            track.set_name(track.prefs.name);
            track.vertical_range = track.prefs.max_value - track.prefs.min_value;
            track.set_min_value(track.prefs.min_value);
            track.set_max_value(track.prefs.max_value);
        }
    });

    this.prefs = this.config.values;
    this.visible_height_px = this.config.values.height;
    this.vertical_range = this.config.values.max_value - this.config.values.min_value;
};
extend(LineTrack.prototype, Drawable.prototype, TiledTrack.prototype, {
    /**
     * Action to take during resize.
     */
    on_resize: function() {
        this.request_draw(true);
    },
    /**
     * Set track minimum value.
     */
    set_min_value: function(new_val) {
        this.prefs.min_value = new_val;
        $('#linetrack_' + this.dataset_id + '_minval').text(this.prefs.min_value);
        this.tile_cache.clear();
        this.request_draw();
    },
    /**
     * Set track maximum value.
     */
    set_max_value: function(new_val) {
        this.prefs.max_value = new_val;
        $('#linetrack_' + this.dataset_id + '_maxval').text(this.prefs.max_value);
        this.tile_cache.clear();
        this.request_draw();
    },
    predraw_init: function() {
        var track = this;
        
        track.vertical_range = undefined;
        return $.getJSON( track.data_url, {  stats: true, chrom: track.view.chrom, low: null, high: null,
                                        hda_ldda: track.hda_ldda, dataset_id: track.dataset_id }, function(result) {
            track.container_div.addClass( "line-track" );
            var data = result.data;
            if ( isNaN(parseFloat(track.prefs.min_value)) || isNaN(parseFloat(track.prefs.max_value)) ) {
                // Compute default minimum and maximum values
                var min_value = data.min
                var max_value = data.max
                // If mean and sd are present, use them to compute a ~95% window
                // but only if it would shrink the range on one side
                min_value = Math.floor( Math.min( 0, Math.max( min_value, data.mean - 2 * data.sd ) ) )
                max_value = Math.ceil( Math.max( 0, Math.min( max_value, data.mean + 2 * data.sd ) ) )
                // Update the prefs
                track.prefs.min_value = min_value;
                track.prefs.max_value = max_value;
                // Update the config
                // FIXME: we should probably only save this when the user explicately sets it
                //        since we lose the ability to compute it on the fly (when changing 
                //        chromosomes for example).
                $('#track_' + track.dataset_id + '_minval').val(track.prefs.min_value);
                $('#track_' + track.dataset_id + '_maxval').val(track.prefs.max_value);
            }
            track.vertical_range = track.prefs.max_value - track.prefs.min_value;
            track.total_frequency = data.total_frequency;
        
            // Draw y-axis labels if necessary
            track.container_div.find(".yaxislabel").remove();
            
            // Add min, max labels.
            var 
            min_label = $("<div/>").text(round(track.prefs.min_value, 3)).make_text_editable({
                num_cols: 6,
                on_finish: function(new_val) {
                    $(".tipsy").remove();
                    var new_val = parseFloat(new_val);
                    if (!isNaN(new_val)) {
                        track.set_min_value(new_val);
                    }
                },
                help_text: "Set min value"
            }).addClass('yaxislabel bottom').attr("id", 'linetrack_' + track.dataset_id + '_minval')
              .prependTo(track.container_div),
            max_label = $("<div/>").text(round(track.prefs.max_value, 3)).make_text_editable({
                  num_cols: 6,
                  on_finish: function(new_val) {
                      $(".tipsy").remove();
                      var new_val = parseFloat(new_val);
                      if (!isNaN(new_val)) {
                          track.set_max_value(new_val);
                      }
                  },
                  help_text: "Set max value"
              }).addClass('yaxislabel top').attr("id", 'linetrack_' + track.dataset_id + '_maxval')
                .prependTo(track.container_div);
        });
    },
    /**
     * Draw LineTrack tile.
     */
    draw_tile: function(result, ctx, mode, resolution, tile_index, w_scale) {
        // Paint onto canvas.
        var 
            canvas = ctx.canvas,
            tile_bounds = this._get_tile_bounds(tile_index, resolution),
            tile_low = tile_bounds[0],
            tile_high = tile_bounds[1],
            painter = new painters.LinePainter(result.data, tile_low, tile_high, this.prefs, mode);
        painter.draw(ctx, canvas.width, canvas.height, w_scale);
        
        return new Tile(this, tile_index, resolution, canvas, result.data);
    },
    /**
     * LineTrack data cannot currently be subsetted.
     */
    can_subset: function(data) {
        return false;
    },
});

var FeatureTrack = function(view, container, obj_dict) {
    //
    // Preinitialization: do things that need to be done before calling Track and TiledTrack
    // initialization code.
    //
    var track = this;
    this.display_modes = ["Auto", "Histogram", "Dense", "Squish", "Pack"];
    
    //
    // Initialization.
    //    
    TiledTrack.call(this, view, container, obj_dict);

    // Define and restore track configuration.
    var 
        block_color = get_random_color(),
        reverse_strand_color = get_random_color( [ block_color, "#ffffff" ] );
    this.config = new DrawableConfig( {
        track: this,
        params: [
            { key: 'name', label: 'Name', type: 'text', default_value: this.name },
            { key: 'block_color', label: 'Block color', type: 'color', default_value: block_color },
            { key: 'reverse_strand_color', label: 'Antisense strand color', type: 'color', default_value: reverse_strand_color },
            { key: 'label_color', label: 'Label color', type: 'color', default_value: 'black' },
            { key: 'show_counts', label: 'Show summary counts', type: 'bool', default_value: true, 
              help: 'Show the number of items in each bin when drawing summary histogram' },
            { key: 'histogram_max', label: 'Histogram maximum', type: 'float', default_value: null, help: 'clear value to set automatically' },
            { key: 'connector_style', label: 'Connector style', type: 'select', default_value: 'fishbones',
                options: [ { label: 'Line with arrows', value: 'fishbone' }, { label: 'Arcs', value: 'arcs' } ] },
            { key: 'mode', type: 'string', default_value: this.mode, hidden: true },
            { key: 'height', type: 'int', default_value: this.visible_height_px, hidden: true}
        ], 
        saved_values: obj_dict.prefs,
        onchange: function() {
            track.set_name(track.prefs.name);
            track.tile_cache.clear();
            track.set_painter_from_config();
            track.request_draw();
        }
    });
    this.prefs = this.config.values;
    this.visible_height_px = this.config.values.height;
        
    this.container_div.addClass( "feature-track" );
    this.hda_ldda = obj_dict.hda_ldda;
    this.dataset_id = obj_dict.dataset_id;
    this.original_dataset_id = obj_dict.dataset_id;
    this.show_labels_scale = 0.001;
    this.showing_details = false;
    this.summary_draw_height = 30;
    this.slotters = {};
    this.start_end_dct = {};
    this.left_offset = 200;

    // this.painter = painters.LinkedFeaturePainter;
    this.set_painter_from_config();
};
extend(FeatureTrack.prototype, Drawable.prototype, TiledTrack.prototype, {
    set_painter_from_config: function() {
        if ( this.config.values['connector_style'] === 'arcs' ) {
            this.painter = painters.ArcLinkedFeaturePainter;
        } else {
            this.painter = painters.LinkedFeaturePainter;
        }
    },
    /**
     * Actions to be taken before drawing.
     */
    before_draw: function() {
        // Clear because this is set when drawing.
        this.max_height_px = 0;
    },
    /**
     * Actions to be taken after showing tile.
     */
    after_show_tile: function(tile) {
        // Update max height based on current tile.
        this.max_height_px = Math.max(this.max_height_px, tile.html_elt.height());
        
        // Update height for all tiles based on max height.
        tile.html_elt.parent().children().css("height", this.max_height_px + "px");
        
        // Update track height based on max height and visible height.
        var track_height = this.max_height_px;
        if (this.visible_height_px !== 0) {
            track_height = Math.min(this.max_height_px, this.visible_height_px);
        }
        this.tiles_div.css("height", track_height + "px");    
    },
    /**
     * Actions to be taken after draw has been completed. Draw is completed when all tiles have been 
     * drawn/fetched and shown.
     */
    postdraw_actions: function(tiles, width, w_scale, clear_after) {
        TiledTrack.prototype.postdraw_actions.call(this, tiles, clear_after);
        
        var track = this;
                
        // If mode is Histogram and tiles do not share max, redraw tiles as necessary using new max.
        if (track.mode === "Histogram") {
            // Get global max.
            var global_max = -1;
            for (var i = 0; i < tiles.length; i++) {
                var cur_max = tiles[i].max_val;
                if (cur_max > global_max) {
                    global_max = cur_max;
                }
            }
            
            for (var i = 0; i < tiles.length; i++) {
                var tile = tiles[i];
                if (tile.max_val !== global_max) {
                    tile.html_elt.remove();
                    track.draw_helper(true, width, tile.index, tile.resolution, tile.html_elt.parent(), w_scale, { more_tile_data: { max: global_max } } );
                }
            }
        }                
        
        //
        // Update filter attributes, UI.
        //

        // Update filtering UI.
        if (track.filters_manager) {
            var filters = track.filters_manager.filters;
            for (var f = 0; f < filters.length; f++) {
                filters[f].update_ui_elt();
            }

            // Determine if filters are available; this is based on the tiles' data.
            // Criteria for filter to be available: (a) it is applicable to tile data and (b) filter min != filter max.
            var filters_available = false,
                example_feature,
                filter;
            for (var i = 0; i < tiles.length; i++) {
                if (tiles[i].data.length) {
                    example_feature = tiles[i].data[0];
                    for (var f = 0; f < filters.length; f++) {
                        filter = filters[f];
                        if ( filter.applies_to(example_feature) && 
                             filter.min !== filter.max ) {
                            filters_available = true;
                            break;
                        }
                    }
                }
            }

            // If filter availability changed, hide filter div if necessary and update menu.
            if (track.filters_available !== filters_available) {
                track.filters_available = filters_available;
                if (!track.filters_available) {
                    track.filters_manager.hide();
                }
                track.update_icons();
            }
        }
        
        //
        // If using SummaryTree tiles, show max and make it editable.
        //
        this.container_div.find(".yaxislabel").remove();
        var first_tile = tiles[0];
        if (first_tile instanceof SummaryTreeTile) {
            var max_val = (this.prefs.histogram_max ? this.prefs.histogram_max : first_tile.max_val),
                max_label = $("<div/>").text(max_val).make_text_editable({
                    num_cols: 12,
                    on_finish: function(new_val) {
                        $(".tipsy").remove();
                        var new_val = parseFloat(new_val);
                        track.prefs.histogram_max = (!isNaN(new_val) ? new_val : null);
                        track.tile_cache.clear();
                        track.request_draw();
                    },
                    help_text: "Set max value; leave blank to use default"
                }).addClass('yaxislabel top').css("color", this.prefs.label_color);
            this.container_div.prepend(max_label);
        }
        
        //
        // If not all features slotted, show icon for showing more rows (slots).
        //
        if (first_tile instanceof FeatureTrackTile) {
            var all_slotted = true;
            for (var i = 0; i < tiles.length; i++) {
                if (!tiles[i].all_slotted) {
                    all_slotted = false;
                    break;
                }
            }
            if (!all_slotted) {
                this.action_icons.show_more_rows_icon.show();
            }
            else {
                this.action_icons.show_more_rows_icon.hide();
            }
        }
        else {
            this.action_icons.show_more_rows_icon.hide();
        }
    },
    update_auto_mode: function( mode ) {
        var mode;
        if ( this.mode === "Auto" ) {
            if ( mode === "no_detail" ) {
                mode = "feature spans";
            } else if ( mode === "summary_tree" ) {
                mode = "coverage histogram";
            }
            this.action_icons.mode_icon.attr("title", "Set display mode (now: Auto/" + mode + ")");
        }
    },
    /**
     * Place features in slots for drawing (i.e. pack features).
     * this.slotters[level] is created in this method. this.slotters[level]
     * is a Slotter object. Returns the number of slots used to pack features.
     */
    incremental_slots: function(level, features, mode) {
        
        // Get/create incremental slots for level. If display mode changed,
        // need to create new slots.
        
        var dummy_context = this.view.canvas_manager.dummy_context,
            slotter = this.slotters[level];
        if (!slotter || (slotter.mode !== mode)) {
            slotter = new (slotting.FeatureSlotter)( level, mode, MAX_FEATURE_DEPTH, function ( x ) { return dummy_context.measureText( x ) } );
            this.slotters[level] = slotter;
        }

        return slotter.slot_features( features );
    },
    /**
     * Given feature data, returns summary tree data. Feature data must be sorted by start 
     * position. Return value is a dict with keys 'data', 'delta' (bin size) and 'max.' Data
     * is a two-item list; first item is bin start, second is bin's count.
     */
    get_summary_tree_data: function(data, low, high, num_bins) {
        if (num_bins > high - low) {
            num_bins = high - low;
        }
        var bin_size = Math.floor((high - low)/num_bins),
            bins = [],
            max_count = 0;
            
        /*    
        // For debugging:
        for (var i = 0; i < data.length; i++)
            console.log("\t", data[i][1], data[i][2], data[i][3]);
        */
        
        //
        // Loop through bins, counting data for each interval.
        //
        var data_index_start = 0,
            data_index = 0,
            data_interval,
            bin_index = 0,
            bin_interval = [], 
            cur_bin,
            overlap;
            
        // Set bin interval.
        var set_bin_interval = function(interval, low, bin_index, bin_size) {
            interval[0] = low + bin_index * bin_size;
            interval[1] = low + (bin_index + 1) * bin_size;
        };
        
        // Loop through bins, data to compute bin counts. Only compute bin counts as long
        // as there is data.
        while (bin_index < num_bins && data_index_start !== data.length) {
            // Find next bin that has data.
            var bin_has_data = false;
            for (; bin_index < num_bins && !bin_has_data; bin_index++) {
                set_bin_interval(bin_interval, low, bin_index, bin_size);
                // Loop through data and break if data found that goes in bin.
                for (data_index = data_index_start; data_index < data.length; data_index++) {
                    data_interval = data[data_index].slice(1, 3);
                    if (is_overlap(data_interval, bin_interval)) {
                        bin_has_data = true;
                        break;
                    }
                }
                // Break from bin loop if this bin has data.
                if (bin_has_data) {
                    break;
                }
            }
            
            // Set start index to current data, which is the first to overlap with this bin
            // and perhaps with later bins.
            data_start_index = data_index;
            
            // Count intervals that overlap with bin.
            bins[bins.length] = cur_bin = [bin_interval[0], 0];
            for (; data_index < data.length; data_index++) {
                data_interval = data[data_index].slice(1, 3);
                if (is_overlap(data_interval, bin_interval)) {
                    cur_bin[1]++;
                }
                else { break; }
            }
            
            // Update max count.
            if (cur_bin[1] > max_count) {
                max_count = cur_bin[1];
            }
            
            // Go to next bin.
            bin_index++;
        }
        return {max: max_count, delta: bin_size, data: bins};
    },
    /**
     * Returns appropriate display mode based on data.
     */
    get_mode: function(data) {
        if (data.dataset_type === "summary_tree") {
            mode = "summary_tree";
        } 
        // HACK: use no_detail mode track is in overview to prevent overview from being too large.
        else if (data.extra_info === "no_detail" || this.is_overview) {
            mode = "no_detail";
        } 
        else {
            // Choose b/t Squish and Pack.
            // Proxy measures for using Squish: 
            // (a) error message re: limiting number of features shown; 
            // (b) X number of features shown;
            // (c) size of view shown.
            // TODO: cannot use (a) and (b) because it requires coordinating mode across tiles;
            // fix this so that tiles are redrawn as necessary to use the same mode.
            //if ( (result.message && result.message.match(/^Only the first [\d]+/)) ||
            //     (result.data && result.data.length > 2000) ||
            //var data = result.data;
            // if ( (data.length && data.length < 4) ||
            //      (this.view.high - this.view.low > MIN_SQUISH_VIEW_WIDTH) ) {
            if ( this.view.high - this.view.low > MIN_SQUISH_VIEW_WIDTH ) {
                mode = "Squish";
            } else {
                mode = "Pack";
            }
        }
        return mode;
    },
    /**
     * Returns canvas height needed to display data; return value is an integer that denotes the
     * number of pixels required.
     */
    get_canvas_height: function(result, mode, w_scale, canvas_width) {
        if (mode === "summary_tree" || mode === "Histogram") {
            // Extra padding at top of summary tree so label does not overlap data.
            return this.summary_draw_height;
        }
        else {
            // All other modes require slotting.
            var rows_required = this.incremental_slots(w_scale, result.data, mode);
            // HACK: use dummy painter to get required height. Painter should be extended so that get_required_height
            // works as a static function.
            var dummy_painter = new (this.painter)(null, null, null, this.prefs, mode);
            return Math.max(MIN_TRACK_HEIGHT, dummy_painter.get_required_height(rows_required, canvas_width) );
        }
    },
    /**
     * Draw FeatureTrack tile.
     * @param result result from server
     * @param cxt canvas context to draw on
     * @param mode mode to draw in
     * @param resolution view resolution
     * @param tile_index index of tile to be drawn
     * @param w_scale pixels per base
     * @param ref_seq reference sequence data
     */
    draw_tile: function(result, ctx, mode, resolution, tile_index, w_scale, ref_seq) {
        var track = this,
            canvas = ctx.canvas,
            tile_bounds = this._get_tile_bounds(tile_index, resolution),
            tile_low = tile_bounds[0],
            tile_high = tile_bounds[1],
            min_height = 25,
            left_offset = this.left_offset;
        
        // Drawing the summary tree (feature coverage histogram)
        if (mode === "summary_tree" || mode === "Histogram") {
            // Get summary tree data if necessary and set max if there is one.
            if (result.dataset_type !== "summary_tree") {
                var st_data = this.get_summary_tree_data(result.data, tile_low, tile_high, 200);
                if (result.max) {
                    st_data.max = result.max;
                }
                result = st_data;
            }
            // Paint summary tree into canvas
            var painter = new painters.SummaryTreePainter(result, tile_low, tile_high, this.prefs);
            painter.draw(ctx, canvas.width, canvas.height, w_scale);
            return new SummaryTreeTile(track, tile_index, resolution, canvas, result.data, result.max);
        }

        // Handle row-by-row tracks

        // Preprocessing: filter features and determine whether all unfiltered features have been slotted.
        var 
            filtered = [],
            slots = this.slotters[w_scale].slots;
            all_slotted = true;
        if ( result.data ) {
            var filters = this.filters_manager.filters;
            for (var i = 0, len = result.data.length; i < len; i++) {
                var feature = result.data[i];
                var hide_feature = false;
                var filter;
                for (var f = 0, flen = filters.length; f < flen; f++) {
                    filter = filters[f];
                    filter.update_attrs(feature);
                    if (!filter.keep(feature)) {
                        hide_feature = true;
                        break;
                    }
                }
                if (!hide_feature) {
                    // Feature visible.
                    filtered.push(feature);
                    // Set flag if not slotted.
                    if ( !(feature[0] in slots) ) {
                        all_slotted = false;
                    }
                }
            }
        }        
        
        // Create painter.
        var filter_alpha_scaler = (this.filters_manager.alpha_filter ? new FilterScaler(this.filters_manager.alpha_filter) : null);
        var filter_height_scaler = (this.filters_manager.height_filter ? new FilterScaler(this.filters_manager.height_filter) : null);
        // HACK: ref_seq will only be defined for ReadTracks, and only the ReadPainter accepts that argument
        var painter = new (this.painter)(filtered, tile_low, tile_high, this.prefs, mode, filter_alpha_scaler, filter_height_scaler, ref_seq);
        var feature_mapper = null;

        // console.log(( tile_low - this.view.low ) * w_scale, tile_index, w_scale);
        ctx.fillStyle = this.prefs.block_color;
        ctx.font = ctx.canvas.manager.default_font;
        ctx.textAlign = "right";
        
        if (result.data) {
            // Draw features.
            feature_mapper = painter.draw(ctx, canvas.width, canvas.height, w_scale, slots);
            feature_mapper.translation = -left_offset;
        }
        
        return new FeatureTrackTile(track, tile_index, resolution, canvas, result.data, w_scale, mode, result.message, all_slotted, feature_mapper);        
    },
    /**
     * Returns true if data is compatible with a given mode.
     */
    data_and_mode_compatible: function(data, mode) {
        // Only handle modes that user can set.
        if (mode === "Auto") {
            return true;
        }
        // All other modes--Histogram, Dense, Squish, Pack--require data + details.
        else if (data.extra_info === "no_detail" || data.dataset_type === "summary_tree") {
            return false;
        }
        else {
            return true;
        }
    },
    /**
     * Returns true if data can be subsetted.
     */
    can_subset: function(data) {
        // Do not subset summary tree data, entries with a message, or data with no detail.
        if (data.dataset_type === "summary_tree" || data.message || data.extra_info === "no_detail")  {
            return false;
        }

        return true;
    },
});

var VcfTrack = function(view, container, obj_dict) {
    FeatureTrack.call(this, view, container, obj_dict);
    
    this.config = new DrawableConfig( {
        track: this,
        params: [
            { key: 'name', label: 'Name', type: 'text', default_value: this.name },
            { key: 'block_color', label: 'Block color', type: 'color', default_value: get_random_color() },
            { key: 'label_color', label: 'Label color', type: 'color', default_value: 'black' },
            { key: 'show_insertions', label: 'Show insertions', type: 'bool', default_value: false },
            { key: 'show_counts', label: 'Show summary counts', type: 'bool', default_value: true },
            { key: 'mode', type: 'string', default_value: this.mode, hidden: true },
        ], 
        saved_values: obj_dict.prefs,
        onchange: function() {
            this.track.set_name(this.track.prefs.name);
            this.track.tile_cache.clear();
            this.track.request_draw();
        }
    });
    this.prefs = this.config.values;
    
    this.painter = painters.ReadPainter;
};

extend(VcfTrack.prototype, Drawable.prototype, TiledTrack.prototype, FeatureTrack.prototype);

var ReadTrack = function (view, container, obj_dict) {
    FeatureTrack.call(this, view, container, obj_dict);
    
    var 
        block_color = get_random_color(),
        reverse_strand_color = get_random_color( [ block_color, "#ffffff" ] );
    this.config = new DrawableConfig( {
        track: this,
        params: [
            { key: 'name', label: 'Name', type: 'text', default_value: this.name },
            { key: 'block_color', label: 'Block and sense strand color', type: 'color', default_value: block_color },
            { key: 'reverse_strand_color', label: 'Antisense strand color', type: 'color', default_value: reverse_strand_color },
            { key: 'label_color', label: 'Label color', type: 'color', default_value: 'black' },
            { key: 'show_insertions', label: 'Show insertions', type: 'bool', default_value: false },
            { key: 'show_differences', label: 'Show differences only', type: 'bool', default_value: true },
            { key: 'show_counts', label: 'Show summary counts', type: 'bool', default_value: true },
            { key: 'histogram_max', label: 'Histogram maximum', type: 'float', default_value: null, help: 'Clear value to set automatically' },
            { key: 'mode', type: 'string', default_value: this.mode, hidden: true },
        ], 
        saved_values: obj_dict.prefs,
        onchange: function() {
            this.track.set_name(this.track.prefs.name);
            this.track.tile_cache.clear();
            this.track.request_draw();
        }
    });
    this.prefs = this.config.values;
    
    this.painter = painters.ReadPainter;
    this.update_icons();
};
extend(ReadTrack.prototype, Drawable.prototype, TiledTrack.prototype, FeatureTrack.prototype);

// Exports
exports.View = View;
exports.DrawableGroup = DrawableGroup;
exports.LineTrack = LineTrack;
exports.FeatureTrack = FeatureTrack;
exports.ReadTrack = ReadTrack;
exports.VcfTrack = VcfTrack;
exports.CompositeTrack = CompositeTrack;

// End trackster_module encapsulation
};

// ---- To be extracted ------------------------------------------------------

// ---- Feature Packing ----

// Encapsulation
var slotting_module = function(require, exports) {
    
var extend = require('class').extend;

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
exports.FeatureSlotter = function (w_scale, mode, max_rows, measureText) {
    this.slots = {};
    this.start_end_dct = {};
    this.w_scale = w_scale;
    this.mode = mode;
    this.include_label = (mode === "Pack");
    this.max_rows = max_rows;
    this.measureText = measureText;
};

/**
 * Slot a set of features, `this.slots` will be updated with slots by id, and
 * the largest slot required for the passed set of features is returned
 */
extend( exports.FeatureSlotter.prototype, {
    slot_features: function( features ) {
        var w_scale = this.w_scale, 
            start_end_dct = this.start_end_dct,
            undone = [], 
            slotted = [], 
            highest_slot = 0, 
            max_rows = this.max_rows;
        
        // If feature already exists in slots (from previously seen tiles), use the same slot,
        // otherwise if not seen, add to "undone" list for slot calculation.
    
        // TODO: Should calculate zoom tile index, which will improve performance
        // by only having to look at a smaller subset
        // if (this.start_end_dct[0] === undefined) { this.start_end_dct[0] = []; }
        for (var i = 0, len = features.length; i < len; i++) {
            var feature = features[i],
                feature_uid = feature[0];
            if (this.slots[feature_uid] !== undefined) {
                highest_slot = Math.max(highest_slot, this.slots[feature_uid]);
                slotted.push(this.slots[feature_uid]);
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
                this.slots[feature_uid] = slot_num;
                highest_slot = Math.max(highest_slot, slot_num);
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
    
var extend = require('class').extend;

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
 * Base class for all scalers. Scalers produce values that are used to change (scale) drawing attributes.
 */
var Scaler = function(default_val) {
    this.default_val = (default_val ? default_val : 1);
};

/**
 * Produce a scaling value.
 */
Scaler.prototype.gen_val = function(input) {
    return this.default_val;
};

/**
 * Base class for painters
 *
 * -- Mode and prefs are both optional
 */
var Painter = function(data, view_start, view_end, prefs, mode) {
    // Data and data properties
    this.data = data;
    // View
    this.view_start = view_start;
    this.view_end = view_end;
    // Drawing prefs
    this.prefs = extend( {}, this.default_prefs, prefs );
    this.mode = mode;
}

Painter.prototype.default_prefs = {};

/**
 * Draw on the context using a rectangle of width x height. w_scale is 
 * needed because it cannot be computed from width and view size alone
 * as a left_offset may be present.
 */
Painter.prototype.draw = function(ctx, width, height, w_scale) {};

/**
 * SummaryTreePainter, a histogram showing number of intervals in a region
 */
var SummaryTreePainter = function(data, view_start, view_end, prefs, mode) {
    Painter.call(this, data, view_start, view_end, prefs, mode);
}

SummaryTreePainter.prototype.default_prefs = { show_counts: false };

SummaryTreePainter.prototype.draw = function(ctx, width, height, w_scale) {
    var view_start = this.view_start,
        view_range = this.view_end - this.view_start,
        points = this.data.data,
        max = (this.prefs.histogram_max ? this.prefs.histogram_max : this.data.max),
        // Set base Y so that max label and data do not overlap. Base Y is where rectangle bases
        // start. However, height of each rectangle is relative to required_height; hence, the
        // max rectangle is required_height.
        base_y = height;
        delta_x_px = Math.ceil(this.data.delta * w_scale);
    ctx.save();
    
    for (var i = 0, len = points.length; i < len; i++) {
        var x = Math.floor( (points[i][0] - view_start) * w_scale );
        var y = points[i][1];
        
        if (!y) { continue; }
        var y_px = y / max * height;
        if (y !== 0 && y_px < 1) { y_px = 1; }

        ctx.fillStyle = this.prefs.block_color;
        ctx.fillRect( x, base_y - y_px, delta_x_px, y_px );
        
        // Draw number count if it can fit the number with some padding, otherwise things clump up
        var text_padding_req_x = 4;
        if (this.prefs.show_counts && (ctx.measureText(y).width + text_padding_req_x) < delta_x_px) {
            ctx.fillStyle = this.prefs.label_color;
            ctx.textAlign = "center";
            ctx.fillText(y, x + (delta_x_px/2), 10);
        }
    }
    
    ctx.restore();
}

var LinePainter = function(data, view_start, view_end, prefs, mode) {
    Painter.call( this, data, view_start, view_end, prefs, mode );
    if ( this.prefs.min_value === undefined ) {
        var min_value = Infinity;
        for (var i = 0, len = this.data.length; i < len; i++) {
            min_value = Math.min( min_value, this.data[i][1] );
        }
        this.prefs.min_value = min_value;
    }
    if ( this.prefs.max_value === undefined ) {
        var max_value = -Infinity;
        for (var i = 0, len = this.data.length; i < len; i++) {
            max_value = Math.max( max_value, this.data[i][1] );
        }
        this.prefs.max_value = max_value;
    }
};

LinePainter.prototype.default_prefs = { min_value: undefined, max_value: undefined, mode: "Histogram", color: "#000", overflow_color: "#F66" };

LinePainter.prototype.draw = function(ctx, width, height, w_scale) {
    var 
        in_path = false,
        min_value = this.prefs.min_value,
        max_value = this.prefs.max_value,
        vertical_range = max_value - min_value,
        height_px = height,
        view_start = this.view_start,
        view_range = this.view_end - this.view_start,
        mode = this.mode,
        data = this.data;

    ctx.save();

    // Pixel position of 0 on the y axis
    var y_zero = Math.round( height + min_value / vertical_range * height );

    // Horizontal line to denote x-axis
    if ( mode !== "Intensity" ) {
        ctx.fillStyle = "#aaa";
        ctx.fillRect( 0, y_zero, width, 1 );
    }
    
    ctx.beginPath();
    var x_scaled, y, delta_x_px;
    if (data.length > 1) {
        delta_x_px = Math.ceil((data[1][0] - data[0][0]) * w_scale);
    } else {
        delta_x_px = 10;
    }
    
    // Extract RGB from preference color.
    var
        pref_color = parseInt( this.prefs.color.slice(1), 16 ),
        pref_r = (pref_color & 0xff0000) >> 16,
        pref_g = (pref_color & 0x00ff00) >> 8,
        pref_b = pref_color & 0x0000ff;
    
    // Paint track.
    for (var i = 0, len = data.length; i < len; i++) {
        ctx.fillStyle = ctx.strokeStyle = this.prefs.color;
        x_scaled = Math.round((data[i][0] - view_start) * w_scale);
        y = data[i][1];
        var top_overflow = false, bot_overflow = false;
        if (y === null) {
            if (in_path && mode === "Filled") {
                ctx.lineTo(x_scaled, height_px);
            }
            in_path = false;
            continue;
        }
        if (y < min_value) {
            bot_overflow = true;
            y = min_value;
        } else if (y > max_value) {
            top_overflow = true;
            y = max_value;
        }
    
        if (mode === "Histogram") {
            // y becomes the bar height in pixels, which is the negated for canvas coords
            y = Math.round( y / vertical_range * height_px );
            ctx.fillRect(x_scaled, y_zero, delta_x_px, - y );
        } else if (mode === "Intensity") {
            var 
                saturation = (y - min_value) / vertical_range,
                // Range is [pref_color, 255] where saturation = 0 --> 255 and saturation = 1 --> pref color
                new_r = Math.round( pref_r + (255 - pref_r) * (1 - saturation) ),
                new_g = Math.round( pref_g + (255 - pref_g) * (1 - saturation) ),
                new_b = Math.round( pref_b + (255 - pref_b) * (1 - saturation) );
            ctx.fillStyle = "rgb(" + new_r + "," + new_g + "," + new_b + ")";
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
        // Draw lines at boundaries if overflowing min or max
        ctx.fillStyle = this.prefs.overflow_color;
        if (top_overflow || bot_overflow) {
            var overflow_x;
            if (mode === "Histogram" || mode === "Intensity") {
                overflow_x = delta_x_px;
            } else { // Line and Filled, which are points
                x_scaled -= 2; // Move it over to the left so it's centered on the point
                overflow_x = 4;
            }
            if (top_overflow) {
                ctx.fillRect(x_scaled, 0, overflow_x, 3);
            }
            if (bot_overflow) {
                ctx.fillRect(x_scaled, height_px - 3, overflow_x, 3);
            }
        }
        ctx.fillStyle = this.prefs.color;
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
    
    ctx.restore();
};

/**
 * Mapper that contains information about feature locations and data.
 */
var FeaturePositionMapper = function(slot_height) {
    this.feature_positions = {};
    this.slot_height = slot_height;
    this.translation = 0;
    this.y_translation = 0;
};

/**
 * Map feature data to a position defined by <slot, x_start, x_end>.
 */
FeaturePositionMapper.prototype.map_feature_data = function(feature_data, slot, x_start, x_end) {
    if (!this.feature_positions[slot]) {
        this.feature_positions[slot] = [];
    }
    this.feature_positions[slot].push({
        data: feature_data,
        x_start: x_start,
        x_end: x_end
    });
};

/**
 * Get feature data for position <x, y>
 */
FeaturePositionMapper.prototype.get_feature_data = function(x, y) {
    // Find slot using Y.
    var slot = Math.floor( (y-this.y_translation)/this.slot_height ),
        feature_dict;

    // May not be over a slot due to padding, margin, etc.
    if (!this.feature_positions[slot]) {
        return null;
    }
    
    // Find feature using X.
    x += this.translation;
    for (var i = 0; i < this.feature_positions[slot].length; i++) {
        feature_dict = this.feature_positions[slot][i];
        if (x >= feature_dict.x_start && x <= feature_dict.x_end) {
            return feature_dict.data;
        }
    }
};

/**
 * Abstract object for painting feature tracks. Subclasses must implement draw_element() for painting to work.
 * Painter uses a 0-based, half-open coordinate system; start coordinate is closed--included--and the end is open.
 * This coordinate system matches the BED format.
 */
var FeaturePainter = function(data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler) {
    Painter.call(this, data, view_start, view_end, prefs, mode);
    this.alpha_scaler = (alpha_scaler ? alpha_scaler : new Scaler());
    this.height_scaler = (height_scaler ? height_scaler : new Scaler());
};

FeaturePainter.prototype.default_prefs = { block_color: "#FFF", connector_color: "#FFF" };

extend(FeaturePainter.prototype, {
    get_required_height: function(rows_required, width) {
        // y_scale is the height per row
        var required_height = y_scale = this.get_row_height(), mode = this.mode;
        // If using a packing mode, need to multiply by the number of slots used
        if (mode === "no_detail" || mode === "Squish" || mode === "Pack") {
            required_height = rows_required * y_scale;
        }
        return required_height + this.get_top_padding(width) + this.get_bottom_padding(width);
    },
    /** Extra padding before first row of features */
    get_top_padding: function(width) {
        return 0;
    },
    /** Extra padding after last row of features */
    get_bottom_padding: function(width) {
        // Pad bottom by half a row, at least 5 px
        return Math.max( Math.round( this.get_row_height() / 2 ), 5 ) 
    },
    /**
     * Draw data on ctx using slots and within the rectangle defined by width and height. Returns
     * a FeaturePositionMapper object with information about where features were drawn.
     */
    draw: function(ctx, width, height, w_scale, slots) {
        var data = this.data, view_start = this.view_start, view_end = this.view_end;

        ctx.save();

        ctx.fillStyle = this.prefs.block_color;
        ctx.textAlign = "right";

        var view_range = this.view_end - this.view_start,
            y_scale = this.get_row_height(),
            feature_mapper = new FeaturePositionMapper(y_scale),
            x_draw_coords;

        for (var i = 0, len = data.length; i < len; i++) {
            var feature = data[i],
                feature_uid = feature[0],
                feature_start = feature[1],
                feature_end = feature[2],
                // Slot valid only if features are slotted and this feature is slotted; 
                // feature may not be due to lack of space.
                slot = (slots && slots[feature_uid] !== undefined ? slots[feature_uid] : null);
                
            // Draw feature if there's overlap and mode is dense or feature is slotted (as it must be for all non-dense modes).
            if ( ( feature_start < view_end && feature_end > view_start ) && (this.mode === "Dense" || slot !== null) ) {
                x_draw_coords = this.draw_element(ctx, this.mode, feature, slot, view_start, view_end, w_scale, y_scale, width);
                feature_mapper.map_feature_data(feature, slot, x_draw_coords[0], x_draw_coords[1]);
            }
        }

        ctx.restore();
        feature_mapper.y_translation = this.get_top_padding(width);
        return feature_mapper;
    },
    /** 
     * Abstract function for drawing an individual feature.
     */
    draw_element: function(ctx, mode, feature, slot, tile_low, tile_high, w_scale, y_scale, width ) {
        console.log("WARNING: Unimplemented function.");
        return [0, 0];
    }
});

// Constants specific to feature tracks moved here (HACKING, these should
// basically all be configuration options)
var DENSE_TRACK_HEIGHT = 10,
    NO_DETAIL_TRACK_HEIGHT = 3,
    SQUISH_TRACK_HEIGHT = 5,
    PACK_TRACK_HEIGHT = 10,
    NO_DETAIL_FEATURE_HEIGHT = 1,
    DENSE_FEATURE_HEIGHT = 9,
    SQUISH_FEATURE_HEIGHT = 3,
    PACK_FEATURE_HEIGHT = 9,
    LABEL_SPACING = 2,
    CONNECTOR_COLOR = "#ccc";

var LinkedFeaturePainter = function(data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler) {
    FeaturePainter.call(this, data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler);
    // Whether to draw a single connector in the background that spans the entire feature (the intron fishbone)
    this.draw_background_connector = true;
    // Whether to call draw_connector for every pair of blocks
    this.draw_individual_connectors = false;
};

extend(LinkedFeaturePainter.prototype, FeaturePainter.prototype, {

    /**
     * Height of a single row, depends on mode
     */
    get_row_height: function() {
        var mode = this.mode, height;
           if (mode === "Dense") {
            height = DENSE_TRACK_HEIGHT;            
        }
        else if (mode === "no_detail") {
            height = NO_DETAIL_TRACK_HEIGHT;
        }
        else if (mode === "Squish") {
            height = SQUISH_TRACK_HEIGHT;
        }
        else { // mode === "Pack"
            height = PACK_TRACK_HEIGHT;
        }
        return height;
    },

    /**
     * Draw a feature. Returns an array with feature's start and end X coordinates.
     */
    draw_element: function(ctx, mode, feature, slot, tile_low, tile_high, w_scale, y_scale, width) {
        var 
            feature_uid = feature[0],
            feature_start = feature[1],
            // -1 because end is not included in feature; see FeaturePainter documentation for details.
            feature_end = feature[2] - 1,
            feature_name = feature[3],
            feature_strand = feature[4],
            f_start = Math.floor( Math.max(0, (feature_start - tile_low) * w_scale) ),
            f_end   = Math.ceil( Math.min(width, Math.max(0, (feature_end - tile_low) * w_scale)) ),
            draw_start = f_start,
            draw_end = f_end,
            y_center = (mode === "Dense" ? 0 : (0 + slot)) * y_scale + this.get_top_padding(width),
            thickness, y_start, thick_start = null, thick_end = null,
            // TODO: is there any reason why block, label color cannot be set at the Painter level?
            // For now, assume '.' === '+'
            block_color = block_color = (!feature_strand || feature_strand === "+" || feature_strand === "." ? this.prefs.block_color : this.prefs.reverse_strand_color);
            label_color = this.prefs.label_color;
        
        // Set global alpha.
        ctx.globalAlpha = this.alpha_scaler.gen_val(feature);
        
        // In dense mode, put all data in top slot.
        if (mode === "Dense") {
            slot = 1;
        }
        
        if (mode === "no_detail") {
            // No details for feature, so only one way to display.
            ctx.fillStyle = block_color;
            ctx.fillRect(f_start, y_center + 5, f_end - f_start, NO_DETAIL_FEATURE_HEIGHT);
        } 
        else { // Mode is either Squish or Pack:
            // Feature details.
            var feature_ts = feature[5],
                feature_te = feature[6],
                feature_blocks = feature[7],
                // Whether we are drawing full height or squished features
                full_height = true;
            
            if (feature_ts && feature_te) {
                thick_start = Math.floor( Math.max(0, (feature_ts - tile_low) * w_scale) );
                thick_end = Math.ceil( Math.min(width, Math.max(0, (feature_te - tile_low) * w_scale)) );
            }
            
            // Set vars that depend on mode.
            var thin_height, thick_height;
            if (mode === "Squish" ) {
                thin_height = 1;
                thick_height = SQUISH_FEATURE_HEIGHT;
                full_height = false;
            } else if ( mode === "Dense" ) {
                thin_height = 5;
                thick_height = DENSE_FEATURE_HEIGHT;
            } else { // mode === "Pack"
                thin_height = 5;
                thick_height = PACK_FEATURE_HEIGHT;
            }
            
            // Draw feature/feature blocks + connectors.
            if (!feature_blocks) {
                // If there are no blocks, treat the feature as one big exon.
                ctx.fillStyle = block_color;
                ctx.fillRect(f_start, y_center + 1, f_end - f_start, thick_height);
                // If strand is specified, draw arrows over feature
                if ( feature_strand && full_height ) {
                    if (feature_strand === "+") {
                        ctx.fillStyle = ctx.canvas.manager.get_pattern( 'right_strand_inv' );
                    } else if (feature_strand === "-") {
                        ctx.fillStyle = ctx.canvas.manager.get_pattern( 'left_strand_inv' );
                    }
                    ctx.fillRect(f_start, y_center + 1, f_end - f_start, thick_height);
                }
            } else { 
                //
                // There are feature blocks and mode is either Squish or Pack.
                //
                // Approach: (a) draw whole feature as connector/intron and (b) draw blocks as 
                // needed. This ensures that whole feature, regardless of whether it starts with
                // a block, is visible.
                //
               
                // Compute y axis center position and height
                var cur_y_center, cur_height;
                if (mode === "Squish" || mode === "Dense") {
                    cur_y_center = y_center + Math.floor(SQUISH_FEATURE_HEIGHT/2) + 1;
                    cur_height = 1;
                }
                else { // mode === "Pack"
                    if (feature_strand) {
                        cur_y_center = y_center;
                        cur_height = thick_height;
                    }
                    else {
                        cur_y_center += (SQUISH_FEATURE_HEIGHT/2) + 1;
                        cur_height = 1;
                    }
                }

                // Draw whole feature as connector/intron.
                if ( this.draw_background_connector ) {
                    if (mode === "Squish" || mode === "Dense") {
                        ctx.fillStyle = CONNECTOR_COLOR;
                    }
                    else { // mode === "Pack"
                        if (feature_strand) {
                            if (feature_strand === "+") {
                                ctx.fillStyle = ctx.canvas.manager.get_pattern( 'right_strand' );
                            } else if (feature_strand === "-") {
                                ctx.fillStyle = ctx.canvas.manager.get_pattern( 'left_strand' );
                            }
                        }
                        else {
                            ctx.fillStyle = CONNECTOR_COLOR;
                        }
                    }
                    ctx.fillRect(f_start, cur_y_center, f_end - f_start, cur_height);
                }
                
                // Draw blocks.
                var start_and_height;
                for (var k = 0, k_len = feature_blocks.length; k < k_len; k++) {
                    var block = feature_blocks[k],
                        block_start = Math.floor( Math.max(0, (block[0] - tile_low) * w_scale) ),
                        // -1 because end is not included in feature; see FeaturePainter documentation for details.
                        block_end = Math.ceil( Math.min(width, Math.max((block[1] - 1 - tile_low) * w_scale)) ),
                        last_block_start, last_block_end;

                    // Skip drawing if block not on tile.    
                    if (block_start > block_end) { continue; }

                    // Draw thin block.
                    ctx.fillStyle = block_color;
                    ctx.fillRect(block_start, y_center + (thick_height-thin_height)/2 + 1, block_end - block_start, thin_height);

                    // If block intersects with thick region, draw block as thick.
                    // - No thick is sometimes encoded as thick_start == thick_end, so don't draw in that case
                    if (thick_start !== undefined && feature_te > feature_ts && !(block_start > thick_end || block_end < thick_start) ) {
                        var block_thick_start = Math.max(block_start, thick_start),
                            block_thick_end = Math.min(block_end, thick_end);
                        ctx.fillRect(block_thick_start, y_center + 1, block_thick_end - block_thick_start, thick_height);
                        // FIXME: for GFF datasets, only one block of many may be fetched, so it is not possible to 
                        // determine if feature has only one block. Hence, Ffr now, do not use b/c color is used to encoding 
                        // strand.
                        /*
                        if ( feature_blocks.length === 1 && mode === "Pack") {
                            // Exactly one block means we have no introns, but do have a distinct "thick" region,
                            // draw arrows over it if in pack mode.
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
                            ctx.fillRect(block_thick_start, y_center + 1, block_thick_end - block_thick_start, thick_height);
                        }
                        */
                    }
                    // Draw individual connectors if required
                    if ( this.draw_individual_connectors && last_block_start ) {
                        this.draw_connector( ctx, last_block_start, last_block_end, block_start, block_end, y_center );
                    }
                    last_block_start = block_start;
                    last_block_end = block_end;
                }
                                
                // FIXME: Height scaling only works in Pack mode right now.
                if (mode === "Pack") {
                    // Reset alpha so height scaling is not impacted by alpha scaling.
                    ctx.globalAlpha = 1;
                    
                    // Height scaling: draw white lines to reduce height according to height scale factor.
                    ctx.fillStyle = "white"; // TODO: set this to background color.
                    var 
                        hscale_factor = this.height_scaler.gen_val(feature),
                        // Ceil ensures that min height is >= 1.
                        new_height = Math.ceil(thick_height * hscale_factor),
                        ws_height = Math.round( (thick_height-new_height)/2 );
                    if (hscale_factor !== 1) {
                        ctx.fillRect(f_start, cur_y_center + 1, f_end - f_start, ws_height);
                        ctx.fillRect(f_start, cur_y_center + thick_height - ws_height + 1, f_end - f_start, ws_height);
                    }   
                }                
            }
            
            // Reset alpha so that label is not transparent.
            ctx.globalAlpha = 1;
                        
            // Draw label for Pack mode.
            if (mode === "Pack" && feature_start > tile_low) {
                ctx.fillStyle = label_color;
                // FIXME: assumption here that the entire view starts at 0
                if (tile_low === 0 && f_start - ctx.measureText(feature_name).width < 0) {
                    ctx.textAlign = "left";
                    ctx.fillText(feature_name, f_end + LABEL_SPACING, y_center + 8);
                    draw_end += ctx.measureText(feature_name).width + LABEL_SPACING;
                } else {
                    ctx.textAlign = "right";
                    ctx.fillText(feature_name, f_start - LABEL_SPACING, y_center + 8);
                    draw_start -= ctx.measureText(feature_name).width + LABEL_SPACING;
                }
                //ctx.fillStyle = block_color;
            }
        }
        
        // Reset global alpha.
        ctx.globalAlpha = 1;
        
        return [draw_start, draw_end];
    }
});

var ReadPainter = function(data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler, ref_seq) {
    FeaturePainter.call(this, data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler);
    this.ref_seq = (ref_seq ? ref_seq.data : null);
};

extend(ReadPainter.prototype, FeaturePainter.prototype, {
    /**
     * Returns height based on mode.
     */
    get_row_height: function() {
        var height, mode = this.mode;
        if (mode === "Dense") {
            height = DENSE_TRACK_HEIGHT;            
        }
        else if (mode === "Squish") {
            height = SQUISH_TRACK_HEIGHT;
        }
        else { // mode === "Pack"
            height = PACK_TRACK_HEIGHT;
            if (this.prefs.show_insertions) {
                height *= 2;
            }
        }
        return height;
    },
    
    /**
     * Draw a single read.
     */
    draw_read: function(ctx, mode, w_scale, y_center, tile_low, tile_high, feature_start, cigar, strand, orig_seq) {
        ctx.textAlign = "center";
        var track = this,
            tile_region = [tile_low, tile_high],
            base_offset = 0,
            seq_offset = 0,
            gap = 0,
            char_width_px = ctx.canvas.manager.char_width_px,
            block_color = (strand === "+" ? this.prefs.block_color : this.prefs.reverse_strand_color);
            
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
            
            // Make sure that read is drawn even if it too small to be rendered officially; in this case,
            // read is drawn at 1px.
            // TODO: need to ensure that s_start, s_end are calcuated the same for both slotting
            // and drawing.
            if (s_start === s_end) {
                s_end += 1;
            }
                
            switch (cig_op) {
                case "H": // Hard clipping.
                    // TODO: draw anything?
                    // Sequence not present, so do not increment seq_offset.
                    break;
                case "S": // Soft clipping.
                case "M": // Match.
                case "=": // Equals.
                    if (is_overlap([seq_start, seq_start + cig_len], tile_region)) {
                        // Draw.
                        var seq = orig_seq.slice(seq_offset, seq_offset + cig_len);
                        if (gap > 0) {
                            ctx.fillStyle = block_color;
                            ctx.fillRect(s_start - gap, y_center + 1, s_end - s_start, 9);
                            ctx.fillStyle = CONNECTOR_COLOR;
                            // TODO: this can be made much more efficient by computing the complete sequence
                            // to draw and then drawing it.
                            for (var c = 0, str_len = seq.length; c < str_len; c++) {
                                if (this.prefs.show_differences) {
                                    if (this.ref_seq) {
                                        var ref_char = this.ref_seq[seq_start - tile_low + c];
                                        if (!ref_char || ref_char.toLowerCase() === seq[c].toLowerCase()) {
                                            continue;
                                        }
                                    }
                                    else {
                                        // No reference so cannot show differences.
                                        continue;
                                    }
                                }
                                if (seq_start + c >= tile_low && seq_start + c <= tile_high) {
                                    var c_start = Math.floor( Math.max(0, (seq_start + c - tile_low) * w_scale) );
                                    ctx.fillText(seq[c], c_start, y_center + 9);
                                }
                            }
                        } else {
                            ctx.fillStyle = block_color;
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
                    var insert_x_coord = s_start - gap;
                    
                    if (is_overlap([seq_start, seq_start + cig_len], tile_region)) {
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
                                switch( compute_overlap( [seq_start, seq_start + cig_len], tile_region ) ) {
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
                                draw_last.push( { type: "text", data: [seq.length, insert_x_coord, y_center + 9] } );
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
            else if (type === "triangle") {
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
            label_color = this.prefs.label_color,
            // Left-gap for label text since we align chrom text to the position tick.
            gap = 0;

        // TODO: fix gap usage; also see note on gap in draw_read.
        if ((mode === "Pack" || this.mode === "Auto") && w_scale > ctx.canvas.manager.char_width_px) {
            var gap = Math.round(w_scale/2);
        }
        
        // Draw read.
        if (feature[5] instanceof Array) {
            // Read is paired.
            var b1_start = Math.floor( Math.max(0, (feature[4][0] - tile_low) * w_scale) ),
                b1_end   = Math.ceil( Math.min(width, Math.max(0, (feature[4][1] - tile_low) * w_scale)) ),
                b2_start = Math.floor( Math.max(0, (feature[5][0] - tile_low) * w_scale) ),
                b2_end   = Math.ceil( Math.min(width, Math.max(0, (feature[5][1] - tile_low) * w_scale)) );

            // Draw left/forward read.
            if (feature[4][1] >= tile_low && feature[4][0] <= tile_high && feature[4][2]) {                
                this.draw_read(ctx, mode, w_scale, y_center, tile_low, tile_high, feature[4][0], feature[4][2], feature[4][3], feature[4][4]);
            }
            // Draw right/reverse read.
            if (feature[5][1] >= tile_low && feature[5][0] <= tile_high && feature[5][2]) {
                this.draw_read(ctx, mode, w_scale, y_center, tile_low, tile_high, feature[5][0], feature[5][2], feature[5][3], feature[5][4]);
            }
            // Draw connector.
            if (b2_start > b1_end) {
                ctx.fillStyle = CONNECTOR_COLOR;
                dashedLine(ctx, b1_end - gap, y_center + 5, b2_start - gap, y_center + 5);
            }
        } else {
            // Read is single.
            this.draw_read(ctx, mode, w_scale, y_center, tile_low, tile_high, feature_start, feature[4], feature[5], feature[6]);
        }
        if (mode === "Pack" && feature_start > tile_low && feature_name !== ".") {
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
        }
        
        // FIXME: provide actual coordinates for drawn read.
        return [0,0];
    }
});

var ArcLinkedFeaturePainter = function(data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler) {
    LinkedFeaturePainter.call(this, data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler);
    // Need to know the longest feature length for adding spacing
    this.longest_feature_length = this.calculate_longest_feature_length();
    this.draw_background_connector = false;
    this.draw_individual_connectors = true;
};

extend(ArcLinkedFeaturePainter.prototype, FeaturePainter.prototype, LinkedFeaturePainter.prototype, {

    calculate_longest_feature_length: function () {
        var longest_feature_length = 0;
        for (var i = 0, len = this.data.length; i < len; i++) {
            var feature = this.data[i], feature_start = feature[1], feature_end = feature[2];
            longest_feature_length = Math.max( longest_feature_length, feature_end - feature_start );
        }
        return longest_feature_length;
    },

    get_top_padding: function( width ) { 
        var view_range = this.view_end - this.view_start,
            w_scale = width / view_range;
        return Math.min( 128, Math.ceil( ( this.longest_feature_length / 2 ) * w_scale ) );
    },

    draw_connector: function( ctx, block1_start, block1_end, block2_start, block2_end, y_center ) {
        // Arc drawing -- from closest endpoints
        var x_center = ( block1_end + block2_start ) / 2,
            radius = block2_start - x_center; 
        // For full half circles
        var angle1 = Math.PI, angle2 = 0;
        if ( radius > 0 ) {
            ctx.beginPath();
            ctx.arc( x_center, y_center, block2_start - x_center, Math.PI, 0 );
            ctx.stroke();
        }
    }
});

exports.Scaler = Scaler;
exports.SummaryTreePainter = SummaryTreePainter;
exports.LinePainter = LinePainter;
exports.LinkedFeaturePainter = LinkedFeaturePainter;
exports.ReadPainter = ReadPainter;
exports.ArcLinkedFeaturePainter = ArcLinkedFeaturePainter;

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
    run_module( 'class', class_module );
    run_module( 'slotting', slotting_module );
    run_module( 'painters', painters_module );
    run_module( 'trackster', trackster_module );
    // Export trackster stuff
    for ( key in modules.trackster ) {
        target[key] = modules.trackster[key];
    }
})(window);
