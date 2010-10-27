/* Trackster
    2010, James Taylor, Kanwei Li
*/

var DENSITY = 200,
    FEATURE_LEVELS = 10,
    MAX_FEATURE_DEPTH = 50,
    CONNECTOR_COLOR = "#ccc",
    DATA_ERROR = "There was an error in indexing this dataset.",
    DATA_NOCONVERTER = "A converter for this dataset is not installed. Please check your datatypes_conf.xml file.",
    DATA_NONE = "No data for this chrom/contig.",
    DATA_PENDING = "Currently indexing... please wait",
    DATA_LOADING = "Loading data...",
    FILTERABLE_CLASS = "filterable",
    CACHED_TILES_FEATURE = 10,
    CACHED_TILES_LINE = 5,
    CACHED_DATA = 5,
    DUMMY_CANVAS = document.createElement("canvas"),
    RIGHT_STRAND, LEFT_STRAND;
    
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

var View = function( container, title, vis_id, dbkey ) {
    this.container = container;
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
        this.intro_div = $("<div/>").addClass("intro").text("Select a chrom from the dropdown below").hide(); // Future overlay
        
        this.nav_container = $("<div/>").addClass("nav-container").appendTo(parent_element);
        this.nav_labeltrack = $("<div/>").addClass("nav-labeltrack").appendTo(this.nav_container);
        this.nav = $("<div/>").addClass("nav").appendTo(this.nav_container);
        this.overview = $("<div/>").addClass("overview").appendTo(this.nav);
        this.overview_viewport = $("<div/>").addClass("overview-viewport").appendTo(this.overview);
        this.overview_close = $("<a href='javascript:void(0);'>Close Overview</a>").addClass("overview-close").hide().appendTo(this.overview_viewport);
        this.overview_highlight = $("<div />").addClass("overview-highlight").hide().appendTo(this.overview_viewport);
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
        this.zo_link = $("<a/>").click(function() { view.zoom_out(); view.redraw(); }).html('<img src="'+image_path+'/fugue/magnifier-zoom-out.png" />').appendTo(this.chrom_form);
        this.zi_link = $("<a/>").click(function() { view.zoom_in(); view.redraw(); }).html('<img src="'+image_path+'/fugue/magnifier-zoom.png" />').appendTo(this.chrom_form);        
        
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
        
        this.overview_close.bind("click", function() {
            for (var track_id = 0, len = view.tracks.length; track_id < len; track_id++) {
                view.tracks[track_id].is_overview = false;
            }
            $(this).siblings().filter("canvas").remove();
            $(this).parent().css("height", view.overview_box.height());
            view.overview_highlight.hide();
            $(this).hide();
        });
        
        this.viewport_container.bind( "dragstart", function( e ) {
            this.original_low = view.low;
            this.current_height = e.clientY;
            this.current_x = e.offsetX;
            this.enable_pan = (e.clientX < view.viewport_container.width() - 16) ? true : false; // Fix webkit scrollbar
        }).bind( "drag", function( e ) {
            if (!this.enable_pan || this.in_reordering) { return; }
            var container = $(this);
            var delta = e.offsetX - this.current_x;
            var new_scroll = container.scrollTop() - (e.clientY - this.current_height);
            container.scrollTop(new_scroll);
            this.current_height = e.clientY;
            this.current_x = e.offsetX;

            var delta_chrom = Math.round(delta / view.viewport_container.width() * (view.high - view.low));
            view.move_delta(delta_chrom);
        });
        
        this.top_labeltrack.bind( "dragstart", function(e) {
            this.drag_origin_x = e.clientX;
            this.drag_origin_pos = e.clientX / view.viewport_container.width() * (view.high - view.low) + view.low;
            this.drag_div = $("<div />").css( { 
                "height": view.content_div.height()+30, "top": "0px", "position": "absolute", 
                "background-color": "#cfc", "border": "1px solid #6a6", "opacity": 0.5, "z-index": 1000
            } ).appendTo( $(this) );
        }).bind( "drag", function(e) {
            var min = Math.min(e.clientX, this.drag_origin_x) - view.container.offset().left,
                max = Math.max(e.clientX, this.drag_origin_x) - view.container.offset().left,
                span = (view.high - view.low),
                width = view.viewport_container.width();
            
            view.update_location(Math.round(min / width * span) + view.low, Math.round(max / width * span) + view.low);
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
        this.viewport_container.height( this.container.height() - this.nav_container.height() - 45 );
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

// Generic filter.
var Filter = function( name, index, value ) {
    this.name = name;
    this.index = index;
    this.value = value;
};

// Number filter for a track.
var NumberFilter = function( name, index ) {
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
$.extend( NumberFilter.prototype, {
    // Returns true if filter can be applied to element.
    applies_to: function( element ) {
        if ( element.length > this.index ) {
            return true;
        }
        return false;
    },
    // Returns true iff element is in [low, high]; range is inclusive.
    keep: function( element ) {
        if ( !this.applies_to( element ) ) {
            // No element to filter on.
            return true;
        }
        return ( element[this.index] >= this.low && element[this.index] <= this.high );
    },
    // Update filter's min and max values based on element's values.
    update_attrs: function( element ) {
        var updated = false;
        if ( !this.applies_to( element ) ) {
            return updated;
        }
        
        // Update filter's min, max based on element values.
        if ( element[this.index] < this.slider_min ) {
            this.slider_min = element[this.index];
            updated = true;
        }
        if ( element[this.index] > this.slider_max ) {
            this.slider_max = element[this.index];
            updated = false;
        }
        return updated;
    },
    // Update filter's slider.
    update_ui_elt: function () {
        var 
            slider_min = this.slider.slider( "option", "min" ),
            slider_max = this.slider.slider( "option", "max" );
        if (this.slider_min < slider_min || this.slider_max > slider_max) {
            // Need to update slider.        
            this.slider.slider( "option", "min", this.slider_min );
            this.slider.slider( "option", "max", this.slider_max );
            // Refresh slider:
            // TODO: do we want to keep current values or reset to min/max?
            // Currently we reset values:
            this.slider.slider( "option", "values", [ this.slider_min, this.slider_max ] );
            // To use the current values.
            //var values = this.slider.slider( "option", "values" );
            //this.slider.slider( "option", "values", values );
        }
    }
});

// Parse filters dict and return filters.
var get_filters = function( filters_dict ) {
    var filters = [];
    for (var i = 0; i < filters_dict.length; i++) {
        var filter_dict = filters_dict[i];
        var name = filter_dict.name, type = filter_dict.type, index = filter_dict.index;
        if ( type == 'int' || type == 'float' ) {
            filters[i] = new NumberFilter( name, index );
        } else {
            filters[i] = new Filter( name, index, type );
        }
    }
    return filters;
};

var Track = function (name, view, parent_element, filters) {
    this.name = name;
    this.view = view;    
    this.parent_element = parent_element;
    this.filters = (filters !== undefined ? get_filters( filters ) : []);
    this.init_global();
};
$.extend( Track.prototype, {
    init_global: function () {
        this.container_div = $("<div />").addClass('track').css("position", "relative");
        if (!this.hidden) {
            this.header_div = $("<div class='track-header' />").appendTo(this.container_div);
            if (this.view.editor) { this.drag_div = $("<div class='draghandle' />").appendTo(this.header_div); }
            this.name_div = $("<div class='menubutton popup' />").appendTo(this.header_div);
            this.name_div.text(this.name);
            this.name_div.attr( "id", this.name.replace(/\s+/g,'-').replace(/[^a-zA-Z0-9\-]/g,'').toLowerCase() );
        }
        // Create track filtering div.
        this.filtering_div = $("<div class='track-filters'>").appendTo(this.container_div);
        this.filtering_div.hide();
        // Dragging is disabled on div so that actions on slider do not impact viz.
        this.filtering_div.bind( "drag", function(e) {
            e.stopPropagation();
        });
        var filters_table = $("<table class='filters'>").appendTo(this.filtering_div);
        var track = this;
        for (var i = 0; i < this.filters.length; i++) {
            var filter = this.filters[i];
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
        }
        
        this.content_div = $("<div class='track-content'>").appendTo(this.container_div);
        this.parent_element.append(this.container_div);
    },
    init_each: function(params, success_fn) {
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
    var track = this,
        view = track.view;
    
    if (track.hidden) { return; }
    
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
            for (var i, len = track.display_modes.length; i < len; i++) {
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
    var track_dropdown = {};
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
    if (track.filters.length > 0) {
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
            $("#" + track.name_div.attr("id") + "-menu").find("li").eq(2).text(menu_option_text);
            track.filtering_div.toggle();
        };
    }
    track_dropdown.Remove = function() {
        view.remove_track(track);
        if (view.num_tracks === 0) {
            $("#no-tracks").show();
        }
    };
    track.popup_menu = make_popupmenu(track.name_div, track_dropdown);
    show_hide_popupmenu_options(track.popup_menu, "(Show|Hide) filters", false);
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
    draw: function( force ) {
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
    }, delayed_draw: function(track, key, low, high, tile_index, resolution, parent_element, w_scale, draw_tile_ids) {
        // Put a 50ms delay on drawing so that if the user scrolls fast, we don't load extra data
        var id = setTimeout(function() {
            if (low <= track.view.high && high >= track.view.low) {
                var tile_element = track.draw_tile( resolution, tile_index, parent_element, w_scale );
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
    }, set_overview: function() {
        var view = this.view;
        
        if (this.initial_canvas && this.is_overview) {
            view.overview_close.show();
            view.overview_viewport.append(this.initial_canvas);
            view.overview_highlight.show().height(this.initial_canvas.height());
            view.overview_viewport.height(this.initial_canvas.height() + view.overview_box.height());
        }
        $(window).trigger("resize");
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

var LineTrack = function ( name, view, dataset_id, prefs ) {
    this.track_type = "LineTrack";
    this.display_modes = ["Histogram", "Line", "Filled", "Intensity"];
    this.mode = "Histogram";
    Track.call( this, name, view, view.viewport_container );
    TiledTrack.call( this );
    
    this.height_px = 80;
    this.dataset_id = dataset_id;
    this.data_cache = new Cache(CACHED_DATA);
    this.tile_cache = new Cache(CACHED_TILES_LINE);
    this.prefs = { 'color': 'black', 'min_value': undefined, 'max_value': undefined, 'mode': this.mode };
};
$.extend( LineTrack.prototype, TiledTrack.prototype, {
    init: function() {
        var track = this,
            track_id = track.view.tracks.indexOf(track);
        
        track.vertical_range = undefined;
        this.init_each({  stats: true, chrom: track.view.chrom, low: null, high: null,
                                dataset_id: track.dataset_id }, function(result) {
            
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
            
            max_label.css({ position: "absolute", top: "22px", left: "10px" });
            max_label.prependTo(track.container_div);
    
            min_label.css({ position: "absolute", top: track.height_px + 11 + "px", left: "10px" });
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
                y = Math.round( height_px - (y - min_value) / vertical_range * height_px );
                ctx.fillRect(x_scaled, y, delta_x_px, height_px - y);
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
                ctx.lineTo(x_scaled, height_px);
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

var FeatureTrack = function ( name, view, dataset_id, filters, prefs ) {
    this.track_type = "FeatureTrack";
    this.display_modes = ["Auto", "Dense", "Squish", "Pack"];
    Track.call( this, name, view, view.viewport_container, filters );
    TiledTrack.call( this );
    
    this.height_px = 0;
    this.container_div.addClass( "feature-track" );
    this.dataset_id = dataset_id;
    this.zo_slots = {};
    this.show_labels_scale = 0.001;
    this.showing_details = false;
    this.vertical_detail_px = 10;
    this.vertical_nodetail_px = 2;
    this.summary_draw_height = 30;
    this.default_font = "9px Monaco, Lucida Console, monospace";
    this.inc_slots = {};
    this.data_queue = {};
    this.s_e_by_tile = {};
    this.tile_cache = new Cache(CACHED_TILES_FEATURE);
    this.data_cache = new Cache(20);
    this.left_offset = 200;
    
    this.prefs = { 'block_color': '#444', 'label_color': 'black', 'show_counts': true };
};
$.extend( FeatureTrack.prototype, TiledTrack.prototype, {
    init: function() {
        var track = this,
            key = "initial";
            
        this.init_each({    low: track.view.max_low, high: track.view.max_high, dataset_id: track.dataset_id,
                            chrom: track.view.chrom, resolution: this.view.resolution, mode: track.mode }, function (result) {    
            track.mode_div.show();
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
            this.inc_slots[level].w_scale = level;
            this.inc_slots[level].mode = mode;
            this.s_e_by_tile[level] = {};
        }
        // TODO: Should calculate zoom tile index, which will improve performance
        // by only having to look at a smaller subset
        // if (this.s_e_by_tile[0] === undefined) { this.s_e_by_tile[0] = []; }
        var w_scale = this.inc_slots[level].w_scale,
            undone = [],
            highest_slot = 0, // To measure how big to draw canvas
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
                var text_len = CONTEXT.measureText(feature_name).width;
                if (f_start - text_len < 0) {
                    f_end += text_len;
                } else {
                    f_start -= text_len;
                }
            }
            
            var j = 0;
            // Try to fit the feature to the first slot that doesn't overlap any other features in that slot
            while (j <= MAX_FEATURE_DEPTH) {
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
    rect_or_text: function( ctx, w_scale, tile_low, tile_high, feature_start, orig_seq, cigar, y_center ) {
        ctx.textAlign = "center";
        var cur_offset = 0,
            gap = Math.round(w_scale / 2);
        
        for (var cig_id = 0, len = cigar.length; cig_id < len; cig_id++) {
            var cig = cigar[cig_id],
                cig_op = "MIDNSHP"[cig[0]],
                cig_len = cig[1];
            
            if (cig_op === "H" || cig_op === "S") {
                // Go left if it clips
                cur_offset -= cig_len;
            }
            var seq_start = feature_start + cur_offset,
                s_start = Math.floor( Math.max(0, (seq_start - tile_low) * w_scale) ),
                s_end = Math.floor( Math.max(0, (seq_start + cig_len - tile_low) * w_scale) );
                
            switch (cig_op) {
                case "S": // Soft clipping
                case "H": // Hard clipping
                case "M": // Match
                    var seq = orig_seq.slice(cur_offset, cig_len);
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
                        ctx.fillRect(s_start + this.left_offset, y_center + 4, s_end - s_start, 3);
                    }
                    break;
                case "N": // Skipped bases
                    ctx.fillStyle = CONNECTOR_COLOR;
                    ctx.fillRect(s_start + this.left_offset, y_center + 5, s_end - s_start, 1);
                    break;
                case "D": // Deletion
                    ctx.fillStyle = "red";
                    ctx.fillRect(s_start + this.left_offset, y_center + 4, s_end - s_start, 3);
                    break;
                case "P": // TODO: No good way to draw insertions/padding right now, so ignore
                case "I":
                    break;
            }
            cur_offset += cig_len;
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
        var k = (!this.initial_canvas ? "initial" : tile_low + '_' + tile_high);
        var result = this.data_cache.get(k);
        var cur_mode;
        
        if (result === undefined || (this.mode !== "Auto" && result.dataset_type === "summary_tree")) {
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
        
        if (result.dataset_type == "summary_tree") {            
            var points = result.data,
                max = result.max,
                delta_x_px = Math.ceil(result.delta * w_scale);
            
            var max_label = $("<div />").addClass('yaxislabel').text(max);
            
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
            cur_mode = "Summary";
            parent_element.append( canvas );
            return canvas;
        }
        
        if (result.message) {
            canvas.css({
                border: "solid red",
                "border-width": "2px 2px 2px 0px"            
            });
            ctx.fillStyle = "red";
            ctx.textAlign = "left";
            ctx.fillText(result.message, 100 + left_offset, y_scale);
        }
        
        //
        // We're now working at the level of individual data points.
        //
        
        // See if tile is filterable. If so, add class.
        var filterable = false;
        if (result.data) {
            filterable = true;
            for (var f = 0; f < this.filters.length; f++) {
                if ( !this.filters[f].applies_to( result.data[0] ) ) {
                    filterable = false;
                }
            }
        }
        if (filterable) {
            canvas.addClass(FILTERABLE_CLASS);
        }
        
        // Draw data points.
        var data = result.data;
        var j = 0;
        for (var i = 0, len = data.length; i < len; i++) {
            var feature = data[i],
                feature_uid = feature[0],
                feature_start = feature[1],
                feature_end = feature[2],
                feature_name = feature[3];
            
            if (slots[feature_uid] === undefined) {
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
                var f_start = Math.floor( Math.max(0, (feature_start - tile_low) * w_scale) ),
                    f_end   = Math.ceil( Math.min(width, Math.max(0, (feature_end - tile_low) * w_scale)) ),
                    y_center = (mode === "Dense" ? 1 : (1 + slots[feature_uid])) * y_scale;
                
                var thickness, y_start, thick_start = null, thick_end = null;
                
                if (result.dataset_type === "bai") {
                    var cigar = feature[4];
                    ctx.fillStyle = block_color;
                    if (feature[5] instanceof Array) {
                        var b1_start = Math.floor( Math.max(0, (feature[5][0] - tile_low) * w_scale) ),
                            b1_end   = Math.ceil( Math.min(width, Math.max(0, (feature[5][1] - tile_low) * w_scale)) ),
                            b2_start = Math.floor( Math.max(0, (feature[6][0] - tile_low) * w_scale) ),
                            b2_end   = Math.ceil( Math.min(width, Math.max(0, (feature[6][1] - tile_low) * w_scale)) );
                        
                        if (feature[5][1] >= tile_low && feature[5][0] <= tile_high) {
                            this.rect_or_text(ctx, w_scale, tile_low, tile_high, feature[5][0], feature[5][2], cigar, y_center);
                        }
                        if (feature[6][1] >= tile_low && feature[6][0] <= tile_high) {
                            this.rect_or_text(ctx, w_scale, tile_low, tile_high, feature[6][0], feature[6][2], cigar, y_center);
                        }
                        if (b2_start > b1_end) {
                            ctx.fillStyle = CONNECTOR_COLOR;
                            ctx.fillRect(b1_end + left_offset, y_center + 5, b2_start - b1_end, 1);
                        }
                    } else {
                        ctx.fillStyle = block_color;
                        this.rect_or_text(ctx, w_scale, tile_low, tile_high, feature_start, feature_name, cigar, y_center);
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
                        ctx.fillStyle = block_color;
                        ctx.fillRect(f_start + left_offset, y_center + 5, f_end - f_start, 1);
                    } else {
                        // Showing labels, blocks, details
                        var feature_strand = feature[4],
                            feature_ts = feature[5],
                            feature_te = feature[6],
                            feature_blocks = feature[7];
                        
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

var ReadTrack = function ( name, view, dataset_id, filters, prefs ) {
    FeatureTrack.call( this, name, view, dataset_id, filters, prefs );
    this.track_type = "ReadTrack";
    this.vertical_detail_px = 10;
    this.vertical_nodetail_px = 5;
    
};
$.extend( ReadTrack.prototype, TiledTrack.prototype, FeatureTrack.prototype, {
});
