(function(){

/**
 * Model, view, and controller objects for Galaxy visualization framework.
 * 
 * Required libraries: Backbone, jQuery
 *
 * Models have no references to views, instead using events to indicate state 
 * changes; this is advantageous because multiple views can use the same object 
 * and models can be used without views.
 */

// --------- Models ---------

/**
 * Implementation of a server-state based deferred. Server is repeatedly polled, and when
 * condition is met, deferred is resolved.
 */
var ServerStateDeferred = Backbone.Model.extend({
    defaults: {
        ajax_settings: {},
        interval: 1000,
        success_fn: function(result) { return true; }
    },
    
    /**
     * Returns a deferred that resolves when success function returns true.
     */
    go: function() {
        var deferred = $.Deferred(),
            self = this,
            ajax_settings = self.get('ajax_settings'),
            success_fn = self.get('success_fn'),
            interval = self.get('interval'),
             _go = function() {
                 $.ajax(ajax_settings).success(function(result) {
                     if (success_fn(result)) {
                         // Result is good, so resolve.
                         deferred.resolve(result);
                     }
                     else {
                         // Result not good, try again.
                         setTimeout(_go, interval);
                     }
                 });
             };
         _go();
         return deferred;
    }
});

// TODO: move to Backbone

/**
 * Canvas manager is used to create canvases, for browsers, this deals with
 * backward comparibility using excanvas, as well as providing a pattern cache
 */
var CanvasManager = function(default_font) {
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
};

_.extend( CanvasManager.prototype, {
    load_pattern: function( key, path ) {
        var patterns = this.patterns,
            dummy_context = this.dummy_context,
            image = new Image();
        image.src = galaxy_paths.attributes.image_path + path;
        image.onload = function() {
            patterns[key] = dummy_context.createPattern( image, "repeat" );
        };
    },
    get_pattern: function( key ) {
        return this.patterns[key];
    },
    new_canvas: function() {
        var canvas = $("<canvas/>")[0];
        // If using excanvas in IE, we need to explicately attach the canvas
        // methods to the DOM element
        if (window.G_vmlCanvasManager) { G_vmlCanvasManager.initElement(canvas); }
        // Keep a reference back to the manager
        canvas.manager = this;
        return canvas;
    }
});

/**
 * Generic cache that handles key/value pairs.
 */ 
var Cache = Backbone.Model.extend({
    defaults: {
        num_elements: 20,
        obj_cache: null,
        key_ary: null
    },

    initialize: function(options) {
        this.clear();
    },
    
    get_elt: function(key) {
        var obj_cache = this.attributes.obj_cache,
            key_ary = this.attributes.key_ary,
            index = key_ary.indexOf(key);
        if (index !== -1) {
            if (obj_cache[key].stale) {
                // Object is stale, so remove key and object.
                key_ary.splice(index, 1);
                delete obj_cache[key];
            }
            else {
                this.move_key_to_end(key, index);
            }
        }
        return obj_cache[key];
    },
    
    set_elt: function(key, value) {
        var obj_cache = this.attributes.obj_cache,
            key_ary = this.attributes.key_ary,
            num_elements = this.attributes.num_elements;
        if (!obj_cache[key]) {
            if (key_ary.length >= num_elements) {
                // Remove first element
                var deleted_key = key_ary.shift();
                delete obj_cache[deleted_key];
            }
            key_ary.push(key);
        }
        obj_cache[key] = value;
        return value;
    },
    
    // Move key to end of cache. Keys are removed from the front, so moving a key to the end 
    // delays the key's removal.
    move_key_to_end: function(key, index) {
        this.attributes.key_ary.splice(index, 1);
        this.attributes.key_ary.push(key);
    },
    
    clear: function() {
        this.attributes.obj_cache = {};
        this.attributes.key_ary = [];
    },
    
    // Returns the number of elements in the cache.
    size: function() {
        return this.attributes.key_ary.length;
    }
});

/**
 * Data manager for genomic data. Data is connected to and queryable by genomic regions.
 */
var GenomeDataManager = Cache.extend({
    defaults: _.extend({}, Cache.prototype.defaults, {
        dataset: null,
        filters_manager: null,
        data_url: null,
        dataset_state_url: null,
        feature_search_url: null,
        genome_wide_summary_data: null,
        data_mode_compatible: function(entry, mode) { return true; },
        can_subset: function(entry) { return false; }
    }),

    /**
     * Returns deferred that resolves to true when dataset is ready (or false if dataset
     * cannot be used).
     */
    data_is_ready: function() {
        var dataset = this.get('dataset'),
            ready_deferred = $.Deferred(),
            ss_deferred = new ServerStateDeferred({
                ajax_settings: {
                    url: this.get('dataset_state_url'),
                    data: {
                        dataset_id: dataset.id,
                        hda_ldda: dataset.get('hda_ldda')
                    },
                    dataType: "json"
                },
                interval: 5000,
                success_fn: function(response) { return response !== "pending"; }
            });

        $.when(ss_deferred.go()).then(function(response) {
            ready_deferred.resolve(response === "ok" || response === "data" );
        });
        return ready_deferred;
    },

    /**
     * Perform a feature search from server; returns Deferred object that resolves when data is available.
     */
    search_features: function(query) {
        var dataset = this.get('dataset'),
            params = {
                query: query,
                dataset_id: dataset.id,
                hda_ldda: dataset.get('hda_ldda')
            };
        return $.getJSON(this.get('feature_search_url'), params);
    },
    
    /**
     * Load data from server; returns Deferred object that resolves when data is available.
     */
    load_data: function(region, mode, resolution, extra_params) {
        // Setup data request params.
        var params = {
                        "chrom": region.get('chrom'), 
                        "low": region.get('start'), 
                        "high": region.get('end'), 
                        "mode": mode, 
                        "resolution": resolution
                     },
            dataset = this.get('dataset');
                        
        // ReferenceDataManager does not have dataset.
        if (dataset) {
            params.dataset_id = dataset.id;
            params.hda_ldda = dataset.get('hda_ldda');
        }
        
        $.extend(params, extra_params);
        
        // Add track filters to params.
        var filters_manager = this.get('filters_manager');
        if (filters_manager) {
            var filter_names = [];
            var filters = filters_manager.filters;
            for (var i = 0; i < filters.length; i++) {
                filter_names.push(filters[i].name);
            }
            params.filter_cols = JSON.stringify(filter_names);
        }
                        
        // Do request.
        var manager = this;
        return $.getJSON(this.get('data_url'), params, function (result) {
            manager.set_data(region, result);
        });
    },
    
    /**
     * Get data from dataset.
     */
    get_data: function(region, mode, resolution, extra_params) {
        // Debugging:
        //console.log("get_data", low, high, mode);
        /*
        console.log("cache contents:")
        for (var i = 0; i < this.key_ary.length; i++) {
            console.log("\t", this.key_ary[i], this.obj_cache[this.key_ary[i]]);
        }
        */
                
        // Look for entry and return if it's a deferred or if data available is compatible with mode.
        var entry = this.get_elt(region);
        if ( entry && 
             ( is_deferred(entry) || this.get('data_mode_compatible')(entry, mode) ) ) {
            return entry;
        }

        //
        // Look in cache for data that can be used. Data can be reused if it
        // has the requested data and is not summary tree and has details.
        // TODO: this logic could be improved if the visualization knew whether
        // the data was "index" or "data."
        //
        var key_ary = this.get('key_ary'),
            obj_cache = this.get('obj_cache'),
            key, entry_region;
        for (var i = 0; i < key_ary.length; i++) {
            key = key_ary[i];
            entry_region = new GenomeRegion({from_str: key});
        
            if (entry_region.contains(region)) {
                // This entry has data in the requested range. Return if data
                // is compatible and can be subsetted.
                entry = obj_cache[key];
                if ( is_deferred(entry) || 
                    ( this.get('data_mode_compatible')(entry, mode) && this.get('can_subset')(entry) ) ) {
                    this.move_key_to_end(key, i);
                    return entry;
                }
            }
        }
                
        // Load data from server. The deferred is immediately saved until the
        // data is ready, it then replaces itself with the actual data.
        entry = this.load_data(region, mode, resolution, extra_params);
        this.set_data(region, entry);
        return entry;
    },
    
    /**
     * Alias for set_elt for readbility.
     */
    set_data: function(region, entry) {
        this.set_elt(region, entry);  
    },
    
    /** "Deep" data request; used as a parameter for DataManager.get_more_data() */
    DEEP_DATA_REQ: "deep",
    
    /** "Broad" data request; used as a parameter for DataManager.get_more_data() */
    BROAD_DATA_REQ: "breadth",
    
    /**
     * Gets more data for a region using either a depth-first or a breadth-first approach.
     */
    get_more_data: function(region, mode, resolution, extra_params, req_type) {
        //
        // Get current data from cache and mark as stale.
        //
        var cur_data = this.get_elt(region);
        if ( !(cur_data && this.get('data_mode_compatible')(cur_data, mode)) ) {
            console.log("ERROR: no current data for: ", dataset, region.toString(), mode, resolution, extra_params);
            return;
        }
        cur_data.stale = true;
        
        //
        // Set parameters based on request type.
        //
        var query_low = region.get('start');
        if (req_type === this.DEEP_DATA_REQ) {
            // Use same interval but set start_val to skip data that's already in cur_data.
            $.extend(extra_params, {start_val: cur_data.data.length + 1});
        }
        else if (req_type === this.BROAD_DATA_REQ) {
            // To get past an area of extreme feature depth, set query low to be after either
            // (a) the maximum high or HACK/FIXME (b) the end of the last feature returned.
            query_low = (cur_data.max_high ? cur_data.max_high : cur_data.data[cur_data.data.length - 1][2]) + 1;
        }
        var query_region = region.copy().set('start', query_low);
        
        //
        // Get additional data, append to current data, and set new data. Use a custom deferred object
        // to signal when new data is available.
        //
        var 
            data_manager = this,
            new_data_request = this.load_data(query_region, mode, resolution, extra_params),
            new_data_available = $.Deferred();
        // load_data sets cache to new_data_request, but use custom deferred object so that signal and data
        // is all data, not just new data.
        this.set_data(region, new_data_available);
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
            data_manager.set_data(region, result);
            new_data_available.resolve(result);
        });
        return new_data_available;
    },
        
    /**
     * Get data from the cache.
     */
    get_elt: function(region) {
        return Cache.prototype.get_elt.call(this, region.toString());
    },
    
    /**
     * Sets data in the cache.
     */
    set_elt: function(region, result) {
        return Cache.prototype.set_elt.call(this, region.toString(), result);
    }
});

var ReferenceTrackDataManager = GenomeDataManager.extend({
    load_data: function(low, high, mode, resolution, extra_params) {
        if (resolution > 1) {
            // Now that data is pre-fetched before draw, we don't load reference tracks
            // unless it's at the bottom level.
            return { data: null };
        }
        return GenomeDataManager.prototype.load_data.call(this, low, high, mode, resolution, extra_params);
    } 
});
 
/**
 * A genome build.
 */
var Genome = Backbone.Model.extend({
    defaults: {
        name: null,
        key: null,
        chroms_info: null
    },
    
    get_chroms_info: function() {
        return this.attributes.chroms_info.chrom_info;  
    }
});

/**
 * A genomic region.
 */
var GenomeRegion = Backbone.RelationalModel.extend({
    defaults: {
        chrom: null,
        start: 0,
        end: 0,
        DIF_CHROMS: 1000,
        BEFORE: 1001, 
        CONTAINS: 1002, 
        OVERLAP_START: 1003, 
        OVERLAP_END: 1004, 
        CONTAINED_BY: 1005, 
        AFTER: 1006
    },
    
    /**
     * If from_str specified, use it to initialize attributes.
     */
    initialize: function(options) {
        if (options.from_str) {
            var pieces = options.from_str.split(':'),
                chrom = pieces[0],
                start_end = pieces[1].split('-');
            this.set({
                chrom: chrom,
                start: parseInt(start_end[0], 10),
                end: parseInt(start_end[1], 10)
            });
        }
    },
    
    copy: function() {
        return new GenomeRegion({
            chrom: this.get('chrom'),
            start: this.get('start'),
            end: this.get('end') 
        });
    },

    length: function() {
        return this.get('end') - this.get('start');
    },
    
    /** Returns region in canonical form chrom:start-end */
    toString: function() {
        return this.get('chrom') + ":" + this.get('start') + "-" + this.get('end');
    },
    
    toJSON: function() {
        return {
            chrom: this.get('chrom'),
            start: this.get('start'),
            end: this.get('end')
        };
    },
    
    /**
     * Compute the type of overlap between this region and another region. The overlap is computed relative to the given/second region; 
     * hence, OVERLAP_START indicates that the first region overlaps the start (but not the end) of the second region.
     */
    compute_overlap: function(a_region) {
        var first_chrom = this.get('chrom'), second_chrom = a_region.get('chrom'),
            first_start = this.get('start'), second_start = a_region.get('start'),
            first_end = this.get('end'), second_end = a_region.get('end'),
            overlap;
            
        // Look at chroms.
        if (first_chrom && second_chrom && first_chrom !== second_chrom) {
            return this.get('DIF_CHROMS');
        }
        
        // Look at regions.
        if (first_start < second_start) {
            if (first_end < second_start) {
                overlap = this.get('BEFORE');
            }
            else if (first_end <= second_end) {
                overlap = this.get('OVERLAP_START');
            }
            else { // first_end > second_end
                overlap = this.get('CONTAINS');
            }
        }
        else { // first_start >= second_start
            if (first_start > second_end) {
                overlap = this.get('AFTER');
            }
            else if (first_end <= second_end) {
                overlap = this.get('CONTAINED_BY');
            }
            else {
                overlap = this.get('OVERLAP_END');
            }
        }

        return overlap;
    },
    
    /**
     * Returns true if this region contains a given region.
     */
    contains: function(a_region) {
        return this.compute_overlap(a_region) === this.get('CONTAINS');  
    },

    /**
     * Returns true if regions overlap.
     */
    overlaps: function(a_region) {
        return _.intersection( [this.compute_overlap(a_region)], 
                               [this.get('DIF_CHROMS'), this.get('BEFORE'), this.get('AFTER')] ).length === 0;  
    }
});

var GenomeRegionCollection = Backbone.Collection.extend({
    model: GenomeRegion
});

/**
 * A genome browser bookmark.
 */
var BrowserBookmark = Backbone.RelationalModel.extend({
    defaults: {
        region: null,
        note: ''
    },

    relations: [
        {
            type: Backbone.HasOne,
            key: 'region',
            relatedModel: GenomeRegion
        }
    ]
});

/**
 * Bookmarks collection.
 */
var BrowserBookmarkCollection = Backbone.Collection.extend({
    model: BrowserBookmark
});

var GenomeWideBigWigData = Backbone.Model.extend({
    defaults: {
        data: null,
        min: 0,
        max: 0
    },

    initialize: function(options) {
        // Set max across dataset by extracting all values, flattening them into a 
        // single array, and getting the min and max.
        var values = _.flatten( _.map(this.get('data'), function(d) {
            if (d.data.length !== 0) {
                // Each data point has the form [position, value], so return all values.
                return _.map(d.data, function(p) {
                    return p[1];
                });
            }
            else {
                return 0;
            }
        }) );
        this.set('max', _.max(values));
        this.set('min', _.min(values));
    }
});

/**
 * Genome-wide summary tree dataset.
 */
var GenomeWideSummaryTreeData = Backbone.RelationalModel.extend({
    defaults: {
        data: null,
        min: 0,
        max: 0
    },
    
    initialize: function(options) {
        // Set max across dataset.
        var max_data = _.max(this.get('data'), function(d) {
            if (!d || typeof d === 'string') { return 0; }
            return d[1];
        });
        this.attributes.max = (max_data && typeof max_data !== 'string' ? max_data[1] : 0);
    }
});

/**
 * A track of data in a genome visualization.
 */
// TODO: rename to Track and merge with Trackster's Track object.
var BackboneTrack = Dataset.extend({

    initialize: function(options) {
        // Dataset id is unique ID for now.
        this.set('id', options.dataset_id);

        // Create genome-wide dataset if available.
        var genome_wide_data = this.get('genome_wide_data');
        if (genome_wide_data) {
            var gwd_class = (this.get('track_type') === 'LineTrack' ? 
                             GenomeWideBigWigData : GenomeWideSummaryTreeData);
            this.set('genome_wide_data', new gwd_class(genome_wide_data));
        }
    }
});

/**
 * A visualization.
 */
var Visualization = Backbone.RelationalModel.extend({
    defaults: {
        id: '',
        title: '',
        type: '',
        dbkey: '',
        tracks: null
    },

    relations: [
        {
            type: Backbone.HasMany,
            key: 'tracks',
            relatedModel: BackboneTrack
        }
    ],

    // Use function because visualization_url changes depending on viz.
    // FIXME: all visualizations should save to the same URL (and hence
    // this function won't be needed).
    url: function() { 
        return galaxy_paths.get("visualization_url");
    },
    
    /**
     * POSTs visualization's JSON to its URL using the parameter 'vis_json'
     * Note: This is necessary because (a) Galaxy requires keyword args and 
     * (b) Galaxy does not handle PUT now.
     */
    save: function() {
        return $.ajax({
            url: this.url(),
            type: "POST",
            dataType: "json",
            data: { 
                vis_json: JSON.stringify(this)
            }
        });
    }
});

/**
 * A Genome space visualization.
 */
var GenomeVisualization = Visualization.extend({
    defaults: _.extend({}, Visualization.prototype.defaults, {
        bookmarks: null,
        viewport: null
    })
});

/**
 * Configuration data for a Trackster track.
 */
var TrackConfig = Backbone.Model.extend({
    
});

/**
 * -- Routers --
 */

/**
 * Router for track browser.
 */
var TrackBrowserRouter = Backbone.Router.extend({    
    initialize: function(options) {
        this.view = options.view;
        
        // Can't put regular expression in routes dictionary.
        // NOTE: parentheses are used to denote parameters returned to callback.
        this.route(/([\w]+)$/, 'change_location');
        this.route(/([\w]+\:[\d,]+-[\d,]+)$/, 'change_location');
        
        // Handle navigate events from view.
        var self = this;
        self.view.on("navigate", function(new_loc) {
            self.navigate(new_loc);
        });
    },
    
    change_location: function(new_loc) {
        this.view.go_to(new_loc);
    }
});

/**
 * -- Helper functions.
 */
 
/**
 * Use a popup grid to add more datasets.
 */
var add_datasets = function(dataset_url, add_track_async_url, success_fn) {
    $.ajax({
        url: dataset_url,
        data: { "f-dbkey": view.dbkey },
        error: function() { alert( "Grid failed" ); },
        success: function(table_html) {
            show_modal(
                "Select datasets for new tracks",
                table_html, {
                    "Cancel": function() {
                        hide_modal();
                    },
                    "Add": function() {
                        var requests = [];
                        $('input[name=id]:checked,input[name=ldda_ids]:checked').each(function() {
                            var data = {
                                    'track_config': true,
                                    'hda_ldda': 'hda'
                                },
                                id = $(this).val();
                                if ($(this).attr("name") !== "id") {
                                    data['hda_ldda'] = 'ldda';
                                }
                                requests[requests.length] = $.ajax({
                                    url: add_track_async_url + "/" + id,
                                    data: data,
                                    dataType: "json"
                                });
                        });
                        // To preserve order, wait until there are definitions for all tracks and then add 
                        // them sequentially.
                        $.when.apply($, requests).then(function() {
                            // jQuery always returns an Array for arguments, so need to look at first element
                            // to determine whether multiple requests were made and consequently how to 
                            // map arguments to track definitions.
                            var track_defs = (arguments[0] instanceof Array ?  
                                               $.map(arguments, function(arg) { return arg[0]; }) :
                                               [ arguments[0] ]
                                               );
                            success_fn(track_defs);
                        });
                        hide_modal();
                    }
                }
            );
        }
    });
};

// ---- Exports ----

var exports = (function() {
    if ( typeof module !== 'undefined' && module.exports ) {
        // CommonJS
        return module.exports;
    } else if ( typeof define === 'function' && define.amd ) {
        // AMD
        exports = {};
        define( function() { return exports; } );
        return exports;
    } else {
        // Browser global
        return window;
    }
})();

exports.BrowserBookmark = BrowserBookmark;        
exports.BrowserBookmarkCollection = BrowserBookmarkCollection;
exports.Cache = Cache;
exports.CanvasManager = CanvasManager;
exports.Genome = Genome;
exports.GenomeDataManager = GenomeDataManager;
exports.GenomeRegion = GenomeRegion;
exports.GenomeRegionCollection = GenomeRegionCollection;
exports.GenomeVisualization = GenomeVisualization;
exports.GenomeWideBigWigData = GenomeWideBigWigData;
exports.GenomeWideSummaryTreeData = GenomeWideSummaryTreeData;
exports.ReferenceTrackDataManager = ReferenceTrackDataManager;
exports.ServerStateDeferred = ServerStateDeferred;
exports.TrackBrowserRouter = TrackBrowserRouter;
exports.TrackConfig = TrackConfig;
exports.Visualization = Visualization;
exports.add_datasets = add_datasets;

}).call(this);