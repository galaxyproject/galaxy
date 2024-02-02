import { getGalaxyInstance } from "app";
import Backbone from "backbone";
import $ from "jquery";
import { Dataset } from "mvc/dataset/data";
import { getAppRoot } from "onload/loadConfig";
import _ from "underscore";
import config_mod from "utils/config";
import _l from "utils/localization";
import util_mod from "viz/trackster/util";

/**
 * Mixin for returning custom JSON representation from toJSON. Class attribute to_json_keys defines a set of attributes
 * to include in the representation; to_json_mappers defines mappers for returned objects.
 */
var CustomToJSON = {
    /**
     * Returns JSON representation of object using to_json_keys and to_json_mappers.
     */
    toJSON: function () {
        var self = this;
        var json = {};
        _.each(self.constructor.to_json_keys, (k) => {
            var val = self.get(k);
            if (k in self.constructor.to_json_mappers) {
                val = self.constructor.to_json_mappers[k](val, self);
            }
            json[k] = val;
        });
        return json;
    },
};

/**
 * Model, view, and controller objects for Galaxy visualization framework.
 *
 * Models have no references to views, instead using events to indicate state
 * changes; this is advantageous because multiple views can use the same object
 * and models can be used without views.
 */

/**
 * Use a popup grid to select datasets from histories or libraries. After datasets are selected,
 * track definitions are obtained from the server and the success_fn is called with the list of
 * definitions for selected datasets.
 */
var select_datasets = (filters, success_fn) => {
    const Galaxy = getGalaxyInstance();
    Galaxy.data.dialog(
        (files) => {
            var requests = [];
            files.forEach((f) => {
                requests.push(
                    $.ajax({
                        url: `${getAppRoot()}api/datasets/${f.id}`,
                        dataType: "json",
                        data: {
                            data_type: "track_config",
                            hda_ldda: f.src === "ldda" ? "ldda" : "hda",
                        },
                    })
                );
            });
            // To preserve order, wait until there are definitions for all tracks and then add
            // them sequentially.
            $.when.apply($, requests).then(function () {
                // jQuery always returns an Array for arguments, so need to look at first element
                // to determine whether multiple requests were made and consequently how to
                // map arguments to track definitions.
                var track_defs = arguments[0] instanceof Array ? $.map(arguments, (arg) => arg[0]) : [arguments[0]];
                success_fn(track_defs);
            });
        },
        { format: null, multiple: true }
    );
};

// --------- Models ---------

/**
 * Canvas manager is used to create canvases for browsers as well as providing a pattern cache
 */
var CanvasManager = function (default_font) {
    this.default_font = default_font !== undefined ? default_font : "9px Monaco, Lucida Console, monospace";

    this.dummy_canvas = this.new_canvas();
    this.dummy_context = this.dummy_canvas.getContext("2d");
    this.dummy_context.font = this.default_font;

    this.char_width_px = this.dummy_context.measureText("A").width;

    this.patterns = {};

    // FIXME: move somewhere to make this more general
    this.load_pattern("right_strand", "/visualization/strand_right.png");
    this.load_pattern("left_strand", "/visualization/strand_left.png");
    this.load_pattern("right_strand_inv", "/visualization/strand_right_inv.png");
    this.load_pattern("left_strand_inv", "/visualization/strand_left_inv.png");
};

_.extend(CanvasManager.prototype, {
    load_pattern: function (key, path) {
        var patterns = this.patterns;
        var dummy_context = this.dummy_context;
        var image = new Image();
        image.src = `${getAppRoot()}static/images${path}`;
        image.onload = () => {
            patterns[key] = dummy_context.createPattern(image, "repeat");
        };
    },
    get_pattern: function (key) {
        return this.patterns[key];
    },
    new_canvas: function () {
        var canvas = $("<canvas/>")[0];
        // Keep a reference back to the manager
        canvas.manager = this;
        return canvas;
    },
});

/**
 * Generic cache that handles key/value pairs. Keys can be any object that can be
 * converted to a String and compared.
 */
var Cache = Backbone.Model.extend({
    defaults: {
        num_elements: 20,
        // Objects in cache; indexes into cache are strings of keys.
        obj_cache: null,
        // key_ary contains keys for objects in cache.
        key_ary: null,
    },

    initialize: function (options) {
        this.clear();
    },

    /**
     * Get an element from the cache using its key.
     */
    get_elt: function (key) {
        var obj_cache = this.attributes.obj_cache;
        var key_ary = this.attributes.key_ary;
        var key_str = key.toString();

        var index = _.indexOf(key_ary, (k) => k.toString() === key_str);

        // Update cache.
        if (index !== -1) {
            // Object is in cache, so update it.
            if (obj_cache[key_str].stale) {
                // Object is stale: remove key and object.
                key_ary.splice(index, 1);
                delete obj_cache[key_str];
            } else {
                // Move key to back because it is most recently used.
                this.move_key_to_end(key, index);
            }
        }

        return obj_cache[key_str];
    },

    /**
     * Put an element into the cache.
     */
    set_elt: function (key, value) {
        var obj_cache = this.attributes.obj_cache;
        var key_ary = this.attributes.key_ary;
        var key_str = key.toString();
        var num_elements = this.attributes.num_elements;

        // Update keys, objects.
        if (!obj_cache[key_str]) {
            // Add object to cache.

            if (key_ary.length >= num_elements) {
                // Cache full, so remove first element.
                var deleted_key = key_ary.shift();
                delete obj_cache[deleted_key.toString()];
            }

            // Add key.
            key_ary.push(key);
        }

        // Add object.
        obj_cache[key_str] = value;
        return value;
    },

    /**
     * Move key to end of cache. Keys are removed from the front, so moving a key to the end
     * delays the key's removal.
     */
    move_key_to_end: function (key, index) {
        this.attributes.key_ary.splice(index, 1);
        this.attributes.key_ary.push(key);
    },

    /**
     * Clear all elements from the cache.
     */
    clear: function () {
        this.attributes.obj_cache = {};
        this.attributes.key_ary = [];
    },

    /** Returns the number of elements in the cache. */
    size: function () {
        return this.attributes.key_ary.length;
    },

    /** Returns key most recently added to cache. */
    most_recently_added: function () {
        return this.size() === 0
            ? null
            : // Most recent key is at the end of key array.
              this.attributes.key_ary[this.attributes.key_ary.length - 1];
    },
});

/**
 * Data manager for genomic data. Data is connected to and queryable by genomic regions.
 */
var GenomeDataManager = Cache.extend({
    defaults: _.extend({}, Cache.prototype.defaults, {
        dataset: null,
        genome: null,
        init_data: null,
        min_region_size: 200,
        filters_manager: null,
        data_type: "data",
        data_mode_compatible: function (entry, mode) {
            return true;
        },
        can_subset: function (entry) {
            return false;
        },
    }),

    /**
     * Initialization.
     */
    initialize: function (options) {
        Cache.prototype.initialize.call(this);

        // Set initial entries in data manager.
        var initial_entries = this.get("init_data");
        if (initial_entries) {
            this.add_data(initial_entries);
        }
    },

    /**
     * Add data entries to manager; each entry should be a dict with attributes region (key), data, and data_type.
     * If necessary, manager size is increased to hold all data.
     */
    add_data: function (entries) {
        // Increase size to accomodate all entries.
        if (this.get("num_elements") < entries.length) {
            this.set("num_elements", entries.length);
        }

        // Put data into manager.
        var self = this;
        _.each(entries, (entry) => {
            self.set_data(entry.region, entry);
        });
    },

    /**
     * Returns deferred that resolves to true when dataset is ready (or false if dataset
     * cannot be used).
     */
    data_is_ready: function () {
        var dataset = this.get("dataset");
        var ready_deferred = $.Deferred();

        var // If requesting raw data, query dataset state; if requesting (converted) data,
            // need to query converted datasets state.
            query_type =
                this.get("data_type") === "raw_data"
                    ? "state"
                    : this.get("data_type") === "data"
                    ? "converted_datasets_state"
                    : "error";

        var ss_deferred = new util_mod.ServerStateDeferred({
            ajax_settings: {
                url: this.get("dataset").url(),
                data: {
                    hda_ldda: dataset.get("hda_ldda"),
                    data_type: query_type,
                },
                dataType: "json",
            },
            interval: 5000,
            success_fn: function (response) {
                return response !== "pending";
            },
        });

        $.when(ss_deferred.go()).then((response) => {
            ready_deferred.resolve(response === "ok" || response === "data");
        });
        return ready_deferred;
    },

    /**
     * Perform a feature search from server; returns Deferred object that resolves when data is available.
     */
    search_features: function (query) {
        var dataset = this.get("dataset");

        var params = {
            query: query,
            hda_ldda: dataset.get("hda_ldda"),
            data_type: "features",
        };

        return $.getJSON(dataset.url(), params);
    },

    /**
     * Load data from server and manages data entries. Adds a Deferred to manager
     * for region; when data becomes available, replaces Deferred with data.
     * Returns the Deferred that resolves when data is available.
     */
    load_data: function (region, mode, resolution, extra_params) {
        // Setup data request params.
        var dataset = this.get("dataset");

        var params = {
            data_type: this.get("data_type"),
            chrom: region.get("chrom"),
            low: region.get("start"),
            high: region.get("end"),
            mode: mode,
            resolution: resolution,
            hda_ldda: dataset.get("hda_ldda"),
        };

        $.extend(params, extra_params);

        // Add track filters to params.
        var filters_manager = this.get("filters_manager");
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

        var entry = $.getJSON(dataset.url(), params, (result) => {
            // Add region to the result.
            result.region = region;
            manager.set_data(region, result);
        });

        this.set_data(region, entry);
        return entry;
    },

    /**
     * Get data from dataset.
     */
    get_data: function (region, mode, resolution, extra_params) {
        // Look for entry and return if it's a deferred or if data available is compatible with mode.
        var entry = this.get_elt(region);
        if (entry && (util_mod.is_deferred(entry) || this.get("data_mode_compatible")(entry, mode))) {
            return entry;
        }

        //
        // Look in cache for data that can be used.
        // TODO: this logic could be improved if the visualization knew whether
        // the data was "index" or "data."
        //
        var key_ary = this.get("key_ary");

        var obj_cache = this.get("obj_cache");
        var entry_region;
        var is_subregion;
        for (var i = 0; i < key_ary.length; i++) {
            entry_region = key_ary[i];

            if (entry_region.contains(region)) {
                is_subregion = true;

                // This entry has data in the requested range. Return if data
                // is compatible and can be subsetted.
                entry = obj_cache[entry_region.toString()];
                if (
                    util_mod.is_deferred(entry) ||
                    (this.get("data_mode_compatible")(entry, mode) && this.get("can_subset")(entry))
                ) {
                    this.move_key_to_end(entry_region, i);

                    // If there's data, subset it.
                    if (!util_mod.is_deferred(entry)) {
                        var subset_entry = this.subset_entry(entry, region);
                        this.set_data(region, subset_entry);
                        entry = subset_entry;
                    }

                    return entry;
                }
            }
        }

        // FIXME: There _may_ be instances where region is a subregion of another entry but cannot be
        // subsetted. For these cases, do not increase length because region will never be found (and
        // an infinite loop will occur.)
        // If needed, extend region to make it minimum size.
        if (!is_subregion && region.length() < this.attributes.min_region_size) {
            // IDEA: alternative heuristic is to find adjacent cache entry to region and use that to extend.
            // This would prevent bad extensions when zooming in/out while still preserving the behavior
            // below.

            // Use copy of region to avoid changing actual region.
            region = region.copy();

            // Use heuristic to extend region: extend relative to last data request.
            var last_request = this.most_recently_added();
            if (!last_request || region.get("start") > last_request.get("start")) {
                // This request is after the last request, so extend right.
                region.set("end", region.get("start") + this.attributes.min_region_size);
            } else {
                // This request is after the last request, so extend left.
                region.set("start", region.get("end") - this.attributes.min_region_size);
            }

            // Trim region to avoid invalid coordinates.
            region.set("genome", this.attributes.genome);
            region.trim();
        }

        return this.load_data(region, mode, resolution, extra_params);
    },

    /**
     * Alias for set_elt for readbility.
     */
    set_data: function (region, entry) {
        this.set_elt(region, entry);
    },

    /** "Deep" data request; used as a parameter for DataManager.get_more_data() */
    DEEP_DATA_REQ: "deep",

    /** "Broad" data request; used as a parameter for DataManager.get_more_data() */
    BROAD_DATA_REQ: "breadth",

    /**
     * Gets more data for a region using either a depth-first or a breadth-first approach.
     */
    get_more_data: function (region, mode, resolution, extra_params, req_type) {
        var cur_data = this._mark_stale(region);
        if (!(cur_data && this.get("data_mode_compatible")(cur_data, mode))) {
            console.log("ERROR: problem with getting more data: current data is not compatible");
            return;
        }

        //
        // Set parameters based on request type.
        //
        var query_low = region.get("start");
        if (req_type === this.DEEP_DATA_REQ) {
            // Use same interval but set start_val to skip data that's already in cur_data.
            $.extend(extra_params, {
                start_val: cur_data.data.length + 1,
            });
        } else if (req_type === this.BROAD_DATA_REQ) {
            // To get past an area of extreme feature depth, set query low to be after either
            // (a) the maximum high or HACK/FIXME (b) the end of the last feature returned.
            query_low = (cur_data.max_high ? cur_data.max_high : cur_data.data[cur_data.data.length - 1][2]) + 1;
        }
        var query_region = region.copy().set("start", query_low);

        //
        // Get additional data, append to current data, and set new data. Use a custom deferred object
        // to signal when new data is available.
        //
        var data_manager = this;

        var new_data_request = this.load_data(query_region, mode, resolution, extra_params);

        var new_data_available = $.Deferred();
        // load_data sets cache to new_data_request, but use custom deferred object so that signal and data
        // is all data, not just new data.
        this.set_data(region, new_data_available);
        $.when(new_data_request).then((result) => {
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
     * Returns true if more detailed data can be obtained for entry.
     */
    can_get_more_detailed_data: function (region) {
        var cur_data = this.get_elt(region);

        // Can only get more detailed data for bigwig data that has less than 8000 data points.
        // Summary tree returns *way* too much data, and 8000 data points ~ 500KB.
        return cur_data.dataset_type === "bigwig" && cur_data.data.length < 8000;
    },

    /**
     * Returns more detailed data for an entry.
     */
    get_more_detailed_data: function (region, mode, resolution, detail_multiplier, extra_params) {
        // Mark current entry as stale.
        var cur_data = this._mark_stale(region);
        if (!cur_data) {
            console.log("ERROR getting more detailed data: no current data");
            return;
        }

        if (!extra_params) {
            extra_params = {};
        }

        // Use additional parameters to get more detailed data.
        if (cur_data.dataset_type === "bigwig") {
            // FIXME: constant should go somewhere.
            extra_params.num_samples = 1000 * detail_multiplier;
        }

        return this.load_data(region, mode, resolution, extra_params);
    },

    /**
     * Marks cache data as stale.
     */
    _mark_stale: function (region) {
        var entry = this.get_elt(region);
        if (!entry) {
            console.log("ERROR: no data to mark as stale: ", this.get("dataset"), region.toString());
        }
        entry.stale = true;
        return entry;
    },

    /**
     * Returns an array of data with each entry representing one chromosome/contig
     * of data or, if data is not available, returns a Deferred that resolves to the
     * data when it becomes available.
     */
    get_genome_wide_data: function (genome) {
        // -- Get all data. --

        var self = this;

        var all_data_available = true;

        var //  Map chromosome info into genome data.
            gw_data = _.map(genome.get("chroms_info").chrom_info, (chrom_info) => {
                var chrom_data = self.get_elt(
                    new GenomeRegion({
                        chrom: chrom_info.chrom,
                        start: 0,
                        end: chrom_info.len,
                    })
                );

                // Set flag if data is not available.
                if (!chrom_data) {
                    all_data_available = false;
                }

                return chrom_data;
            });

        // -- If all data is available, return it. --
        if (all_data_available) {
            return gw_data;
        }

        // -- All data is not available, so load from server. --

        var deferred = $.Deferred();
        $.getJSON(this.get("dataset").url(), { data_type: "genome_data" }, (genome_wide_data) => {
            self.add_data(genome_wide_data.data);
            deferred.resolve(genome_wide_data.data);
        });

        return deferred;
    },

    /**
     * Returns entry with only data in the subregion.
     */
    subset_entry: function (entry, subregion) {
        // Dictionary from entry type to function for subsetting data.
        var subset_fns = {
            bigwig: function (data, subregion) {
                return _.filter(
                    data,
                    (data_point) => data_point[0] >= subregion.get("start") && data_point[0] <= subregion.get("end")
                );
            },
            refseq: function (data, subregion) {
                var seq_start = subregion.get("start") - entry.region.get("start");
                return entry.data.slice(seq_start, seq_start + subregion.length());
            },
        };

        // Subset entry if there is a function for subsetting and regions are not the same.
        var subregion_data = entry.data;
        if (!entry.region.same(subregion) && entry.dataset_type in subset_fns) {
            subregion_data = subset_fns[entry.dataset_type](entry.data, subregion);
        }

        // Return entry with subregion's data.
        return {
            region: subregion,
            data: subregion_data,
            dataset_type: entry.dataset_type,
        };
    },
});

var GenomeReferenceDataManager = GenomeDataManager.extend({
    initialize: function (options) {
        // Use generic object in place of dataset and set urlRoot to fetch data.
        var dataset_placeholder = new Backbone.Model();
        dataset_placeholder.urlRoot = options.data_url;
        this.set("dataset", dataset_placeholder);
    },

    load_data: function (region, mode, resolution, extra_params) {
        // Fetch data if region is not too large.
        return region.length() <= 100000
            ? GenomeDataManager.prototype.load_data.call(this, region, mode, resolution, extra_params)
            : { data: null, region: region };
    },
});

/**
 * A genome build.
 */
var Genome = Backbone.Model.extend({
    defaults: {
        name: null,
        key: null,
        chroms_info: null,
    },

    initialize: function (options) {
        this.id = options.dbkey;
    },

    /**
     * Shorthand for getting to chromosome information.
     */
    get_chroms_info: function () {
        return this.attributes.chroms_info.chrom_info;
    },

    /**
     * Returns a GenomeRegion object denoting a complete chromosome.
     */
    get_chrom_region: function (chr_name) {
        // FIXME: use findWhere in underscore 1.4
        var chrom_info = _.find(this.get_chroms_info(), (chrom_info) => chrom_info.chrom === chr_name);
        return new GenomeRegion({
            chrom: chrom_info.chrom,
            end: chrom_info.len,
        });
    },

    /** Returns the length of a chromosome. */
    get_chrom_len: function (chr_name) {
        // FIXME: use findWhere in underscore 1.4
        return _.find(this.get_chroms_info(), (chrom_info) => chrom_info.chrom === chr_name).len;
    },
});

/**
 * A genomic region.
 */
var GenomeRegion = Backbone.Model.extend(
    {
        defaults: {
            chrom: null,
            start: 0,
            end: 0,
            str_val: null,
            genome: null,
        },

        /**
         * Returns true if this region is the same as a given region.
         * It does not test the genome right now.
         */
        same: function (region) {
            return (
                this.attributes.chrom === region.get("chrom") &&
                this.attributes.start === region.get("start") &&
                this.attributes.end === region.get("end")
            );
        },

        /**
         * If from_str specified, use it to initialize attributes.
         */
        initialize: function (options) {
            if (options.from_str) {
                var pieces = options.from_str.split(":");
                var chrom = pieces[0];
                var start_end = pieces[1].split("-");
                this.set({
                    chrom: chrom,
                    start: parseInt(start_end[0], 10),
                    end: parseInt(start_end[1], 10),
                });
            }

            // Keep a copy of region's string value for fast lookup.
            this.attributes.str_val = `${this.get("chrom")}:${this.get("start")}-${this.get("end")}`;

            // Set str_val on attribute change.
            this.on(
                "change",
                function () {
                    this.attributes.str_val = `${this.get("chrom")}:${this.get("start")}-${this.get("end")}`;
                },
                this
            );
        },

        copy: function () {
            return new GenomeRegion({
                chrom: this.get("chrom"),
                start: this.get("start"),
                end: this.get("end"),
            });
        },

        length: function () {
            return this.get("end") - this.get("start");
        },

        /** Returns region in canonical form chrom:start-end */
        toString: function () {
            return this.attributes.str_val;
        },

        toJSON: function () {
            return {
                chrom: this.get("chrom"),
                start: this.get("start"),
                end: this.get("end"),
            };
        },

        /**
         * Compute the type of overlap between this region and another region. The overlap is computed relative to the given/second region;
         * hence, OVERLAP_START indicates that the first region overlaps the start (but not the end) of the second region.
         */
        compute_overlap: function (a_region) {
            var first_chrom = this.get("chrom");
            var second_chrom = a_region.get("chrom");
            var first_start = this.get("start");
            var second_start = a_region.get("start");
            var first_end = this.get("end");
            var second_end = a_region.get("end");
            var overlap;

            // Compare chroms.
            if (first_chrom && second_chrom && first_chrom !== second_chrom) {
                return GenomeRegion.overlap_results.DIF_CHROMS;
            }

            // Compare regions.
            if (first_start < second_start) {
                if (first_end < second_start) {
                    overlap = GenomeRegion.overlap_results.BEFORE;
                } else if (first_end < second_end) {
                    overlap = GenomeRegion.overlap_results.OVERLAP_START;
                } else {
                    // first_end >= second_end
                    overlap = GenomeRegion.overlap_results.CONTAINS;
                }
            } else if (first_start > second_start) {
                if (first_start > second_end) {
                    overlap = GenomeRegion.overlap_results.AFTER;
                } else if (first_end <= second_end) {
                    overlap = GenomeRegion.overlap_results.CONTAINED_BY;
                } else {
                    overlap = GenomeRegion.overlap_results.OVERLAP_END;
                }
            } else {
                // first_start === second_start
                overlap =
                    first_end >= second_end
                        ? GenomeRegion.overlap_results.CONTAINS
                        : GenomeRegion.overlap_results.CONTAINED_BY;
            }

            return overlap;
        },

        /**
         * Trim a region to match genome's constraints.
         */
        trim: function (genome) {
            // Assume that all chromosome/contigs start at 0.
            if (this.attributes.start < 0) {
                this.attributes.start = 0;
            }

            // Only try to trim the end if genome is set.
            if (this.attributes.genome) {
                var chrom_len = this.attributes.genome.get_chrom_len(this.attributes.chrom);
                if (this.attributes.end > chrom_len) {
                    this.attributes.end = chrom_len - 1;
                }
            }

            return this;
        },

        /**
         * Returns true if this region contains a given region.
         */
        contains: function (a_region) {
            return this.compute_overlap(a_region) === GenomeRegion.overlap_results.CONTAINS;
        },

        /**
         * Returns true if regions overlap.
         */
        overlaps: function (a_region) {
            return (
                _.intersection(
                    [this.compute_overlap(a_region)],
                    [
                        GenomeRegion.overlap_results.DIF_CHROMS,
                        GenomeRegion.overlap_results.BEFORE,
                        GenomeRegion.overlap_results.AFTER,
                    ]
                ).length === 0
            );
        },
    },
    {
        overlap_results: {
            DIF_CHROMS: 1000,
            BEFORE: 1001,
            CONTAINS: 1002,
            OVERLAP_START: 1003,
            OVERLAP_END: 1004,
            CONTAINED_BY: 1005,
            AFTER: 1006,
        },
    }
);

var GenomeRegionCollection = Backbone.Collection.extend({
    model: GenomeRegion,
});

/**
 * A genome browser bookmark.
 */
var BrowserBookmark = Backbone.Model.extend({
    defaults: {
        region: null,
        note: "",
    },

    initialize: function (options) {
        this.set("region", new GenomeRegion(options.region));
    },
});

/**
 * Bookmarks collection.
 */
var BrowserBookmarkCollection = Backbone.Collection.extend({
    model: BrowserBookmark,
});

/**
 * A track of data in a genome visualization.
 */
// TODO: rename to Track and merge with Trackster's Track object.
var BackboneTrack = Backbone.Model.extend(CustomToJSON).extend(
    {
        defaults: {
            mode: "Auto",
        },

        initialize: function (options) {
            this.set("dataset", new Dataset(options.dataset));

            // -- Set up config settings. --
            var models = [
                {
                    key: "name",
                    default_value: this.get("dataset").get("name"),
                },
                { key: "color" },
                {
                    key: "min_value",
                    label: "Min Value",
                    type: "float",
                    default_value: 0,
                },
                {
                    key: "max_value",
                    label: "Max Value",
                    type: "float",
                    default_value: 1,
                },
            ];

            this.set("config", config_mod.ConfigSettingCollection.from_models_and_saved_values(models, options.prefs));

            // -- Set up data manager. --
            var preloaded_data = this.get("preloaded_data");
            if (preloaded_data) {
                preloaded_data = preloaded_data.data;
            } else {
                preloaded_data = [];
            }
            this.set(
                "data_manager",
                new GenomeDataManager({
                    dataset: this.get("dataset"),
                    init_data: preloaded_data,
                })
            );
        },
    },
    {
        // This definition matches that produced by to_dict() methods in tracks.js
        to_json_keys: ["track_type", "dataset", "prefs", "mode", "filters", "tool_state"],
        to_json_mappers: {
            prefs: function (p, self) {
                if (_.size(p) === 0) {
                    p = {
                        name: self.get("config").get("name").get("value"),
                        color: self.get("config").get("color").get("value"),
                    };
                }
                return p;
            },
            dataset: function (d) {
                return {
                    id: d.id,
                    hda_ldda: d.get("hda_ldda"),
                };
            },
        },
    }
);

var BackboneTrackCollection = Backbone.Collection.extend({
    model: BackboneTrack,
});

/**
 * A visualization.
 */
var Visualization = Backbone.Model.extend({
    defaults: {
        title: "",
        type: "",
    },

    urlRoot: `${getAppRoot()}api/visualizations`,

    /**
     * POSTs visualization's JSON to its URL using the parameter 'vis_json'
     * Note: This is necessary because (a) Galaxy requires keyword args and
     * (b) Galaxy does not handle PUT now.
     */
    save: function () {
        return $.ajax({
            url: this.url(),
            type: "POST",
            dataType: "json",
            data: {
                vis_json: JSON.stringify(this),
            },
        });
    },
});

/**
 * A visualization of genome data.
 */
var GenomeVisualization = Visualization.extend(CustomToJSON).extend(
    {
        defaults: _.extend({}, Visualization.prototype.defaults, {
            dbkey: "",
            drawables: null,
            bookmarks: null,
            viewport: null,
        }),

        initialize: function (options) {
            // Replace drawables with tracks.
            this.set("drawables", new BackboneTrackCollection(options.tracks));

            var models = [];
            this.set("config", config_mod.ConfigSettingCollection.from_models_and_saved_values(models, options.prefs));

            // Clear track and data definitions to avoid storing large objects.
            this.unset("tracks");
            this.get("drawables").each((d) => {
                d.unset("preloaded_data");
            });
        },

        /**
         * Add a track or array of tracks to the visualization.
         */
        add_tracks: function (tracks) {
            this.get("drawables").add(tracks);
        },
    },
    {
        // This definition matches that produced by to_dict() methods in tracks.js
        to_json_keys: ["view", "viewport", "bookmarks"],

        to_json_mappers: {
            view: function (dummy, self) {
                return {
                    obj_type: "View",
                    prefs: {
                        name: self.get("title"),
                        content_visible: true,
                    },
                    drawables: self.get("drawables"),
                };
            },
        },
    }
);

/**
 * -- Routers --
 */

/**
 * Router for track browser.
 */
var TrackBrowserRouter = Backbone.Router.extend({
    initialize: function (options) {
        this.view = options.view;

        // Can't put regular expression in routes dictionary.
        // NOTE: parentheses are used to denote parameters returned to callback.
        this.route(/([\w]+)$/, "change_location");
        this.route(/([\w+]+:[\d,]+-[\d,]+)$/, "change_location");

        // Handle navigate events from view.
        this.view.on("navigate", (new_loc) => {
            this.navigate(new_loc);
        });
    },

    change_location: function (new_loc) {
        this.view.go_to(new_loc);
    },
});

export default {
    BackboneTrack: BackboneTrack,
    BrowserBookmark: BrowserBookmark,
    BrowserBookmarkCollection: BrowserBookmarkCollection,
    Cache: Cache,
    CanvasManager: CanvasManager,
    Genome: Genome,
    GenomeDataManager: GenomeDataManager,
    GenomeRegion: GenomeRegion,
    GenomeRegionCollection: GenomeRegionCollection,
    GenomeVisualization: GenomeVisualization,
    GenomeReferenceDataManager: GenomeReferenceDataManager,
    TrackBrowserRouter: TrackBrowserRouter,
    Visualization: Visualization,
    select_datasets: select_datasets,
};
