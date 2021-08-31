import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import visualization from "viz/visualization";
import viz_views from "viz/viz_views";
import util from "viz/trackster/util";
import slotting from "viz/trackster/slotting";
import painters from "viz/trackster/painters";
import filters_mod from "viz/trackster/filters";
import { Dataset } from "mvc/dataset/data";
import tools_mod from "viz/tools";
import config_mod from "utils/config";
import bbi from "viz/bbi-data-manager";
import "ui/editable-text";

var extend = _.extend;

// ---- Web UI specific utilities ----

/**
 * Dictionary of HTML element-JavaScript object relationships.
 */
// TODO: probably should separate moveable objects from containers.
var html_elt_js_obj_dict = {};

/**
 * Designates an HTML as a container.
 */
function is_container(element, obj) {
    html_elt_js_obj_dict[element.attr("id")] = obj;
}

/**
 * Make `element` moveable within parent and sibling elements by dragging `handle` (a selector).
 * Function manages JS objects, containers as well.
 *
 * @param element HTML element to make moveable
 * @param handle_class classname that denotes HTML element to be used as handle
 * @param container_selector selector used to identify possible containers for this element
 * @param element_js_obj JavaScript object associated with element; used
 */
function moveable(element, handle_class, container_selector, element_js_obj) {
    // HACK: set default value for container selector.
    container_selector = ".group";

    // Register element with its object.
    html_elt_js_obj_dict[element.attr("id")] = element_js_obj;

    // Need to provide selector for handle, not class.
    element
        .bind("drag", { handle: `.${handle_class}`, relative: true }, function (e, d) {
            var element = $(this);
            var parent = element.parent();
            // Only sorting amongst tracks and groups.
            var children = parent.children(".track,.group");
            var this_obj = html_elt_js_obj_dict[$(this).attr("id")];
            var child;
            var container;
            var top;
            var bottom;
            var i;

            //
            // Enable three types of dragging: (a) out of container; (b) into container;
            // (c) sibling movement, aka sorting. Handle in this order for simplicity.
            //

            // Handle dragging out of container.
            container = $(this).parents(container_selector);
            if (container.length !== 0) {
                top = container.position().top;
                bottom = top + container.outerHeight();
                var cur_container = html_elt_js_obj_dict[container.attr("id")];
                if (d.offsetY < top) {
                    // Moving above container.
                    $(this).insertBefore(container);
                    cur_container.remove_drawable(this_obj);
                    cur_container.container.add_drawable_before(this_obj, cur_container);
                    return;
                } else if (d.offsetY > bottom) {
                    // Moving below container.
                    $(this).insertAfter(container);
                    cur_container.remove_drawable(this_obj);
                    cur_container.container.add_drawable(this_obj);
                    return;
                }
            }

            // Handle dragging into container. Child is appended to container's content_div.
            container = null;
            for (i = 0; i < children.length; i++) {
                child = $(children.get(i));
                top = child.position().top;
                bottom = top + child.outerHeight();
                // Dragging into container if child is a container and offset is inside container.
                if (child.is(container_selector) && this !== child.get(0) && d.offsetY >= top && d.offsetY <= bottom) {
                    // Append/prepend based on where offsetY is closest to and return.
                    if (d.offsetY - top < bottom - d.offsetY) {
                        child.find(".content-div").prepend(this);
                    } else {
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
            for (i = 0; i < children.length; i++) {
                child = $(children.get(i));
                if (
                    d.offsetY < child.position().top &&
                    // Cannot move tracks above reference track or intro div.
                    !(child.hasClass("reference-track") || child.hasClass("intro"))
                ) {
                    break;
                }
            }

            // If not already in the right place, move. Need
            // to handle the end specially since we don't have
            // insert at index
            if (i === children.length) {
                if (this !== children.get(i - 1)) {
                    parent.append(this);
                    html_elt_js_obj_dict[parent.attr("id")].move_drawable(this_obj, i);
                }
            } else if (this !== children.get(i)) {
                $(this).insertBefore(children.get(i));
                // Need to adjust insert position if moving down because move is changing
                // indices of all list items.
                html_elt_js_obj_dict[parent.attr("id")].move_drawable(this_obj, d.deltaY > 0 ? i - 1 : i);
            }
        })
        .bind("dragstart", function () {
            $(this).addClass("dragging");
        })
        .bind("dragend", function () {
            $(this).removeClass("dragging");
        });
}

/**
 * Init constants & functions used throughout trackster.
 */

// Padding at the top of tracks for error messages
const ERROR_PADDING = 20;

// Maximum number of rows un a slotted track
const MAX_FEATURE_DEPTH = 100;

// Minimum width for window for squish to be used.
const MIN_SQUISH_VIEW_WIDTH = 12000;

// Number of pixels per tile, not including left offset.
const TILE_SIZE = 400;

const DEFAULT_DATA_QUERY_WAIT = 5000;

// Maximum number of chromosomes that are selectable at any one time.
const MAX_CHROMS_SELECTABLE = 100;

const DATA_ERROR = "Cannot display dataset due to an error. ";

const DATA_NOCONVERTER = "A converter for this dataset is not installed. Please check your datatypes_conf.xml file.";

const DATA_NONE = "No data for this chrom/contig.";

const DATA_PENDING =
    "Preparing data. This can take a while for a large dataset. " +
    "If the visualization is saved and closed, preparation will continue in the background.";

const DATA_CANNOT_RUN_TOOL = "Tool cannot be rerun: ";
//var DATA_LOADING = "Loading data...";
const DATA_OK = "Ready for display";
const TILE_CACHE_SIZE = 10;
//var DATA_CACHE_SIZE = 20;
//
// Numerical/continuous data display modes.
const CONTINUOUS_DATA_MODES = ["Histogram", "Line", "Filled", "Intensity"];

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
 * Check if a server can do byte range requests.
 */
function supportsByteRanges(url) {
    var promise = $.Deferred();
    $.ajax({
        type: "HEAD",
        url: url,
        beforeSend: function (xhr) {
            xhr.setRequestHeader("Range", "bytes=0-10");
        },
        success: function (result, status, xhr) {
            promise.resolve(xhr.status === 206);
        },
    });

    return promise;
}

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
var Drawable = function (view, container, obj_dict) {
    if (!Drawable.id_counter) {
        Drawable.id_counter = 0;
    }
    this.id = Drawable.id_counter++;
    this.view = view;
    this.container = container;
    this.drag_handle_class = obj_dict.drag_handle_class;
    this.is_overview = false;
    this.action_icons = {};

    // -- Set up drawable configuration. --
    this.config = config_mod.ConfigSettingCollection.from_models_and_saved_values(
        this.build_config_params(),
        obj_dict.prefs
    );

    // If there's no saved name, use object name.
    if (!this.config.get_value("name")) {
        this.config.set_value("name", obj_dict.name);
    }
    if (this.config_onchange) {
        this.config.on("change", this.config_onchange, this);
    }

    // Build Drawable HTML and behaviors.
    this.container_div = this.build_container_div();
    this.header_div = null;

    // Use opt-out policy on header creation because this is the more frequent approach:
    // unless flag set, create header.
    if (obj_dict.header !== false) {
        var header_view = new viz_views.TrackHeaderView({
            model: this,
            id: this.id,
        });

        this.header_div = header_view.$el;
        this.container_div.append(this.header_div);

        // Show icons when users is hovering over track.
        var icons_div = header_view.icons_div;
        this.action_icons = header_view.action_icons;
        this.container_div.hover(
            () => {
                icons_div.show();
            },
            () => {
                icons_div.hide();
            }
        );
    }
};

Drawable.prototype.action_icons_def = [
    // Hide/show drawable content.
    // FIXME: make this an odict for easier lookup.
    {
        name: "toggle_icon",
        title: "Hide/show content",
        css_class: "toggle",
        on_click_fn: function (drawable) {
            if (drawable.config.get_value("content_visible")) {
                drawable.action_icons.toggle_icon.addClass("toggle-expand").removeClass("toggle");
                drawable.hide_contents();
                drawable.config.set_value("content_visible", false);
            } else {
                drawable.action_icons.toggle_icon.addClass("toggle").removeClass("toggle-expand");
                drawable.config.set_value("content_visible", true);
                drawable.show_contents();
            }
        },
    },
    // Edit settings.
    {
        name: "settings_icon",
        title: _l("Edit settings"),
        css_class: "gear",
        on_click_fn: function (drawable) {
            var view = new config_mod.ConfigSettingCollectionView({
                collection: drawable.config,
            });
            view.render_in_modal("Configure Track");
        },
    },
    // Remove.
    {
        name: "remove_icon",
        title: _l("Remove"),
        css_class: "remove-icon",
        on_click_fn: function (drawable) {
            // Tooltip for remove icon must be deleted when drawable is deleted.
            $(".tooltip").remove();
            drawable.remove();
        },
    },
];

extend(Drawable.prototype, {
    config_params: [
        { key: "name", label: "Name", type: "text", default_value: "" },
        {
            key: "content_visible",
            type: "bool",
            default_value: true,
            hidden: true,
        },
    ],

    build_config_params: function () {
        return this.config_params;
    },

    config_onchange: function () {},

    init: function () {},

    changed: function () {
        this.view.changed();
    },

    can_draw: function () {
        if (this.enabled && this.config.get_value("content_visible")) {
            return true;
        }

        return false;
    },

    request_draw: function () {},

    _draw: function (options) {},

    /**
     * Returns representation of object in a dictionary for easy saving.
     * Use from_dict to recreate object.
     */
    to_dict: function () {},

    /**
     * Set drawable name.
     */
    set_name: function (new_name) {
        this.old_name = this.config.get_value("name");
        this.config.set_value("name", new_name);
    },

    /**
     * Revert track name; currently name can be reverted only once.
     */
    revert_name: function () {
        if (this.old_name) {
            this.config.set_value("name", this.old_name);
        }
    },

    /**
     * Remove drawable (a) from its container and (b) from the HTML.
     */
    remove: function () {
        this.changed();

        this.container.remove_drawable(this);
        var view = this.view;
        this.container_div.hide(0, function () {
            $(this).remove();
            // HACK: is there a better way to update the view?
            view.update_intro_div();
        });
    },

    /**
     * Build drawable's container div; this is the parent div for all drawable's elements.
     */
    build_container_div: function () {},

    /**
     * Update icons.
     */
    update_icons: function () {},

    /**
     * Hide drawable's contents.
     */
    hide_contents: function () {},

    /**
     * Show drawable's contents.
     */
    show_contents: function () {},

    /**
     * Returns a shallow copy of all drawables in this drawable.
     */
    get_drawables: function () {},
});

/**
 * A collection of drawable objects.
 */
var DrawableCollection = function (view, container, obj_dict) {
    Drawable.call(this, view, container, obj_dict);

    // Attribute init.
    this.obj_type = obj_dict.obj_type;
    this.drawables = [];
};

extend(DrawableCollection.prototype, Drawable.prototype, {
    /**
     * Unpack and add drawables to the collection.
     */
    unpack_drawables: function (drawables_array) {
        // Add drawables to collection.
        this.drawables = [];
        var drawable;
        for (var i = 0; i < drawables_array.length; i++) {
            drawable = object_from_template(drawables_array[i], this.view, this);
            this.add_drawable(drawable);
        }
    },

    /**
     * Init each drawable in the collection.
     */
    init: function () {
        for (var i = 0; i < this.drawables.length; i++) {
            this.drawables[i].init();
        }
    },

    /**
     * Draw each drawable in the collection.
     */
    _draw: function (options) {
        for (var i = 0; i < this.drawables.length; i++) {
            this.drawables[i]._draw(options);
        }
    },

    /**
     * Returns representation of object in a dictionary for easy saving.
     * Use from_dict to recreate object.
     */
    to_dict: function () {
        var dictified_drawables = [];
        for (var i = 0; i < this.drawables.length; i++) {
            dictified_drawables.push(this.drawables[i].to_dict());
        }
        return {
            prefs: this.config.to_key_value_dict(),
            obj_type: this.obj_type,
            drawables: dictified_drawables,
        };
    },

    /**
     * Add a drawable to the end of the collection.
     */
    add_drawable: function (drawable) {
        this.drawables.push(drawable);
        drawable.container = this;
        this.changed();
    },

    /**
     * Add a drawable before another drawable.
     */
    add_drawable_before: function (drawable, other) {
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
    replace_drawable: function (old_drawable, new_drawable, update_html) {
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
    remove_drawable: function (drawable) {
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
    move_drawable: function (drawable, new_position) {
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
    },

    /**
     * Returns all drawables in this drawable.
     */
    get_drawables: function () {
        return this.drawables;
    },

    /**
     * Returns all <track_type> tracks in collection.
     */
    get_tracks: function (track_type) {
        // Initialize queue with copy of drawables array.
        var queue = this.drawables.slice(0);

        var tracks = [];
        var drawable;
        while (queue.length !== 0) {
            drawable = queue.shift();
            if (drawable instanceof track_type) {
                tracks.push(drawable);
            } else if (drawable.drawables) {
                queue = queue.concat(drawable.drawables);
            }
        }
        return tracks;
    },
});

/**
 * A group of drawables that are moveable, visible.
 */
var DrawableGroup = function (view, container, obj_dict) {
    extend(obj_dict, {
        obj_type: "DrawableGroup",
        drag_handle_class: "group-handle",
    });
    DrawableCollection.call(this, view, container, obj_dict);

    // Set up containers/moving for group: register both container_div and content div as container
    // because both are used as containers (container div to recognize container, content_div to
    // store elements). Group can be moved.
    this.content_div = $("<div/>")
        .addClass("content-div")
        .attr("id", `group_${this.id}_content_div`)
        .appendTo(this.container_div);
    is_container(this.container_div, this);
    is_container(this.content_div, this);
    moveable(this.container_div, this.drag_handle_class, ".group", this);

    // Set up filters.
    this.filters_manager = new filters_mod.FiltersManager(this);
    this.header_div.after(this.filters_manager.parent_div);

    // HACK: add div to clear floating elements.
    this.filters_manager.parent_div.after($("<div style='clear: both'/>"));

    // For saving drawables' filter managers when group-level filtering is done:
    this.saved_filters_managers = [];

    // Add drawables.
    if ("drawables" in obj_dict) {
        this.unpack_drawables(obj_dict.drawables);
    }

    // Restore filters.
    if ("filters" in obj_dict) {
        // FIXME: Pass collection_dict to DrawableCollection/Drawable will make this easier.
        var old_manager = this.filters_manager;
        this.filters_manager = new filters_mod.FiltersManager(this, obj_dict.filters);
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
            title: _l("Show composite track"),
            css_class: "layers-stack",
            on_click_fn: function (group) {
                $(".tooltip").remove();
                group.show_composite_track();
            },
        },
        // Toggle track filters.
        {
            name: "filters_icon",
            title: _l("Filters"),
            css_class: "ui-slider-050",
            on_click_fn: function (group) {
                // TODO: update Tooltip text.
                if (group.filters_manager.visible()) {
                    // Hiding filters.
                    group.filters_manager.clear_filters();
                    group._restore_filter_managers();
                    // TODO: maintain current filter by restoring and setting saved manager's
                    // settings to current/shared manager's settings.
                    // TODO: need to restore filter managers when moving drawable outside group.
                } else {
                    // Showing filters.
                    group.setup_multitrack_filtering();
                    group.request_draw({ clear_tile_cache: true });
                }
                group.filters_manager.toggle();
            },
        },
        Drawable.prototype.action_icons_def[2],
    ],

    build_container_div: function () {
        var container_div = $("<div/>").addClass("group").attr("id", `group_${this.id}`);
        if (this.container) {
            this.container.content_div.append(container_div);
        }
        return container_div;
    },

    hide_contents: function () {
        this.tiles_div.hide();
    },

    show_contents: function () {
        // Show the contents div and labels (if present)
        this.tiles_div.show();
        // Request a redraw of the content
        this.request_draw();
    },

    update_icons: function () {
        //
        // Handle update when there are no tracks.
        //
        var num_drawables = this.drawables.length;
        if (num_drawables === 0) {
            this.action_icons.composite_icon.hide();
            this.action_icons.filters_icon.hide();
        } else if (num_drawables === 1) {
            this.action_icons.composite_icon.toggle(this.drawables[0] instanceof CompositeTrack);
            this.action_icons.filters_icon.hide();
        } else {
            // There are 2 or more tracks.

            //
            // Determine if a composite track can be created. Current criteria:
            // (a) all tracks are line tracks;
            //      OR
            // FIXME: this is not enabled right now because it has not been well tested:
            // (b) there is a single FeatureTrack.
            //

            // All tracks the same?
            var i;

            var j;
            var drawable;
            var same_type = true;
            var a_type = this.drawables[0].get_type();
            var num_feature_tracks = 0;
            for (i = 0; i < num_drawables; i++) {
                drawable = this.drawables[i];
                if (drawable.get_type() !== a_type) {
                    break;
                }
                if (drawable instanceof FeatureTrack) {
                    num_feature_tracks++;
                }
            }

            if (same_type && this.drawables[0] instanceof LineTrack) {
                this.action_icons.composite_icon.show();
            } else {
                this.action_icons.composite_icon.hide();
                $(".tooltip").remove();
            }

            //
            // Set up group-level filtering and update filter icon.
            //
            if (num_feature_tracks > 1 && num_feature_tracks === this.drawables.length) {
                //
                // Find shared filters.
                //
                var shared_filters = {};

                var filter;

                // Init shared filters with filters from first drawable.
                drawable = this.drawables[0];
                for (j = 0; j < drawable.filters_manager.filters.length; j++) {
                    filter = drawable.filters_manager.filters[j];
                    shared_filters[filter.name] = [filter];
                }

                // Create lists of shared filters.
                for (i = 1; i < this.drawables.length; i++) {
                    drawable = this.drawables[i];
                    for (j = 0; j < drawable.filters_manager.filters.length; j++) {
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
                for (var filter_name in shared_filters) {
                    const filters = shared_filters[filter_name];
                    if (filters.length === num_feature_tracks) {
                        // Add new filter.
                        // FIXME: can filter.copy() be used?
                        const new_filter = new filters_mod.NumberFilter({
                            name: filters[0].name,
                            index: filters[0].index,
                        });
                        this.filters_manager.add_filter(new_filter);
                    }
                }

                // Show/hide icon based on filter availability.
                this.action_icons.filters_icon.toggle(this.filters_manager.filters.length > 0);
            } else {
                this.action_icons.filters_icon.hide();
            }
        }
    },

    /**
     * Restore individual track filter managers.
     */
    _restore_filter_managers: function () {
        for (var i = 0; i < this.drawables.length; i++) {
            this.drawables[i].filters_manager = this.saved_filters_managers[i];
        }
        this.saved_filters_managers = [];
    },

    /**
     *
     */
    setup_multitrack_filtering: function () {
        // Save tracks' managers and set up shared manager.
        if (this.filters_manager.filters.length > 0) {
            // For all tracks, save current filter manager and set manager to shared (this object's) manager.
            this.saved_filters_managers = [];
            for (var i = 0; i < this.drawables.length; i++) {
                var drawable = this.drawables[i];
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
    show_composite_track: function () {
        var composite_track = new CompositeTrack(this.view, this.view, {
            name: this.config.get_value("name"),
            drawables: this.drawables,
        });
        this.container.replace_drawable(this, composite_track, true);
        composite_track.request_draw();
    },

    add_drawable: function (drawable) {
        DrawableCollection.prototype.add_drawable.call(this, drawable);
        this.update_icons();
    },

    remove_drawable: function (drawable) {
        DrawableCollection.prototype.remove_drawable.call(this, drawable);
        this.update_icons();
    },

    to_dict: function () {
        // If filters are visible, need to restore original filter managers before converting to dict.
        if (this.filters_manager.visible()) {
            this._restore_filter_managers();
        }

        var obj_dict = extend(DrawableCollection.prototype.to_dict.call(this), {
            filters: this.filters_manager.to_dict(),
        });

        // Setup multi-track filtering again.
        if (this.filters_manager.visible()) {
            this.setup_multitrack_filtering();
        }

        return obj_dict;
    },

    request_draw: function (options) {
        _.each(this.drawables, (d) => {
            d.request_draw(options);
        });
    },
});

/**
 * View object manages a trackster visualization, including tracks and user interactions.
 * Events triggered:
 *      navigate: when browser view changes to a new locations
 */
var TracksterView = Backbone.View.extend({
    initialize: function (obj_dict) {
        extend(obj_dict, {
            obj_type: "View",
        });
        DrawableCollection.call(this, "View", obj_dict.container, obj_dict);
        this.chrom = null;
        this.vis_id = obj_dict.vis_id;
        this.dbkey = obj_dict.dbkey;
        this.stand_alone = obj_dict.stand_alone !== undefined ? obj_dict.stand_alone : true;
        this.label_tracks = [];
        this.tracks_to_be_redrawn = [];
        this.max_low = 0;
        this.max_high = 0;
        this.zoom_factor = 3;
        this.min_separation = 30;
        this.has_changes = false;
        // Deferred object that indicates when view's chrom data has been loaded.
        this.load_chroms_deferred = null;
        this.render();
        this.canvas_manager = new visualization.CanvasManager(this.container.get(0).ownerDocument);
        this.reset();

        // Define track configuration
        this.config = config_mod.ConfigSettingCollection.from_models_and_saved_values(
            [
                {
                    key: "name",
                    label: "Name",
                    type: "text",
                    default_value: "",
                },
                {
                    key: "a_color",
                    label: "A Color",
                    type: "color",
                    default_value: "#FF0000",
                },
                {
                    key: "c_color",
                    label: "C Color",
                    type: "color",
                    default_value: "#00FF00",
                },
                {
                    key: "g_color",
                    label: "G Color",
                    type: "color",
                    default_value: "#0000FF",
                },
                {
                    key: "t_color",
                    label: "T Color",
                    type: "color",
                    default_value: "#FF00FF",
                },
                {
                    key: "n_color",
                    label: "N Color",
                    type: "color",
                    default_value: "#AAAAAA",
                },
            ],
            { name: obj_dict.name }
        );
    },

    render: function () {
        // Attribute init.
        this.requested_redraw = false;

        // Create DOM elements
        var parent_element = this.container;

        var view = this;
        // Top container for things that are fixed at the top
        this.top_container = $("<div/>").addClass("top-container").appendTo(parent_element);
        // Browser content, primary tracks are contained in here
        this.browser_content_div = $("<div/>").addClass("content").appendTo(parent_element);
        // Bottom container for things that are fixed at the bottom
        this.bottom_container = $("<div/>").addClass("bottom-container").appendTo(parent_element);
        // Label track fixed at top
        this.top_labeltrack = $("<div/>").addClass("top-labeltrack").appendTo(this.top_container);
        // Viewport for dragging tracks in center
        this.viewport_container = $("<div/>")
            .addClass("viewport-container")
            .attr("id", "viewport-container")
            .appendTo(this.browser_content_div);
        // Alias viewport_container as content_div so that it matches function of DrawableCollection/Group content_div.
        this.content_div = this.viewport_container;
        is_container(this.viewport_container, view);
        // Introduction div shown when there are no tracks.
        this.intro_div = $("<div/>").addClass("intro").appendTo(this.viewport_container);
        // Add tracks button
        $("<div/>")
            .text("Add Datasets to Visualization")
            .addClass("action-button")
            .appendTo(this.intro_div)
            .click(() => {
                visualization.select_datasets({ dbkey: view.dbkey }, (tracks) => {
                    _.each(tracks, (track) => {
                        view.add_drawable(object_from_template(track, view, view));
                    });
                });
            });

        // We break out of the parent container with nav (and potentially other
        // things?) so we need to override any overflow settings here.
        parent_element.attr("style", "overflow: visible !important");
        // Navigation at top
        this.nav_container = $("<div/>").addClass("trackster-nav-container").prependTo(this.top_container);
        this.nav = $("<div/>").addClass("trackster-nav").appendTo(this.nav_container);

        if (this.stand_alone) {
            this.nav_container.addClass("stand-alone");
            this.nav.addClass("stand-alone");
        }

        // Overview (scrollbar and overview plot) at bottom
        this.overview = $("<div/>").addClass("overview").appendTo(this.bottom_container);
        this.overview_viewport = $("<div/>").addClass("overview-viewport").appendTo(this.overview);
        this.overview_close = $("<a/>")
            .attr("title", "Close overview")
            .addClass("icon-button overview-close tooltip")
            .hide()
            .appendTo(this.overview_viewport);
        this.overview_highlight = $("<div/>").addClass("overview-highlight").hide().appendTo(this.overview_viewport);
        this.overview_box_background = $("<div/>").addClass("overview-boxback").appendTo(this.overview_viewport);
        this.overview_box = $("<div/>").addClass("overview-box").appendTo(this.overview_viewport);
        this.default_overview_height = this.overview_box.height();

        this.nav_controls = $("<div/>").addClass("nav-controls").appendTo(this.nav);
        this.chrom_select = $("<select/>")
            .attr({ name: "chrom" })
            .addClass("chrom-nav")
            .append("<option value=''>Loading</option>")
            .appendTo(this.nav_controls);
        var submit_nav = function (e) {
            if (e.type === "focusout" || (e.keyCode || e.which) === 13 || (e.keyCode || e.which) === 27) {
                if ((e.keyCode || e.which) !== 27) {
                    // Not escape key
                    view.go_to($(this).val());
                }
                $(this).hide();
                $(this).val("");
                view.location_span.show();
                view.chrom_select.show();
            }

            // Suppress key presses so that they do impact viz.
            e.stopPropagation();
        };
        this.nav_input = $("<input/>")
            .addClass("nav-input")
            .hide()
            .bind("keyup focusout", submit_nav)
            .appendTo(this.nav_controls);
        this.location_span = $("<span/>")
            .addClass("location")
            .attr("title", "Click to change location")
            .tooltip({ placement: "bottom" })
            .appendTo(this.nav_controls);
        this.location_span.click(() => {
            view.location_span.hide();
            view.chrom_select.hide();
            view.nav_input.val(`${view.chrom}:${view.low}-${view.high}`);
            view.nav_input.css("display", "inline-block");
            view.nav_input.select();
            view.nav_input.focus();
            // Set up autocomplete for tracks' features.
            view.nav_input.autocomplete({
                source: function (request, response) {
                    // Using current text, query each track and create list of all matching features.
                    var all_features = [];

                    var feature_search_deferreds = $.map(view.get_tracks(FeatureTrack), (t) =>
                        t.data_manager.search_features(request.term).success((dataset_features) => {
                            all_features = all_features.concat(dataset_features);
                        })
                    );

                    // When all searching is done, fill autocomplete.
                    $.when.apply($, feature_search_deferreds).done(() => {
                        response(
                            $.map(all_features, (feature) => ({
                                label: feature[0],
                                value: feature[1],
                            }))
                        );
                    });
                },
                minLength: 2,
            });
        });
        if (this.vis_id !== undefined) {
            this.hidden_input = $("<input/>").attr("type", "hidden").val(this.vis_id).appendTo(this.nav_controls);
        }

        this.zo_link = $("<a/>")
            .attr("id", "zoom-out")
            .attr("title", "Zoom out")
            .tooltip({ placement: "bottom" })
            .click(() => {
                view.zoom_out();
            })
            .appendTo(this.nav_controls);
        this.zi_link = $("<a/>")
            .attr("id", "zoom-in")
            .attr("title", "Zoom in")
            .tooltip({ placement: "bottom" })
            .click(() => {
                view.zoom_in();
            })
            .appendTo(this.nav_controls);

        // Get initial set of chroms.
        this.load_chroms_deferred = this.load_chroms({ low: 0 });
        this.chrom_select.bind("change", () => {
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
        this.browser_content_div.click(function (e) {
            $(this).find("input").trigger("blur");
        });

        // Double clicking zooms in
        this.browser_content_div.bind("dblclick", function (e) {
            view.zoom_in(e.pageX, this.viewport_container);
        });

        // Dragging the overview box (~ horizontal scroll bar)
        this.overview_box
            .bind("dragstart", function (e, d) {
                this.current_x = d.offsetX;
            })
            .bind("drag", function (e, d) {
                var delta = d.offsetX - this.current_x;
                this.current_x = d.offsetX;
                var delta_chrom = Math.round(
                    (delta / view.viewport_container.width()) * (view.max_high - view.max_low)
                );
                view.move_delta(-delta_chrom);
            });

        this.overview_close.click(() => {
            view.reset_overview();
        });

        // Dragging in the viewport scrolls
        this.viewport_container
            .bind("draginit", (e, d) => {
                // Disable interaction if started in scrollbar (for webkit)
                if (e.clientX > view.viewport_container.width() - 16) {
                    return false;
                }
            })
            .bind("dragstart", (e, d) => {
                d.original_low = view.low;
                d.current_height = e.clientY;
                d.current_x = d.offsetX;
            })
            .bind("drag", function (e, d) {
                var container = $(this);
                var delta = d.offsetX - d.current_x;
                var new_scroll = container.scrollTop() - (e.clientY - d.current_height);
                container.scrollTop(new_scroll);
                d.current_height = e.clientY;
                d.current_x = d.offsetX;
                var delta_chrom = Math.round((delta / view.viewport_container.width()) * (view.high - view.low));
                view.move_delta(delta_chrom);
            });
        /*
        FIXME: Do not do this for now because it's too jittery. Some kind of gravity approach is
        needed here because moving left/right should be difficult.

        // Also capture mouse wheel for left/right scrolling
        }).bind( 'mousewheel', function( e, d, dx, dy ) {
            // Only handle x axis scrolling; y axis scrolling is
            // handled by the browser when the event bubbles up.
            if (dx) {
                var delta_chrom = Math.round( - dx / view.viewport_container.width() * (view.high - view.low) );
                view.move_delta( delta_chrom );
            }
        });
        */

        // Dragging in the top label track allows selecting a region to zoom in on selected region.
        this.top_labeltrack
            .bind("dragstart", function (e, d) {
                return $("<div/>")
                    .addClass("zoom-area")
                    .css("height", view.browser_content_div.height() + view.top_labeltrack.height() + 1)
                    .appendTo($(this));
            })
            .bind("drag", (e, d) => {
                $(d.proxy).css({
                    left: Math.min(e.pageX, d.startX) - view.container.offset().left,
                    width: Math.abs(e.pageX - d.startX),
                });

                var min = Math.min(e.pageX, d.startX) - view.container.offset().left;

                var max = Math.max(e.pageX, d.startX) - view.container.offset().left;

                var span = view.high - view.low;
                var width = view.viewport_container.width();
                view.update_location(
                    Math.round((min / width) * span) + view.low,
                    Math.round((max / width) * span) + view.low
                );
            })
            .bind("dragend", (e, d) => {
                var min = Math.min(e.pageX, d.startX);
                var max = Math.max(e.pageX, d.startX);
                var span = view.high - view.low;
                var width = view.viewport_container.width();
                var old_low = view.low;
                view.low = Math.round((min / width) * span) + old_low;
                view.high = Math.round((max / width) * span) + old_low;
                $(d.proxy).remove();
                view.request_redraw();
            });

        // FIXME: this is still wonky for embedded visualizations.
        /*
        // For vertical alignment, track mouse with simple line.
        var mouse_tracker_div = $('<div/>').addClass('mouse-pos').appendTo(parent_element);

        // Show tracker only when hovering over view.
        parent_element.hover(
            function() {
                mouse_tracker_div.show();
                parent_element.mousemove(function(e) {
                    mouse_tracker_div.css({
                        // -1 makes line appear next to the mouse w/o preventing mouse actions.
                        left: e.pageX - parent_element.offset().left - 1
                    });
                });
            },
            function() {
                parent_element.off('mousemove');
                mouse_tracker_div.hide();
            }
        );
        */

        this.add_label_track(new LabelTrack(this, { content_div: this.top_labeltrack }));

        $(window).bind("resize", function () {
            // Stop previous timer.
            if (this.resize_timer) {
                window.clearTimeout(this.resize_timer);
            }

            // When function activated, resize window and redraw.
            this.resize_timer = window.setTimeout(() => {
                view.resize_window();
            }, 500);
        });
        $(document).bind("redraw", () => {
            view.redraw();
        });

        this.reset();
        $(window).trigger("resize");
    },

    get_base_color: function (base) {
        return this.config.get_value(`${base.toLowerCase()}_color`) || this.config.get_value("n_color");
    },
});

// FIXME: need to use this approach to enable inheritance of DrawableCollection functions.
extend(TracksterView.prototype, DrawableCollection.prototype, {
    changed: function () {
        this.has_changes = true;
    },

    /** Add or remove intro div depending on view state. */
    update_intro_div: function () {
        this.intro_div.toggle(this.drawables.length === 0);
    },

    /**
     * Triggers navigate events as needed. If there is a delay,
     * then event is triggered only after navigation has stopped.
     */
    trigger_navigate: function (new_chrom, new_low, new_high, delay) {
        // Stop previous timer.
        if (this.timer) {
            window.clearTimeout(this.timer);
        }

        if (delay) {
            // To aggregate calls, use timer and only navigate once
            // location has stabilized.
            this.timer = window.setTimeout(() => {
                this.trigger("navigate", `${new_chrom}:${new_low}-${new_high}`);
            }, 500);
        } else {
            this.trigger("navigate", `${new_chrom}:${new_low}-${new_high}`);
        }
    },

    update_location: function (low, high) {
        this.location_span.text(`${util.commatize(low)} - ${util.commatize(high)}`);
        this.nav_input.val(`${this.chrom}:${util.commatize(low)}-${util.commatize(high)}`);

        // Update location. Only update when there is a valid chrom; when loading vis, there may
        // not be a valid chrom.
        var chrom = this.chrom_select.val();
        if (chrom !== "") {
            this.trigger_navigate(chrom, this.low, this.high, true);
        }
    },

    /**
     * Load chrom data for the view. Returns a jQuery Deferred.
     */
    // FIXME: instead of loading chrom data, should load and store genome object.
    load_chroms: function (url_parms) {
        url_parms.num = MAX_CHROMS_SELECTABLE;

        var chrom_data = $.Deferred();
        $.ajax({
            url: `${getAppRoot()}api/genomes/${this.dbkey}`,
            data: url_parms,
            dataType: "json",
            success: (result) => {
                // Do nothing if could not load chroms.
                if (result.chrom_info.length === 0) {
                    return;
                }

                // Load chroms.
                if (result.reference) {
                    var ref_track = new ReferenceTrack(this);
                    this.add_label_track(ref_track);
                    this.reference_track = ref_track;
                }
                this.chrom_data = result.chrom_info;

                this.chrom_select.html("");
                this.chrom_select.append($('<option value="">Select Chrom/Contig</option>'));

                for (var i = 0, len = this.chrom_data.length; i < len; i++) {
                    var chrom = this.chrom_data[i].chrom;
                    var chrom_option = $("<option>");
                    chrom_option.text(chrom);
                    chrom_option.val(chrom);
                    this.chrom_select.append(chrom_option);
                }
                if (result.prev_chroms) {
                    this.chrom_select.append($(`<option value="previous">Previous ${MAX_CHROMS_SELECTABLE}</option>`));
                }
                if (result.next_chroms) {
                    this.chrom_select.append($(`<option value="next">Next ${MAX_CHROMS_SELECTABLE}</option>`));
                }
                this.chrom_start_index = result.start_index;

                chrom_data.resolve(result.chrom_info);
            },
            error: function () {
                alert(`Could not load chroms for this dbkey: ${this.dbkey}`);
            },
        });
        return chrom_data;
    },

    change_chrom: function (chrom, low, high) {
        var view = this;
        // If chrom data is still loading, wait for it.
        if (!view.chrom_data) {
            view.load_chroms_deferred.then(() => {
                view.change_chrom(chrom, low, high);
            });
            return;
        }

        // Don't do anything if chrom is "None" (hackish but some browsers already have this set), or null/blank
        if (!chrom || chrom === "None") {
            return;
        }

        //
        // If user is navigating to previous/next set of chroms, load new chrom set and return.
        //
        if (chrom === "previous") {
            view.load_chroms({
                low: this.chrom_start_index - MAX_CHROMS_SELECTABLE,
            });
            return;
        }
        if (chrom === "next") {
            view.load_chroms({
                low: this.chrom_start_index + MAX_CHROMS_SELECTABLE,
            });
            return;
        }

        //
        // User is loading a particular chrom. Look first in current set; if not in current set, load new
        // chrom set.
        //
        var found = $.grep(view.chrom_data, (v, i) => v.chrom === chrom)[0];
        if (found === undefined) {
            // Try to load chrom and then change to chrom.
            view.load_chroms({ chrom: chrom }, () => {
                view.change_chrom(chrom, low, high);
            });
            return;
        } else {
            // Switching to local chrom.
            if (chrom !== view.chrom) {
                view.chrom = chrom;
                view.chrom_select.val(view.chrom);
                view.max_high = found.len - 1; // -1 because we're using 0-based indexing.
                view.reset();

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

            // Resolve low, high.
            if (low === undefined && high === undefined) {
                // Both are undefined, so view is whole chromosome.
                view.low = 0;
                view.high = view.max_high;
            } else {
                // Low and/or high is defined.
                view.low = low !== undefined ? Math.max(low, 0) : 0;
                if (high === undefined) {
                    // Center visualization around low.
                    // HACK: max resolution is currently 30 bases.
                    view.low = Math.max(view.low - 15, 0);
                    view.high = view.low + 30;
                } else {
                    // High is defined.
                    view.high = Math.min(high, view.max_high);
                }
            }

            view.request_redraw();
        }
    },

    /**
     * Change viewing region to that denoted by string. General format of string is:
     *
     * <chrom>[ {separator}<start>[-<end>] ]
     *
     * where separator can be whitespace or a colon. Examples:
     *
     * chr22
     * chr1:100-200
     * chr7 89999
     * chr8 90000 990000
     */
    go_to: function (str) {
        // Remove commas.
        str = str.replace(/,/g, "");

        // Replace colons and hyphens with space for easy parsing.
        str = str.replace(/:|-/g, " ");

        // Parse new location.
        var chrom_pos = str.split(/\s+/);

        var chrom = chrom_pos[0];
        var new_low = chrom_pos[1] ? parseInt(chrom_pos[1], 10) : undefined;
        var new_high = chrom_pos[2] ? parseInt(chrom_pos[2], 10) : undefined;

        this.change_chrom(chrom, new_low, new_high);
    },

    move_fraction: function (fraction) {
        var view = this;
        var span = view.high - view.low;
        this.move_delta(fraction * span);
    },

    move_delta: function (delta_chrom) {
        //
        // Update low, high.
        //

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

        //
        // Redraw view.
        //

        // Redraw without requesting more data immediately.
        view.request_redraw({ data_fetch: false });

        // Set up timeout to redraw with more data when moving stops.
        if (this.redraw_on_move_fn) {
            window.clearTimeout(this.redraw_on_move_fn);
        }

        this.redraw_on_move_fn = window.setTimeout(() => {
            view.request_redraw();
        }, 200);

        // Navigate.
        var chrom = view.chrom_select.val();
        this.trigger_navigate(chrom, view.low, view.high, true);
    },

    /**
     * Add a drawable to the view.
     */
    add_drawable: function (drawable) {
        DrawableCollection.prototype.add_drawable.call(this, drawable);
        drawable.init();
        this.changed();
        this.update_intro_div();

        // When drawable config changes, mark view as changed. This
        // captures most (all?) state change that needs to be saved.
        var self = this;
        drawable.config.on("change", () => {
            self.changed();
        });
    },

    add_label_track: function (label_track) {
        label_track.view = this;
        label_track.init();
        this.label_tracks.push(label_track);
    },

    /**
     * Remove drawable from the view.
     */
    remove_drawable: function (drawable, hide) {
        DrawableCollection.prototype.remove_drawable.call(this, drawable);
        if (hide) {
            var view = this;
            drawable.container_div.hide(0, function () {
                $(this).remove();
                view.update_intro_div();
            });
        }
    },

    reset: function () {
        this.low = this.max_low;
        this.high = this.max_high;
        this.viewport_container.find(".yaxislabel").remove();
    },

    /**
     * Request that view redraw one or more of view's drawables. If drawable is not specified,
     * all drawables are redrawn.
     */
    request_redraw: function (options, drawable) {
        var view = this;

        var // Either redrawing a single drawable or all view's drawables.
            track_list = drawable ? [drawable] : view.drawables;

        // Add/update tracks in track list to redraw list.
        _.each(track_list, (track) => {
            var track_options = _.find(view.tracks_to_be_redrawn, (to) => to[0] === track);

            if (track_options) {
                // Track already in list; update options.
                track_options[1] = options;
            } else {
                // Track not in list yet.
                view.tracks_to_be_redrawn.push([track, options]);
            }
        });

        // Set up redraw if it has not been requested since last redraw.
        if (!this.requested_redraw) {
            window.requestAnimationFrame(() => {
                view._redraw();
            });
            this.requested_redraw = true;
        }
    },

    /**
     * Redraws view and tracks.
     * NOTE: this method should never be called directly; request_redraw() should be used so
     * that requestAnimationFrame can manage redrawing.
     */
    _redraw: function () {
        // TODO: move this code to function that does location setting.

        // Clear because requested redraw is being handled now.
        this.requested_redraw = false;

        var low = this.low;
        var high = this.high;

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

        // Resolution is a pixel density.
        this.resolution_px_b = this.viewport_container.width() / (this.high - this.low);

        // Overview
        var left_px = (this.low / (this.max_high - this.max_low)) * this.overview_viewport.width() || 0;
        var width_px = ((this.high - this.low) / (this.max_high - this.max_low)) * this.overview_viewport.width() || 0;
        var min_width_px = 13;

        this.overview_box
            .css({
                left: left_px,
                width: Math.max(min_width_px, width_px),
            })
            .show();
        if (width_px < min_width_px) {
            this.overview_box.css("left", left_px - (min_width_px - width_px) / 2);
        }
        if (this.overview_highlight) {
            this.overview_highlight.css({
                left: left_px,
                width: width_px,
            });
        }

        // Draw data tracks.
        _.each(this.tracks_to_be_redrawn, (track_options) => {
            var track = track_options[0];
            var options = track_options[1];
            if (track) {
                track._draw(options);
            }
        });
        this.tracks_to_be_redrawn = [];

        // Draw label tracks.
        _.each(this.label_tracks, (label_track) => {
            label_track._draw();
        });
    },

    zoom_in: function (point, container) {
        if (this.max_high === 0 || this.high - this.low <= this.min_separation) {
            return;
        }
        var span = this.high - this.low;
        var cur_center = span / 2 + this.low;
        var new_half = span / this.zoom_factor / 2;
        if (point) {
            cur_center = (point / this.viewport_container.width()) * (this.high - this.low) + this.low;
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
        var span = this.high - this.low;
        var cur_center = span / 2 + this.low;
        var new_half = (span * this.zoom_factor) / 2;
        this.low = Math.round(cur_center - new_half);
        this.high = Math.round(cur_center + new_half);
        this.changed();
        this.request_redraw();
    },

    /** Resize viewport. Use this method if header/footer content has changed in size. */
    resize_viewport: function () {
        this.viewport_container.height(
            this.container.height() - this.top_container.height() - this.bottom_container.height()
        );
    },

    /** Called when window is resized. */
    resize_window: function () {
        this.resize_viewport();
        this.request_redraw();
    },

    /** Show a Drawable in the overview. */
    set_overview: function (drawable) {
        if (this.overview_drawable) {
            // If drawable to be set as overview is already in overview, do nothing.
            // Otherwise, remove overview.
            if (this.overview_drawable.dataset.id === drawable.dataset.id) {
                return;
            }
            this.overview_viewport.find(".track").remove();
        }

        // Set new overview.
        var overview_drawable = drawable.copy({
            content_div: this.overview_viewport,
        });

        var view = this;
        overview_drawable.header_div.hide();
        overview_drawable.is_overview = true;
        view.overview_drawable = overview_drawable;
        this.overview_drawable.postdraw_actions = () => {
            view.overview_highlight.show().height(view.overview_drawable.content_div.height());
            view.overview_viewport.height(
                view.overview_drawable.content_div.height() + view.overview_box.outerHeight()
            );
            view.overview_close.show();
            view.resize_window();
        };
        view.overview_drawable.request_draw();
        this.changed();
    },

    /** Close and reset overview. */
    reset_overview: function () {
        // Update UI.
        $(".tooltip").remove();
        this.overview_viewport.find(".track-tile").remove();
        this.overview_viewport.height(this.default_overview_height);
        this.overview_box.height(this.default_overview_height);
        this.overview_close.hide();
        this.overview_highlight.hide();
        this.resize_window();
        this.overview_drawable = null;
    },
});

/**
 * Encapsulation of a tool that users can apply to tracks/datasets.
 */
var TracksterTool = tools_mod.Tool.extend({
    defaults: {
        track: null,
    },

    initialize: function (options) {
        tools_mod.Tool.prototype.initialize.call(this, options);

        // Restore tool visibility from state; default to hidden.
        var hidden = true;
        if (options.tool_state !== undefined && options.tool_state.hidden !== undefined) {
            hidden = options.tool_state.hidden;
        }
        this.set("hidden", hidden);

        // FIXME: need to restore tool values from options.tool_state

        // HACK: remove some inputs because Trackster does yet not work with them.
        this.remove_inputs(["data", "hidden_data", "conditional"]);
    },

    state_dict: function (options) {
        return _.extend(this.get_inputs_dict(), {
            hidden: !this.is_visible(),
        });
    },
});

/**
 * View renders tool parameter HTML and updates parameter value as it is changed in the HTML.
 */
var ToolParameterView = Backbone.View.extend({
    events: {
        "change :input": "update_value",
    },

    render: function () {
        var param_div = this.$el.addClass("param-row");
        var param = this.model;

        // Param label.
        $("<div>").addClass("param-label").text(param.get("label")).appendTo(param_div);
        // Param HTML.
        var html_div = $("<div/>").addClass("param-input").html(param.get("html")).appendTo(param_div);
        // Set initial value.
        html_div.find(":input").val(param.get("value"));

        // Add to clear floating layout.
        $("<div style='clear: both;'/>").appendTo(param_div);
    },

    update_value: function (update_event) {
        this.model.set_value($(update_event.target).val());
    },
});

/**
 * View for TracksterTool.
 */
var TracksterToolView = Backbone.View.extend({
    initialize: function (options) {
        this.model.on("change:hidden", this.set_visible, this);
    },

    /**
     * Render tool UI.
     */
    render: function () {
        var self = this;
        var tool = this.model;
        var parent_div = this.$el.addClass("dynamic-tool").hide();

        // Prevent div events from propogating to other elements.
        parent_div
            .bind("drag", (e) => {
                e.stopPropagation();
            })
            .click((e) => {
                e.stopPropagation();
            })
            .bind("dblclick", (e) => {
                e.stopPropagation();
            })
            .keydown((e) => {
                e.stopPropagation();
            });

        // Add name, inputs.
        $("<div class='tool-name'>").appendTo(parent_div).text(tool.get("name"));
        tool.get("inputs").each((param) => {
            // Render parameter.
            var param_view = new ToolParameterView({ model: param });
            param_view.render();
            parent_div.append(param_view.$el);
        });

        // Highlight value for inputs for easy replacement.
        parent_div.find("input").click(function () {
            $(this).select();
        });

        // Add buttons for running on dataset, region.
        var run_tool_row = $("<div>").addClass("param-row").appendTo(parent_div);
        var run_on_dataset_button = $("<input type='submit'>")
            .attr("value", "Run on complete dataset")
            .appendTo(run_tool_row);
        var run_on_region_button = $("<input type='submit'>")
            .attr("value", "Run on visible region")
            .appendTo(run_tool_row);
        run_on_region_button.click(() => {
            // Run tool to create new track.
            self.run_on_region();
        });
        run_on_dataset_button.click(() => {
            self.run_on_dataset();
        });

        if (tool.is_visible()) {
            this.$el.show();
        }
    },

    /**
     * Show or hide tool depending on tool visibility state.
     */
    set_visible: function () {
        this.$el.toggle(this.model.is_visible());
    },

    /**
     * Update tool parameters.
     */
    update_params: function () {
        for (var i = 0; i < this.params.length; i++) {
            this.params[i].update_value();
        }
    },

    /**
     * Run tool on dataset. Output is placed in dataset's history and no changes to viz are made.
     */
    run_on_dataset: function () {
        var tool = this.model;
        const Galaxy = getGalaxyInstance();
        this.run(
            // URL params.
            {
                target_dataset_id: this.model.get("track").dataset.id,
                action: "rerun",
                tool_id: tool.id,
            },
            null,
            (track_data) => {
                Galaxy.modal.show({
                    title: `${tool.get("name")} is Running`,
                    body: `${tool.get(
                        "name"
                    )} is running on the complete dataset. Tool outputs are in dataset's history.`,
                    buttons: {
                        Close: function () {
                            Galaxy.modal.hide();
                        },
                    },
                });
            }
        );
    },

    /**
     * Run dataset on visible region. This creates a new track and sets the track's contents
     * to the tool's output.
     */
    run_on_region: function () {
        //
        // Create track for tool's output immediately to provide user feedback.
        //
        var track = this.model.get("track");

        var tool = this.model;

        var region = new visualization.GenomeRegion({
            chrom: track.view.chrom,
            start: track.view.low,
            end: track.view.high,
        });

        var url_params = {
            target_dataset_id: track.dataset.id,
            action: "rerun",
            tool_id: tool.id,
            regions: [region.toJSON()],
        };

        // Set name of track to include tool name, parameters, and region used.
        var track_name = tool.get("name") + track.tool_region_and_parameters_str(region);

        var container;

        // If track not in a group, create a group for it and add new track to group. If track
        // already in group, add track to group.
        if (track.container === track.view) {
            // Create new group.
            var group = new DrawableGroup(track.view, track.view, {
                name: track.config.get_value("name"),
            });

            // Replace track with group.
            var index = track.container.replace_drawable(track, group, false);

            // Update HTML.
            // FIXME: this is ugly way to replace a track with a group -- make this easier via
            // a Drawable or DrawableCollection function.
            group.container_div.insertBefore(track.view.content_div.children()[index]);
            group.add_drawable(track);
            track.container_div.appendTo(group.content_div);
            container = group;
        } else {
            // Use current group.
            container = track.container;
        }

        // Create and init new track.
        var new_track = new track.constructor(track.view, container, {
            name: track_name,
            hda_ldda: "hda",
        });
        new_track.init_for_tool_data();
        new_track.change_mode(track.mode);
        new_track.set_filters_manager(track.filters_manager.copy(new_track));
        new_track.update_icons();
        container.add_drawable(new_track);
        new_track.tiles_div.text("Starting job.");

        // Run tool.
        this.run(url_params, new_track, (track_data) => {
            new_track.set_dataset(new Dataset(track_data));
            new_track.tiles_div.text("Running job.");
            new_track.init();
        });
    },

    /**
     * Run tool using a set of URL params and a success callback.
     */
    run: function (url_params, new_track, success_callback) {
        // Run tool.
        url_params.inputs = this.model.get_inputs_dict();
        var ss_deferred = new util.ServerStateDeferred({
            ajax_settings: {
                url: `${getAppRoot()}api/tools`,
                data: JSON.stringify(url_params),
                dataType: "json",
                contentType: "application/json",
                type: "POST",
            },
            interval: 2000,
            success_fn: function (response) {
                return response !== "pending";
            },
        });

        // Start with this status message.
        //new_track.container_div.addClass("pending");
        //new_track.content_div.html(DATA_PENDING);

        $.when(ss_deferred.go()).then((response) => {
            if (response === "no converter") {
                // No converter available for input datasets, so cannot run tool.
                new_track.container_div.addClass("error");
                new_track.content_div.text(DATA_NOCONVERTER);
            } else if (response.error) {
                // General error.
                new_track.container_div.addClass("error");
                new_track.content_div.text(DATA_CANNOT_RUN_TOOL + response.message);
            } else {
                // Job submitted and running.
                success_callback(response);
            }
        });
    },
});

/**
 * Generates scale values based on filter and feature's value for filter.
 */
var FilterScaler = function (filter, default_val) {
    painters.Scaler.call(this, default_val);
    this.filter = filter;
};

FilterScaler.prototype.gen_val = function (feature_data) {
    // If filter is not initalized yet, return default val.
    if (
        this.filter.high === Number.MAX_VALUE ||
        this.filter.low === -Number.MAX_VALUE ||
        this.filter.low === this.filter.high
    ) {
        return this.default_val;
    }

    // Scaling value is ratio of (filter's value compared to low) to (complete filter range).
    return (parseFloat(feature_data[this.filter.index]) - this.filter.low) / (this.filter.high - this.filter.low);
};

/**
 * Tiles drawn by tracks.
 */
var Tile = function (track, region, w_scale, canvas, data) {
    this.track = track;
    this.region = region;
    this.low = region.get("start");
    this.high = region.get("end");
    this.w_scale = w_scale;
    this.canvas = canvas;
    // Wrap element in div for background and to provide container for tile-specific elements.
    this.html_elt = $("<div class='track-tile'/>").append(canvas);
    this.data = data;
    this.stale = false;
};

/**
 * Perform pre-display actions.
 */
Tile.prototype.predisplay_actions = () => {};

var LineTrackTile = function (track, region, w_scale, canvas, data) {
    Tile.call(this, track, region, w_scale, canvas, data);
};
LineTrackTile.prototype.predisplay_actions = () => {};

var FeatureTrackTile = function (
    track,
    region,
    w_scale,
    canvas,
    data,
    mode,
    message,
    all_slotted,
    feature_mapper,
    incomplete_features,
    seq_data
) {
    // Attribute init.
    Tile.call(this, track, region, w_scale, canvas, data);
    this.mode = mode;
    this.all_slotted = all_slotted;
    this.feature_mapper = feature_mapper;
    this.has_icons = false;
    this.incomplete_features = incomplete_features;
    // Features drawn based on data from other tiles.
    this.other_tiles_features_drawn = {};
    this.seq_data = seq_data;

    // Add message + action icons to tile's html.
    /*
    This does not work right now because a random set of reads is returned by the server.
    When the server can respond with more data systematically, renable these icons.
    if (message) {
        this.has_icons = true;

        var
            tile = this;
            canvas = this.html_elt.children()[0],
            message_div = $("<div/>").addClass("tile-message")
                            // -1 to account for border.
                            .css({'height': ERROR_PADDING, 'width': canvas.width}).prependTo(this.html_elt);

        // Handle message; only message currently is that only the first N elements are displayed.
        var tile_region = new visualization.GenomeRegion({
                chrom: track.view.chrom,
                start: this.low,
                end: this.high
            }),
            num_features = data.length,
            more_down_icon = $("<a/>").addClass("icon more-down")
                                .attr("title", "For speed, only the first " + num_features + " features in this region were obtained from server. Click to get more data including depth")
                                .tooltip().appendTo(message_div),
            more_across_icon = $("<a/>").addClass("icon more-across")
                                .attr("title", "For speed, only the first " + num_features + " features in this region were obtained from server. Click to get more data excluding depth")
                                .tooltip().appendTo(message_div);

        // Set up actions for icons.
        more_down_icon.click(function() {
            // Mark tile as stale, request more data, and redraw track.
            tile.stale = true;
            track.data_manager.get_more_data(tile_region, track.mode, 1 / tile.w_scale, {}, track.data_manager.DEEP_DATA_REQ);
            $(".tooltip").hide();
            track.request_draw();
        }).dblclick(function(e) {
            // Do not propogate as this would normally zoom in.
            e.stopPropagation();
        });

        more_across_icon.click(function() {
            // Mark tile as stale, request more data, and redraw track.
            tile.stale = true;
            track.data_manager.get_more_data(tile_region, track.mode, 1 / tile.w_scale, {}, track.data_manager.BROAD_DATA_REQ);
            $(".tooltip").hide();
            track.request_draw();
        }).dblclick(function(e) {
            // Do not propogate as this would normally zoom in.
            e.stopPropagation();
        });
    }
    */
};
extend(FeatureTrackTile.prototype, Tile.prototype);

/**
 * Sets up support for popups.
 */
FeatureTrackTile.prototype.predisplay_actions = () => {
    /*
    FIXME: use a canvas library to handle popups.
    //
    // Add support for popups.
    //
    var tile = this,
        popups = {};

    // Only show popups in Pack mode.
    if (tile.mode !== "Pack") { return; }

    $(this.html_elt).hover(
    function() {
        this.hovered = true;
        $(this).mousemove();
    },
    function() {
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
                var feature_dict = {
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
                popup = $("<div/>").attr("id", feature_uid).addClass("feature-popup");
                var table = $("<table/>"),
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
                popupX = offsetX + parseInt( tile.html_elt.css("left"), 10 ) - popup.width() / 2,
                popupY = offsetY + parseInt( tile.html_elt.css("top"), 10 ) + 7;
            popup.css("left", popupX + "px").css("top", popupY + "px");
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
    */
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
 * ----> VariantTrack
 */
var Track = function (view, container, obj_dict) {
    // For now, track's container is always view.
    extend(obj_dict, {
        drag_handle_class: "draghandle",
    });
    Drawable.call(this, view, container, obj_dict);

    //
    // Attribute init.
    //

    // Set or create dataset.
    this.dataset = null;
    if (obj_dict.dataset) {
        // Dataset can be a Backbone model or a dict that can be used to create a model.
        this.dataset = obj_dict.dataset instanceof Backbone.Model ? obj_dict.dataset : new Dataset(obj_dict.dataset);
    }
    this.dataset_check_type = "converted_datasets_state";
    this.data_url_extra_params = {};
    this.data_query_wait = "data_query_wait" in obj_dict ? obj_dict.data_query_wait : DEFAULT_DATA_QUERY_WAIT;
    // A little ugly creating data manager right now due to transition to Backbone-based objects.
    this.data_manager =
        "data_manager" in obj_dict
            ? obj_dict.data_manager
            : new visualization.GenomeDataManager({
                  dataset: this.dataset,
                  // HACK: simulate 'genome' attributes from view for now.
                  // View should eventually use Genome object.
                  genome: new visualization.Genome({
                      key: view.dbkey,
                      chroms_info: {
                          chrom_info: view.chrom_data,
                      },
                  }),
                  data_mode_compatible: this.data_and_mode_compatible,
                  can_subset: this.can_subset,
              });

    // Height attributes: min height, max height, and visible height.
    this.min_height_px = 16;
    this.max_height_px = 800;
    this.visible_height_px = this.config.get_value("height");

    //
    // Create content div, which is where track is displayed, and add to container if available.
    //
    this.content_div = $("<div class='track-content'>").appendTo(this.container_div);
    if (this.container) {
        this.container.content_div.append(this.container_div);
        if (!("resize" in obj_dict) || obj_dict.resize) {
            this.add_resize_handle();
        }
    }
};

extend(Track.prototype, Drawable.prototype, {
    action_icons_def: [
        // Change track mode.
        {
            name: "mode_icon",
            title: _l("Set display mode"),
            css_class: "chevron-expand",
            on_click_fn: function () {},
        },
        // Hide/show content.
        Drawable.prototype.action_icons_def[0],
        // Set track as overview.
        {
            name: "overview_icon",
            title: _l("Set as overview"),
            css_class: "application-dock-270",
            on_click_fn: function (track) {
                track.view.set_overview(track);
            },
        },
        // Edit config.
        Drawable.prototype.action_icons_def[1],
        // Toggle track filters.
        {
            name: "filters_icon",
            title: _l("Filters"),
            css_class: "ui-slider-050",
            on_click_fn: function (drawable) {
                // TODO: update Tooltip text.
                if (drawable.filters_manager.visible()) {
                    drawable.filters_manager.clear_filters();
                } else {
                    drawable.filters_manager.init_filters();
                }
                drawable.filters_manager.toggle();
            },
        },
        // Toggle track tool.
        {
            name: "tools_icon",
            title: _l("Tool"),
            css_class: "hammer",
            on_click_fn: function (track) {
                // TODO: update Tooltip text.

                track.tool.toggle();

                // Update track name.
                if (track.tool.is_visible()) {
                    track.set_name(track.config.get_value("name") + track.tool_region_and_parameters_str());
                } else {
                    track.revert_name();
                }
                // HACK: name change modifies icon placement, which leaves tooltip incorrectly placed.
                $(".tooltip").remove();
            },
        },
        // Go to parameter exploration visualization.
        {
            name: "param_space_viz_icon",
            title: _l("Tool parameter space visualization"),
            css_class: "arrow-split",
            on_click_fn: (track) => {
                const Galaxy = getGalaxyInstance();

                var html = `
                    <strong>Tool</strong>:${track.tool.get("name")}<br/>
                    <strong>Dataset</strong>:${track.config.get_value("name")}<br/>
                    <strong>Region(s)</strong>:
                        <select name="regions">
                            <option value="cur">current viewing area</option>
                            <option value="bookmarks">bookmarks</option>
                            <option value="both">current viewing area and bookmarks</option>
                        </select>
                    `;

                var cancel_fn = () => {
                    Galaxy.modal.hide();
                    $(window).unbind("keypress.check_enter_esc");
                };

                var ok_fn = () => {
                    var regions_to_use = $('select[name="regions"] option:selected').val();
                    var regions;
                    var view_region = new visualization.GenomeRegion({
                        chrom: this.view.chrom,
                        start: this.view.low,
                        end: this.view.high,
                    });
                    var bookmarked_regions = _.map(
                        $(".bookmark"),
                        (elt) =>
                            new visualization.GenomeRegion({
                                from_str: $(elt).children(".position").text(),
                            })
                    );

                    // Get regions for visualization.
                    if (regions_to_use === "cur") {
                        // Use only current region.
                        regions = [view_region];
                    } else if (regions_to_use === "bookmarks") {
                        // Use only bookmarks.
                        regions = bookmarked_regions;
                    } else {
                        // Use both current region and bookmarks.
                        regions = [view_region].concat(bookmarked_regions);
                    }

                    Galaxy.modal.hide();

                    // Go to visualization.
                    window.top.location.href = `${getAppRoot()}visualization/sweepster?${$.param({
                        dataset_id: track.dataset.id,
                        hda_ldda: track.dataset.get("hda_ldda"),
                        regions: JSON.stringify(new Backbone.Collection(regions).toJSON()),
                    })}`;
                };

                /*
                 * TODO: Re-enable this when functional.
                var check_enter_esc = e => {
                    if ((e.keyCode || e.which) === 27) {
                        // Escape key
                        cancel_fn();
                    } else if ((e.keyCode || e.which) === 13) {
                        // Enter key
                        ok_fn();
                    }
                };
                */

                // show dialog
                Galaxy.modal.show({
                    title: "Visualize tool parameter space and output from different parameter settings?",
                    body: html,
                    buttons: { No: cancel_fn, Yes: ok_fn },
                });
            },
        },
        // Remove track.
        Drawable.prototype.action_icons_def[2],
    ],

    can_draw: function () {
        return this.dataset && Drawable.prototype.can_draw.call(this);
    },

    build_container_div: function () {
        return $("<div/>").addClass("track").attr("id", `track_${this.id}`);
    },

    /**
     * Set track's dataset.
     */
    set_dataset: function (dataset) {
        this.dataset = dataset;
        this.data_manager.set("dataset", dataset);
    },

    /**
     * Action to take during resize.
     */
    on_resize: function () {
        this.request_draw({ clear_tile_cache: true });
    },

    /**
     * Add resizing handle to drawable's container_div.
     */
    add_resize_handle: function () {
        var track = this;
        var in_handle = false;
        var in_drag = false;
        var drag_control = $("<div class='track-resize'>");
        // Control shows on hover over track, stays while dragging
        $(track.container_div).hover(
            () => {
                if (track.config.get_value("content_visible")) {
                    in_handle = true;
                    drag_control.show();
                }
            },
            () => {
                in_handle = false;
                if (!in_drag) {
                    drag_control.hide();
                }
            }
        );
        // Update height and force redraw of current view while dragging,
        // clear cache to force redraw of other tiles.
        drag_control
            .hide()
            .bind("dragstart", (e, d) => {
                in_drag = true;
                d.original_height = $(track.content_div).height();
            })
            .bind("drag", (e, d) => {
                var new_height = Math.min(
                    Math.max(d.original_height + d.deltaY, track.min_height_px),
                    track.max_height_px
                );
                $(track.tiles_div).css("height", new_height);
                track.visible_height_px = track.max_height_px === new_height ? 0 : new_height;
                track.on_resize();
            })
            .bind("dragend", (e, d) => {
                track.tile_cache.clear();
                in_drag = false;
                if (!in_handle) {
                    drag_control.hide();
                }
                track.config.set_value("height", track.visible_height_px);
                track.changed();
            })
            .appendTo(track.container_div);
    },

    /**
     * Hide any elements that are part of the tracks contents area. Should
     * remove as approprite, the track will be redrawn by show_contents.
     */
    hide_contents: function () {
        // Hide tiles.
        this.tiles_div.hide();
        // Hide any y axis labels (common to several track types)
        this.container_div.find(".yaxislabel, .track-resize").hide();
    },

    show_contents: function () {
        // Show the contents div and labels (if present)
        this.tiles_div.show();
        this.container_div.find(".yaxislabel, .track-resize").show();
        // Request a redraw of the content
        this.request_draw();
    },

    /**
     * Returns track type.
     */
    get_type: function () {
        // Order is important: start with most-specific classes and go up the track hierarchy.
        if (this instanceof LabelTrack) {
            return "LabelTrack";
        } else if (this instanceof ReferenceTrack) {
            return "ReferenceTrack";
        } else if (this instanceof LineTrack) {
            return "LineTrack";
        } else if (this instanceof ReadTrack) {
            return "ReadTrack";
        } else if (this instanceof VariantTrack) {
            return "VariantTrack";
        } else if (this instanceof CompositeTrack) {
            return "CompositeTrack";
        } else if (this instanceof FeatureTrack) {
            return "FeatureTrack";
        }
        return "";
    },

    /**
     * Remove visualization content and display message.
     */
    show_message: function (msg_html) {
        this.tiles_div.remove();
        return $("<span/>").addClass("message").html(msg_html).appendTo(this.content_div);
    },

    /**
     * Initialize and draw the track.
     */
    init: function (retry) {
        // FIXME: track should have a 'state' attribute that is checked on load; this state attribute should be
        // used in this function to determine what action(s) to take.

        var track = this;
        track.enabled = false;
        track.tile_cache.clear();
        track.data_manager.clear();
        /*
        if (!track.content_div.text()) {
            track.content_div.text(DATA_LOADING);
        }
        */
        // Remove old track content (e.g. tiles, messages).
        track.content_div.children().remove();
        track.container_div.removeClass("nodata error pending");

        track.tiles_div = $("<div/>").addClass("tiles").appendTo(track.content_div);

        //
        // Tracks with no dataset id are handled differently.
        // FIXME: is this really necessary?
        //
        if (!track.dataset.id) {
            return;
        }

        // Get dataset state; if state is fine, enable and draw track. Otherwise, show message
        // about track status.
        var init_deferred = $.Deferred();

        var params = {
            hda_ldda: track.dataset.get("hda_ldda"),
            data_type: this.dataset_check_type,
            chrom: track.view.chrom,
            retry: retry,
        };

        $.getJSON(this.dataset.url(), params, (result) => {
            if (!result || result === "error" || result.kind === "error") {
                // Dataset is in error state.
                track.container_div.addClass("error");
                var msg_elt = track.show_message(DATA_ERROR);
                if (result.message) {
                    // Add links to (a) show error and (b) try again.
                    msg_elt.append(
                        $("<a href='javascript:void(0);'></a>")
                            .text("View error")
                            .click(() => {
                                const Galaxy = getGalaxyInstance();
                                Galaxy.modal.show({
                                    title: _l("Trackster Error"),
                                    body: `<pre>${result.message}</pre>`,
                                    buttons: {
                                        Close: function () {
                                            Galaxy.modal.hide();
                                        },
                                    },
                                });
                            })
                    );
                    msg_elt.append($("<span/>").text(" "));
                    msg_elt.append(
                        $("<a href='javascript:void(0);'></a>")
                            .text("Try again")
                            .click(() => {
                                track.init(true);
                            })
                    );
                }
            } else if (result === "no converter") {
                track.container_div.addClass("error");
                track.show_message(DATA_NOCONVERTER);
            } else if (
                result === "no data" ||
                (result.data !== undefined && (result.data === null || result.data.length === 0))
            ) {
                track.container_div.addClass("nodata");
                track.show_message(DATA_NONE);
            } else if (result === "pending") {
                track.container_div.addClass("pending");
                track.show_message(DATA_PENDING);
                //$("<img/>").attr("src", image_path + "/yui/rel_interstitial_loading.gif").appendTo(track.tiles_div);
                window.setTimeout(() => {
                    track.init();
                }, track.data_query_wait);
            } else if (result === "data" || result.status === "data") {
                if (result.valid_chroms) {
                    track.valid_chroms = result.valid_chroms;
                    track.update_icons();
                }
                track.tiles_div.text(DATA_OK);
                if (track.view.chrom) {
                    track.tiles_div.text("");
                    track.tiles_div.css("height", `${track.visible_height_px}px`);
                    track.enabled = true;
                    // predraw_init may be asynchronous, wait for it and then draw
                    $.when.apply($, track.predraw_init()).done(() => {
                        init_deferred.resolve();
                        track.container_div.removeClass("nodata error pending");
                        track.request_draw();
                    });
                } else {
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
    predraw_init: function () {
        var track = this;
        return $.getJSON(
            track.dataset.url(),
            {
                data_type: "data",
                stats: true,
                chrom: track.view.chrom,
                low: 0,
                high: track.view.max_high,
                hda_ldda: track.dataset.get("hda_ldda"),
            },
            (result) => {
                var data = result.data;

                // Tracks may not have stat data either because there is no data or data is not yet ready.
                if (data && data.min !== undefined && data.max !== undefined) {
                    // Compute default minimum and maximum values
                    var min_value = data.min;

                    var max_value = data.max;
                    // If mean and sd are present, use them to compute a ~95% window
                    // but only if it would shrink the range on one side
                    min_value = Math.floor(Math.min(0, Math.max(min_value, data.mean - 2 * data.sd)));
                    max_value = Math.ceil(Math.max(0, Math.min(max_value, data.mean + 2 * data.sd)));
                    // Update config, prefs
                    track.config.set_default_value("min_value", min_value);
                    track.config.set_default_value("max_value", max_value);
                    track.config.set_value("min_value", min_value);
                    track.config.set_value("max_value", max_value);
                }
            }
        );
    },

    /**
     * Returns all drawables in this drawable.
     */
    get_drawables: function () {
        return this;
    },
});

var TiledTrack = function (view, container, obj_dict) {
    Track.call(this, view, container, obj_dict);

    var track = this;

    // Make track moveable.
    moveable(track.container_div, track.drag_handle_class, ".group", track);

    // Attribute init.
    this.filters_manager = new filters_mod.FiltersManager(this, "filters" in obj_dict ? obj_dict.filters : null);
    // HACK: set filters manager for data manager.
    // FIXME: prolly need function to set filters and update data_manager reference.
    this.data_manager.set("filters_manager", this.filters_manager);
    this.filters_available = false;
    this.tool = obj_dict.tool
        ? new TracksterTool(
              _.extend(obj_dict.tool, {
                  track: this,
                  tool_state: obj_dict.tool_state,
              })
          )
        : null;
    this.tile_cache = new visualization.Cache(TILE_CACHE_SIZE);
    this.left_offset = 0;

    if (this.header_div) {
        //
        // Setup filters.
        //
        this.set_filters_manager(this.filters_manager);

        //
        // Create dynamic tool view.
        //
        if (this.tool) {
            var tool_view = new TracksterToolView({ model: this.tool });
            tool_view.render();
            this.dynamic_tool_div = tool_view.$el;
            this.header_div.after(this.dynamic_tool_div);
        }
    }

    // Add tiles_div, overlay_div to content_div.
    this.tiles_div = $("<div/>").addClass("tiles").appendTo(this.content_div);
    if (!this.config.get_value("content_visible")) {
        this.tiles_div.hide();
    }
    this.overlay_div = $("<div/>").addClass("overlay").appendTo(this.content_div);

    if (obj_dict.mode) {
        this.change_mode(obj_dict.mode);
    }
};
extend(TiledTrack.prototype, Drawable.prototype, Track.prototype, {
    action_icons_def: Track.prototype.action_icons_def.concat([
        // Show more rows when all features are not slotted.
        {
            name: "show_more_rows_icon",
            title: "To minimize track height, not all feature rows are displayed. Click to display more rows.",
            css_class: "exclamation",
            on_click_fn: function (track) {
                $(".tooltip").remove();
                track.slotters[track.view.resolution_px_b].max_rows *= 2;
                track.request_draw({ clear_tile_cache: true });
            },
            hide: true,
        },
    ]),

    /**
     * Returns a copy of the track. The copy uses the same data manager so that the tracks can share data.
     */
    copy: function (container) {
        // Create copy.
        var obj_dict = this.to_dict();
        extend(obj_dict, {
            data_manager: this.data_manager,
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
    set_filters_manager: function (filters_manager) {
        this.filters_manager = filters_manager;
        this.header_div.after(this.filters_manager.parent_div);
    },

    /**
     * Returns representation of object in a dictionary for easy saving.
     * Use from_dict to recreate object.
     */
    to_dict: function () {
        return {
            track_type: this.get_type(),
            dataset: {
                id: this.dataset.id,
                hda_ldda: this.dataset.get("hda_ldda"),
            },
            prefs: this.config.to_key_value_dict(),
            mode: this.mode,
            filters: this.filters_manager.to_dict(),
            tool_state: this.tool ? this.tool.state_dict() : {},
        };
    },

    /**
     * Set track bounds for current chromosome.
     */
    set_min_max: function () {
        var track = this;

        return $.getJSON(
            track.dataset.url(),
            {
                data_type: "data",
                stats: true,
                chrom: track.view.chrom,
                low: 0,
                high: track.view.max_high,
                hda_ldda: track.dataset.get("hda_ldda"),
            },
            (result) => {
                var data = result.data;
                if (
                    isNaN(parseFloat(track.config.get_value("min_value"))) ||
                    isNaN(parseFloat(track.config.get_value("max_value")))
                ) {
                    // Compute default minimum and maximum values
                    var min_value = data.min;

                    var max_value = data.max;
                    // If mean and sd are present, use them to compute a ~95% window
                    // but only if it would shrink the range on one side
                    min_value = Math.floor(Math.min(0, Math.max(min_value, data.mean - 2 * data.sd)));
                    max_value = Math.ceil(Math.max(0, Math.min(max_value, data.mean + 2 * data.sd)));
                    // Update the prefs
                    track.config.set_value("min_value", min_value);
                    track.config.set_value("max_value", max_value);
                }
            }
        );
    },

    /**
     * Change track's mode.
     */
    change_mode: function (new_mode) {
        var track = this;
        // TODO: is it necessary to store the mode in two places (.mode and track_config)?
        track.mode = new_mode;
        track.config.set_value("mode", new_mode);
        // FIXME: find a better way to get Auto data w/o clearing cache; using mode in the
        // data manager would work if Auto data were checked for compatibility when a specific
        // mode is chosen.
        if (new_mode === "Auto") {
            this.data_manager.clear();
        }
        track.request_draw({ clear_tile_cache: true });
        this.action_icons.mode_icon.attr("title", `Set display mode (now: ${track.mode})`);
        return track;
    },

    /**
     * Update track's buttons.
     */
    update_icons: function () {
        var track = this;

        //
        // Show/hide filter icon.
        //
        track.action_icons.filters_icon.toggle(track.filters_available);

        //
        // Show/hide tool icons.
        //
        track.action_icons.tools_icon.toggle(track.tool !== null);
        track.action_icons.param_space_viz_icon.toggle(track.tool !== null);
    },

    /**
     * Generate a key for the tile cache.
     * TODO: create a TileCache object (like DataCache) and generate key internally.
     */
    _gen_tile_cache_key: function (w_scale, tile_region) {
        return `${w_scale}_${tile_region}`;
    },

    /**
     * Request that track be drawn.
     */
    request_draw: function (options) {
        if (options && options.clear_tile_cache) {
            this.tile_cache.clear();
        }
        this.view.request_redraw(options, this);
    },

    /**
     * Actions to be taken before drawing.
     */
    before_draw: function () {
        // Clear because this is set when drawing.
        this.max_height_px = 0;
    },

    /**
     * Draw track. Options include:
     * -force: force a redraw rather than use cached tiles (default: false)
     * -clear_after: clear old tiles after drawing new tiles (default: false)
     * -data_fetch: fetch data if necessary (default: true)
     *
     * NOTE: this function should never be called directly; use request_draw() so that drawing
     * management can be used.
     */
    _draw: function (options) {
        if (!this.can_draw()) {
            return;
        }

        var clear_after = options && options.clear_after;
        var low = this.view.low;
        var high = this.view.high;
        //var range = high - low;
        var width = this.view.container.width();
        var w_scale = this.view.resolution_px_b;
        var resolution = 1 / w_scale;

        // For overview, adjust high, low, resolution, and w_scale.
        if (this.is_overview) {
            low = this.view.max_low;
            high = this.view.max_high;
            w_scale = width / (this.view.max_high - this.view.max_low);
            resolution = 1 / w_scale;
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

        var // Tile width in bases.
            tile_width = Math.floor(TILE_SIZE * resolution);

        var // Index of first tile that overlaps visible region.
            tile_index = Math.floor(low / tile_width);

        var tile_region;
        var tile_promise;
        var tile_promises = [];
        var tiles = [];
        // Draw tiles.
        while (tile_index * tile_width < high) {
            // Get tile region.
            tile_region = new visualization.GenomeRegion({
                chrom: this.view.chrom,
                start: tile_index * tile_width,
                // Tile high cannot be larger than view.max_high, which the chromosome length.
                end: Math.min((tile_index + 1) * tile_width, this.view.max_high),
            });
            tile_promise = this.draw_helper(tile_region, w_scale, options);
            tile_promises.push(tile_promise);
            $.when(tile_promise).then((tile) => {
                tiles.push(tile);
            });

            // Go to next tile.
            tile_index += 1;
        }

        // Step (c) for (re)moving tiles when clear_after is false.
        if (!clear_after) {
            this.tiles_div.children(".remove").removeClass("remove").remove();
        }

        // When all tiles are drawn, call post-draw actions.
        $.when.apply($, tile_promises).then(() => {
            // Step (c) for (re)moving tiles when clear_after is true:
            this.tiles_div.children(".remove").remove();

            // Only do postdraw actions for tiles; instances where tiles may not be drawn include:
            // (a) ReferenceTrack without sufficient resolution;
            // (b) data_fetch = false.
            tiles = _.filter(tiles, (t) => t !== null);
            if (tiles.length !== 0) {
                this.postdraw_actions(tiles, width, w_scale, clear_after);
            }
        });
    },

    /**
     * Add a maximum/minimum label to track.
     */
    _add_yaxis_label: function (type, on_change) {
        var css_class = type === "max" ? "top" : "bottom";
        var text = type === "max" ? "max" : "min";
        var pref_name = type === "max" ? "max_value" : "min_value";
        var label = this.container_div.find(`.yaxislabel.${css_class}`);
        var value = round(this.config.get_value(pref_name), 1);

        // Default action for on_change is to redraw track.
        on_change =
            on_change ||
            (() => {
                this.request_draw({ clear_tile_cache: true });
            });

        if (label.length !== 0) {
            // Label already exists, so update value.
            label.text(value);
        } else {
            // Add label.
            label = $("<div/>")
                .text(value)
                .make_text_editable({
                    num_cols: 12,
                    on_finish: function (new_val) {
                        $(".tooltip").remove();
                        this.config.set_value(pref_name, round(new_val, 1));
                        on_change();
                    },
                    help_text: `Set ${text} value`,
                })
                .addClass(`yaxislabel ${css_class}`)
                .css("color", this.config.get_value("label_color"));
            this.container_div.prepend(label);
        }
    },

    /**
     * Actions to be taken after draw has been completed. Draw is completed when all tiles have been
     * drawn/fetched and shown.
     */
    postdraw_actions: function (tiles, width, w_scale, clear_after) {
        var line_track_tiles = _.filter(tiles, (tile) => tile instanceof LineTrackTile);

        //
        // Take different actions depending on whether there are LineTrack/Coverage tiles.
        //

        if (line_track_tiles.length > 0) {
            // -- Drawing in Coverage mode. --

            // Clear because this is set when drawing.
            this.max_height_px = 0;
            _.each(tiles, (tile) => {
                if (!(tile instanceof LineTrackTile)) {
                    tile.html_elt.remove();
                    this.draw_helper(tile.region, w_scale, {
                        force: true,
                        mode: "Coverage",
                    });
                }
            });

            this._add_yaxis_label("max");
        } else {
            // -- Drawing in non-Coverage mode. --

            // Remove Y-axis labels because there are no line track tiles.
            this.container_div.find(".yaxislabel").remove();

            //
            // If some tiles have icons, set padding of tiles without icons so features and rows align.
            //
            var icons_present = _.find(tiles, (tile) => tile.has_icons);

            if (icons_present) {
                _.each(tiles, (tile) => {
                    if (!tile.has_icons) {
                        // Need to align with other tile(s) that have icons.
                        tile.html_elt.css("padding-top", ERROR_PADDING);
                    }
                });
            }
        }
    },

    /**
     * Returns appropriate display mode based on data.
     */
    get_mode: function (data) {
        return this.mode;
    },

    /**
     * Update track interface to show display mode being used.
     */
    update_auto_mode: function (display_mode) {
        // FIXME: needs to be implemented.
    },

    /**
     * Returns a list of drawables to draw. Defaults to current track.
     */
    _get_drawables: function () {
        return [this];
    },

    /**
     * Retrieves from cache, draws, or sets up drawing for a single tile. Returns either a Tile object or a
     * jQuery.Deferred object that is fulfilled when tile can be drawn again. Options include:
     * -force: force a redraw rather than use cached tiles (default: false)
     * -data_fetch: fetch data if necessary (default: true)
     */
    draw_helper: function (region, w_scale, options) {
        // Init options if necessary to avoid having to check if options defined.
        if (!options) {
            options = {};
        }

        var force = options.force;
        var mode = options.mode || this.mode;
        var resolution = 1 / w_scale;

        var drawables = this._get_drawables();
        var key = this._gen_tile_cache_key(w_scale, region);

        var is_tile = (o) => o && "track" in o;

        // Check tile cache, if found show existing tile in correct position
        var tile = force ? undefined : this.tile_cache.get_elt(key);
        if (tile) {
            if (is_tile(tile)) {
                this.show_tile(tile, w_scale);
            }
            return tile;
        }

        // If not fetching data, nothing more to do because data is needed to draw tile.
        if (options.data_fetch === false) {
            return null;
        }

        // Function that returns data/Deferreds needed to draw tile.
        var get_tile_data = () => {
            // HACK: if display mode (mode) is in continuous data modes, data mode must be coverage to get coverage data.
            var data_mode = _.find(CONTINUOUS_DATA_MODES, (m) => m === mode) ? "Coverage" : mode;

            // Map drawable object to data needed for drawing.
            var tile_data = _.map(drawables, (d) =>
                // Get the track data/promise.
                d.data_manager.get_data(region, data_mode, resolution, this.data_url_extra_params)
            );

            // Get reference data/promise.
            if (this.view.reference_track) {
                tile_data.push(
                    this.view.reference_track.data_manager.get_data(
                        region,
                        mode,
                        resolution,
                        this.view.reference_track.data_url_extra_params
                    )
                );
            }

            return tile_data;
        };

        //
        // When data is available, draw tile.
        //
        var tile_drawn = $.Deferred();
        this.tile_cache.set_elt(key, tile_drawn);
        $.when.apply($, get_tile_data()).then(() => {
            var tile_data = get_tile_data();
            var tracks_data = tile_data;
            var seq_data;

            // Deferreds may show up here if trying to fetch a subset of data from a superset data chunk
            // that cannot be subsetted. This may occur if the superset has a message. If there is a
            // Deferred, try again from the top. NOTE: this condition could (should?) be handled by the
            // GenomeDataManager in visualization module.
            if (_.find(tile_data, (d) => util.is_deferred(d))) {
                this.tile_cache.set_elt(key, undefined);
                $.when(this.draw_helper(region, w_scale, options)).then((tile) => {
                    tile_drawn.resolve(tile);
                });
                return;
            }

            // If sequence data is available, subset to get only data in region.
            if (this.view.reference_track) {
                seq_data = this.view.reference_track.data_manager.subset_entry(tile_data.pop(), region);
            }

            // Get drawing modes, heights for all tracks.
            var drawing_modes = [];
            var drawing_heights = [];

            _.each(drawables, (d, i) => {
                var data = tracks_data[i];
                if (d.mode === "Auto") {
                    d.mode = d.get_mode(data);
                    d.update_auto_mode(d.mode);
                }
                drawing_modes.push(d.mode);
                drawing_heights.push(d.get_canvas_height(data, d.mode, w_scale, width));
            });

            var canvas = this.view.canvas_manager.new_canvas();
            var tile_low = region.get("start");
            var tile_high = region.get("end");
            var width = Math.ceil((tile_high - tile_low) * w_scale) + this.left_offset;
            var height = _.max(drawing_heights);
            var tile;

            //
            // Draw all tracks on tile.
            //
            canvas.width = width;
            // Height is specified in options or is the height found above.
            canvas.height = options.height || height;
            var ctx = canvas.getContext("2d");
            ctx.translate(this.left_offset, 0);
            if (drawables.length > 1) {
                ctx.globalAlpha = 0.5;
                ctx.globalCompositeOperation = "source-over";
            }
            _.each(drawables, (d, i) => {
                tile = d.draw_tile(tracks_data[i], ctx, drawing_modes[i], region, w_scale, seq_data);
            });

            // Don't cache, show if no tile.
            if (tile !== undefined) {
                this.tile_cache.set_elt(key, tile);
                this.show_tile(tile, w_scale);
            }

            tile_drawn.resolve(tile);
        });

        return tile_drawn;
    },

    /**
     * Returns canvas height needed to display data; return value is an integer that denotes the
     * number of pixels required.
     */
    get_canvas_height: function (result, mode, w_scale, canvas_width) {
        return this.visible_height_px;
    },

    /**
     * Draw line (bigwig) data onto tile.
     */
    _draw_line_track_tile: function (result, ctx, mode, region, w_scale) {
        // Set min/max if they are not already set.
        // FIXME: checking for different null/undefined/0 is messy; it would be nice to
        // standardize this.
        if ([undefined, null].indexOf(this.config.get_value("min_value")) !== -1) {
            this.config.set_value("min_value", 0);
        }
        if ([undefined, null, 0].indexOf(this.config.get_value("max_value")) !== -1) {
            this.config.set_value("max_value", _.max(_.map(result.data, (d) => d[1])) || 0);
        }

        var canvas = ctx.canvas;

        var painter = new painters.LinePainter(
            result.data,
            region.get("start"),
            region.get("end"),
            this.config.to_key_value_dict(),
            mode
        );

        painter.draw(ctx, canvas.width, canvas.height, w_scale);

        return new LineTrackTile(this, region, w_scale, canvas, result.data);
    },

    /**
     * Draw a track tile.
     * @param result result from server
     * @param ctx canvas context to draw on
     * @param mode mode to draw in
     * @param region region to draw on tile
     * @param w_scale pixels per base
     * @param ref_seq reference sequence data
     */
    draw_tile: function (result, ctx, mode, region, w_scale, ref_seq) {},

    /**
     * Show track tile and perform associated actions. Showing tile may actually move
     * an existing tile rather than reshowing it.
     */
    show_tile: function (tile, w_scale) {
        var tile_element = tile.html_elt;

        // -- Show/move tile element. --

        tile.predisplay_actions();

        // Position tile element based on current viewport.
        var left = Math.round((tile.low - (this.is_overview ? this.view.max_low : this.view.low)) * w_scale);
        if (this.left_offset) {
            left -= this.left_offset;
        }
        tile_element.css("left", left);

        if (tile_element.hasClass("remove")) {
            // Step (b) for (re)moving tiles. See _draw() function for description of algorithm
            // for removing tiles.
            tile_element.removeClass("remove");
        } else {
            // Showing new tile.
            this.tiles_div.append(tile_element);
        }

        // -- Update track, tile heights based on new tile. --

        tile_element.css("height", "auto");

        // Update max height based on current tile's height.
        // BUG/HACK: tile_element.height() returns a height that is always 2 pixels too big, so
        // -2 to get the correct height.
        this.max_height_px = Math.max(this.max_height_px, tile_element.height() - 2);

        // Update height for all tiles based on max height.
        tile_element.parent().children().css("height", `${this.max_height_px}px`);

        // Update track height based on max height and visible height.
        var track_height = this.max_height_px;
        if (this.visible_height_px !== 0) {
            track_height = Math.min(this.max_height_px, this.visible_height_px);
        }
        this.tiles_div.css("height", `${track_height}px`);
    },

    /**
     * Utility function that creates a label string describing the region and parameters of a track's tool.
     */
    tool_region_and_parameters_str: function (region) {
        var track = this;
        var region_str = region !== undefined ? region.toString() : "all";
        var param_str = _.values(track.tool.get_inputs_dict()).join(", ");
        return ` - region=[${region_str}], parameters=[${param_str}]`;
    },

    /**
     * Returns true if data is compatible with a given mode.
     */
    data_and_mode_compatible: function (data, mode) {
        // Only handle modes that user can set.
        if (mode === "Auto") {
            return true;
        } else if (mode === "Coverage") {
            // Histogram mode requires bigwig data.
            return data.dataset_type === "bigwig";
        } else if (data.dataset_type === "bigwig" || data.extra_info === "no_detail") {
            // All other modes--Dense, Squish, Pack--require data + details.
            return false;
        } else {
            return true;
        }
    },

    /**
     * Returns true if entry can be subsetted.
     */
    can_subset: function (entry) {
        // Do not subset entries with a message or data with no detail.
        if (entry.message || entry.extra_info === "no_detail") {
            return false;
        } else if (entry.dataset_type === "bigwig") {
            // Subset only if data is single-bp resolution.
            return entry.data[1][0] - entry.data[0][0] === 1;
        }

        return true;
    },

    /**
     * Set up track to receive tool data.
     */
    init_for_tool_data: function () {
        // Set up track to fetch raw data rather than converted data.
        this.data_manager.set("data_type", "raw_data");
        this.data_query_wait = 1000;
        this.dataset_check_type = "state";

        // FIXME: this is optional and is disabled for now because it creates
        // additional converter jobs without a clear benefit because indexing
        // such a small dataset provides little benefit.
        //
        // Set up one-time, post-draw to clear tool execution settings.
        //
        /*
        this.normal_postdraw_actions = this.postdraw_actions;
        this.postdraw_actions = function(tiles, width, w_scale, clear_after) {
            var self = this;

            // Do normal postdraw init.
            self.normal_postdraw_actions(tiles, width, w_scale, clear_after);

            // Tool-execution specific post-draw init:

            // Reset dataset check, wait time.
            self.dataset_check_type = 'converted_datasets_state';
            self.data_query_wait = DEFAULT_DATA_QUERY_WAIT;

            // Reset data URL when dataset indexing has completed/when not pending.
            var ss_deferred = new util.ServerStateDeferred({
                url: self.dataset_state_url,
                url_params: {dataset_id : self.dataset.id, hda_ldda: self.dataset.get('hda_ldda')},
                interval: self.data_query_wait,
                // Set up deferred to check dataset state until it is not pending.
                success_fn: function(result) { return result !== "pending"; }
            });
            $.when(ss_deferred.go()).then(function() {
                // Dataset is indexed, so use converted data.
                self.data_manager.set('data_type', 'data');
            });

            // Reset post-draw actions function.
            self.postdraw_actions = self.normal_postdraw_actions;
        };
        */
    },
});

var LabelTrack = function (view, container) {
    Track.call(this, view, container, {
        resize: false,
        header: false,
    });
    this.container_div.addClass("label-track");
};
extend(LabelTrack.prototype, Track.prototype, {
    init: function () {
        // Enable by default because there should always be data when drawing track.
        this.enabled = true;
    },

    /**
     * Additional initialization required before drawing track for the first time.
     */
    predraw_init: function () {},

    _draw: function (options) {
        var view = this.view;
        var range = view.high - view.low;

        var tickDistance = Math.floor(Math.pow(10, Math.floor(Math.log(range) / Math.log(10))));

        var position = Math.floor(view.low / tickDistance) * tickDistance;
        var width = this.view.container.width();
        var new_div = $("<div/>").addClass("label-container");
        while (position < view.high) {
            var screenPosition = Math.floor(((position - view.low) / range) * width);
            new_div.append(
                $("<div/>").addClass("pos-label").text(util.commatize(position)).css({
                    left: screenPosition,
                })
            );
            position += tickDistance;
        }
        this.content_div.children(":first").remove();
        this.content_div.append(new_div);
    },
});

// FIXME: Composite tracks have code for showing composite tracks with line tracks and
// composite tracks with line + feature tracks. It's probably best if different classes
// are created for each type of composite track.

/**
 * A tiled track composed of multiple other tracks. Composite tracks only work with
 * bigwig data for now.
 */
var CompositeTrack = function (view, container, obj_dict) {
    TiledTrack.call(this, view, container, obj_dict);

    // Init drawables; each drawable is a copy so that config/preferences
    // are independent of each other. Also init left offset.
    this.drawables = [];
    if ("drawables" in obj_dict) {
        var drawable;
        for (var i = 0; i < obj_dict.drawables.length; i++) {
            drawable = obj_dict.drawables[i];
            this.drawables[i] = object_from_template(drawable, view, null);

            // Track's left offset is the max of all tracks.
            if (drawable.left_offset > this.left_offset) {
                this.left_offset = drawable.left_offset;
            }
        }
        this.enabled = true;
    }

    // Set all feature tracks to use Coverage mode.
    _.each(this.drawables, (d) => {
        if (d instanceof FeatureTrack || d instanceof ReadTrack) {
            d.change_mode("Coverage");
        }
    });

    this.update_icons();

    // HACK: needed for saving object for now. Need to generalize get_type() to all Drawables and use
    // that for object type.
    this.obj_type = "CompositeTrack";
};

extend(CompositeTrack.prototype, TiledTrack.prototype, {
    display_modes: CONTINUOUS_DATA_MODES,

    build_config_params: function () {
        return _.union(Drawable.prototype.config_params, [
            {
                key: "min_value",
                label: "Min Value",
                type: "float",
                default_value: undefined,
            },
            {
                key: "max_value",
                label: "Max Value",
                type: "float",
                default_value: undefined,
            },
            {
                key: "mode",
                type: "string",
                default_value: this.mode,
                hidden: true,
            },
            {
                key: "height",
                type: "int",
                default_value: 30,
                hidden: true,
            },
        ]);
    },

    action_icons_def: [
        // Create composite track from group's tracks.
        {
            name: "composite_icon",
            title: _l("Show individual tracks"),
            css_class: "layers-stack",
            on_click_fn: function (track) {
                $(".tooltip").remove();
                track.show_group();
            },
        },
    ].concat(TiledTrack.prototype.action_icons_def),

    // HACK: CompositeTrack should inherit from DrawableCollection as well.
    /**
     * Returns representation of object in a dictionary for easy saving.
     * Use from_dict to recreate object.
     */
    to_dict: DrawableCollection.prototype.to_dict,

    add_drawable: DrawableCollection.prototype.add_drawable,

    unpack_drawables: DrawableCollection.prototype.unpack_drawables,

    config_onchange: function () {
        this.set_name(this.config.get_value("name"));
        this.request_draw({ clear_tile_cache: true });
    },

    /**
     * Action to take during resize.
     */
    on_resize: function () {
        // Propogate visible height to other tracks.
        var visible_height = this.visible_height_px;
        _.each(this.drawables, (d) => {
            d.visible_height_px = visible_height;
        });
        Track.prototype.on_resize.call(this);
    },

    /**
     * Change mode for all tracks.
     */
    change_mode: function (new_mode) {
        TiledTrack.prototype.change_mode.call(this, new_mode);
        for (var i = 0; i < this.drawables.length; i++) {
            this.drawables[i].change_mode(new_mode);
        }
    },

    /**
     * Initialize component tracks and draw composite track when all components are initialized.
     */
    init: function () {
        // Init components.
        var init_deferreds = [];
        for (var i = 0; i < this.drawables.length; i++) {
            init_deferreds.push(this.drawables[i].init());
        }

        // Draw composite when all tracks available.
        var track = this;
        $.when.apply($, init_deferreds).then(() => {
            track.enabled = true;
            track.request_draw();
        });
    },

    update_icons: function () {
        // For now, hide filters and tool.
        this.action_icons.filters_icon.hide();
        this.action_icons.tools_icon.hide();
        this.action_icons.param_space_viz_icon.hide();
    },

    can_draw: Drawable.prototype.can_draw,

    _get_drawables: function () {
        return this.drawables;
    },

    /**
     * Replace this track with group that includes individual tracks.
     */
    show_group: function () {
        // Create group with individual tracks.
        var group = new DrawableGroup(this.view, this.container, {
            name: this.config.get_value("name"),
        });

        var track;
        for (var i = 0; i < this.drawables.length; i++) {
            track = this.drawables[i];
            track.update_icons();
            group.add_drawable(track);
            track.container = group;
            group.content_div.append(track.container_div);
        }

        // Replace track with group.
        this.container.replace_drawable(this, group, true);
        group.request_draw({ clear_tile_cache: true });
    },

    /**
     * Actions taken before drawing.
     */
    before_draw: function () {
        // FIXME: this is needed only if there are feature tracks in the composite track.
        // TiledTrack.prototype.before_draw.call(this);

        //
        // Set min, max for tracks to be largest min, max.
        //

        // Get smallest min, biggest max.
        var min = _.min(_.map(this.drawables, (d) => d.config.get_value("min_value")));

        var max = _.max(_.map(this.drawables, (d) => d.config.get_value("max_value")));

        this.config.set_value("min_value", min);
        this.config.set_value("max_value", max);

        // Set all tracks to smallest min, biggest max.
        _.each(this.drawables, (d) => {
            d.config.set_value("min_value", min);
            d.config.set_value("max_value", max);
        });
    },

    /**
     * Update minimum, maximum for component tracks.
     */
    update_all_min_max: function () {
        var min_value = this.config.get_value("min_value");
        var max_value = this.config.get_value("max_value");
        _.each(this.drawables, (d) => {
            d.config.set_value("min_value", min_value);
            d.config.set_value("max_value", max_value);
        });
        this.request_draw({ clear_tile_cache: true });
    },

    /**
     * Actions to be taken after draw has been completed. Draw is completed when all tiles have been
     * drawn/fetched and shown.
     */
    postdraw_actions: function (tiles, width, w_scale, clear_after) {
        // All tiles must be the same height in order to draw LineTracks, so redraw tiles as needed.
        var max_height = -1;

        var i;
        for (i = 0; i < tiles.length; i++) {
            var height = tiles[i].html_elt.find("canvas").height();
            if (height > max_height) {
                max_height = height;
            }
        }

        for (i = 0; i < tiles.length; i++) {
            var tile = tiles[i];
            if (tile.html_elt.find("canvas").height() !== max_height) {
                this.draw_helper(tile.region, w_scale, {
                    force: true,
                    height: max_height,
                });
                tile.html_elt.remove();
            }
        }

        // Wrap function so that it can be called without object reference.
        var track = this;

        var t = () => {
            track.update_all_min_max();
        };

        // Add min, max labels.
        this._add_yaxis_label("min", t);
        this._add_yaxis_label("max", t);
    },
});

/**
 * Displays reference genome data.
 */
var ReferenceTrack = function (view) {
    TiledTrack.call(this, view, { content_div: view.top_labeltrack }, { resize: false, header: false });

    // Use offset to ensure that bases at tile edges are drawn.
    this.left_offset = view.canvas_manager.char_width_px;
    this.container_div.addClass("reference-track");
    this.data_url = `${getAppRoot()}api/genomes/${this.view.dbkey}`;
    this.data_url_extra_params = { reference: true };
    this.data_manager = new visualization.GenomeReferenceDataManager({
        data_url: this.data_url,
        can_subset: this.can_subset,
    });
    this.hide_contents();
};
extend(ReferenceTrack.prototype, Drawable.prototype, TiledTrack.prototype, {
    build_config_params: function () {
        return _.union(Drawable.prototype.config_params, [
            {
                key: "height",
                type: "int",
                default_value: 13,
                hidden: true,
            },
        ]);
    },

    init: function () {
        this.data_manager.clear();
        // Enable by default because there should always be data when drawing track.
        this.enabled = true;
    },

    /**
     * Additional initialization required before drawing track for the first time.
     */
    predraw_init: function () {},

    can_draw: Drawable.prototype.can_draw,

    /**
     * Draws and shows tile if reference data can be displayed; otherwise track is hidden.
     */
    draw_helper: function (region, w_scale, options) {
        var cur_visible = this.tiles_div.is(":visible");
        var new_visible;
        var tile = null;
        if (w_scale > this.view.canvas_manager.char_width_px) {
            this.tiles_div.show();
            new_visible = true;
            tile = TiledTrack.prototype.draw_helper.call(this, region, w_scale, options);
        } else {
            new_visible = false;
            this.tiles_div.hide();
        }

        // NOTE: viewport resizing conceptually belongs in postdraw_actions(), but currently
        // postdraw_actions is not called when reference track not shown due to no tiles. If
        // it is moved to postdraw_actions, resize must be called each time because cannot
        // easily detect showing/hiding.

        // If showing or hiding reference track, resize viewport.
        if (cur_visible !== new_visible) {
            this.view.resize_viewport();
        }

        return tile;
    },

    can_subset: function (entry) {
        return true;
    },

    /**
     * Draw ReferenceTrack tile.
     */
    draw_tile: function (data, ctx, mode, region, w_scale) {
        // Try to subset data.
        var subset = this.data_manager.subset_entry(data, region);

        var seq_data = subset.data;

        // Draw sequence data.
        var canvas = ctx.canvas;
        ctx.font = ctx.canvas.manager.default_font;
        ctx.textAlign = "center";
        for (var c = 0, str_len = seq_data.length; c < str_len; c++) {
            ctx.fillStyle = this.view.get_base_color(seq_data[c]);
            ctx.fillText(seq_data[c], Math.floor(c * w_scale), 10);
        }
        return new Tile(this, region, w_scale, canvas, subset);
    },
});

/**
 * Track displays continuous/numerical data. Track expects position data in 1-based format, i.e. wiggle format.
 */
var LineTrack = function (view, container, obj_dict) {
    this.mode = "Histogram";
    TiledTrack.call(this, view, container, obj_dict);
    // Need left offset for drawing overlap near tile boundaries.
    this.left_offset = 30;

    // If server has byte-range support, use BBI data manager to read directly from the BBI file.
    // FIXME: there should be a flag to wait for this check to complete before loading the track.
    var self = this;
    $.when(supportsByteRanges(`${getAppRoot()}datasets/${this.dataset.id}/display`)).then((supportsByteRanges) => {
        if (supportsByteRanges) {
            self.data_manager = new bbi.BBIDataManager({
                dataset: self.dataset,
            });
        }
    });
};

extend(LineTrack.prototype, Drawable.prototype, TiledTrack.prototype, {
    display_modes: CONTINUOUS_DATA_MODES,

    build_config_params: function () {
        return _.union(Drawable.prototype.config_params, [
            { key: "color", label: "Color", type: "color" },
            {
                key: "min_value",
                label: "Min Value",
                type: "float",
                default_value: undefined,
            },
            {
                key: "max_value",
                label: "Max Value",
                type: "float",
                default_value: undefined,
            },
            {
                key: "mode",
                type: "string",
                default_value: this.mode,
                hidden: true,
            },
            {
                key: "height",
                type: "int",
                default_value: 30,
                hidden: true,
            },
        ]);
    },

    config_onchange: function () {
        this.set_name(this.config.get_value("name"));
        this.request_draw({ clear_tile_cache: true });
    },

    /**
     * Actions to be taken before drawing.
     */
    // FIXME: can the default behavior be used; right now it breaks during resize.
    before_draw: function () {},

    /**
     * Draw track tile.
     */
    draw_tile: function (result, ctx, mode, region, w_scale) {
        return this._draw_line_track_tile(result, ctx, mode, region, w_scale);
    },

    /**
     * Subset data only if data is at single-base pair resolution.
     */
    can_subset: function (entry) {
        return entry.data[1][0] - entry.data[0][0] === 1;
    },

    /**
     * Add min, max labels.
     */
    postdraw_actions: function (tiles, width, w_scale, clear_after) {
        // Add min, max labels.
        this._add_yaxis_label("max");
        this._add_yaxis_label("min");
    },
});

/**
 * Diagonal heatmap for showing interactions data.
 */
var DiagonalHeatmapTrack = function (view, container, obj_dict) {
    this.mode = "Heatmap";
    TiledTrack.call(this, view, container, obj_dict);
};

extend(DiagonalHeatmapTrack.prototype, Drawable.prototype, TiledTrack.prototype, {
    display_modes: ["Heatmap"],

    build_config_params: function () {
        return _.union(Drawable.prototype.config_params, [
            {
                key: "pos_color",
                label: "Positive Color",
                type: "color",
                default_value: "#FF8C00",
            },
            {
                key: "neg_color",
                label: "Negative Color",
                type: "color",
                default_value: "#4169E1",
            },
            {
                key: "min_value",
                label: "Min Value",
                type: "int",
                default_value: undefined,
            },
            {
                key: "max_value",
                label: "Max Value",
                type: "int",
                default_value: undefined,
            },
            {
                key: "mode",
                type: "string",
                default_value: this.mode,
                hidden: true,
            },
            {
                key: "height",
                type: "int",
                default_value: 500,
                hidden: true,
            },
        ]);
    },

    config_onchange: function () {
        this.set_name(this.config.get_value("name"));
        this.request_draw({ clear_tile_cache: true });
    },

    /**
     * Additional initialization required before drawing track for the first time.
     */
    predraw_init: function () {
        var track = this;
        return $.getJSON(
            track.dataset.url(),
            {
                data_type: "data",
                stats: true,
                chrom: track.view.chrom,
                low: 0,
                high: track.view.max_high,
                hda_ldda: track.dataset.get("hda_ldda"),
            },
            (result) => {
                // What does this do?  Is it meant to be attached to some higher scope state object?
                // var data = result.data;
            }
        );
    },

    /**
     * Draw tile.
     */
    draw_tile: function (result, ctx, mode, region, w_scale) {
        // Paint onto canvas.
        var canvas = ctx.canvas;

        var painter = new painters.DiagonalHeatmapPainter(
            result.data,
            region.get("start"),
            region.get("end"),
            this.config.to_key_value_dict(),
            mode
        );

        painter.draw(ctx, canvas.width, canvas.height, w_scale);

        return new Tile(this, region, w_scale, canvas, result.data);
    },
});

/**
 * A track that displays features/regions. Track expects position data in BED format, i.e. 0-based, half-open.
 */
var FeatureTrack = function (view, container, obj_dict) {
    TiledTrack.call(this, view, container, obj_dict);
    this.container_div.addClass("feature-track");
    this.summary_draw_height = 30;
    this.slotters = {};
    this.start_end_dct = {};
    this.left_offset = 200;
    this.set_painter_from_config();
};

extend(FeatureTrack.prototype, Drawable.prototype, TiledTrack.prototype, {
    display_modes: ["Auto", "Coverage", "Dense", "Squish", "Pack"],

    build_config_params: function () {
        return _.union(Drawable.prototype.config_params, [
            {
                key: "block_color",
                label: "Block color",
                type: "color",
            },
            {
                key: "reverse_strand_color",
                label: "Antisense strand color",
                type: "color",
            },
            {
                key: "label_color",
                label: "Label color",
                type: "color",
                default_value: "black",
            },
            {
                key: "show_counts",
                label: "Show summary counts",
                type: "bool",
                default_value: true,
                help: "Show the number of items in each bin when drawing summary histogram",
            },
            {
                key: "min_value",
                label: "Histogram minimum",
                type: "float",
                default_value: undefined,
                help: "clear value to set automatically",
            },
            {
                key: "max_value",
                label: "Histogram maximum",
                type: "float",
                default_value: undefined,
                help: "clear value to set automatically",
            },
            {
                key: "connector_style",
                label: "Connector style",
                type: "select",
                default_value: "fishbones",
                options: [
                    {
                        label: "Line with arrows",
                        value: "fishbone",
                    },
                    { label: "Arcs", value: "arcs" },
                ],
            },
            {
                key: "mode",
                type: "string",
                default_value: this.mode,
                hidden: true,
            },
            {
                key: "height",
                type: "int",
                default_value: 0,
                hidden: true,
            },
        ]);
    },

    config_onchange: function () {
        this.set_name(this.config.get_value("name"));
        this.set_painter_from_config();
        this.request_draw({ clear_tile_cache: true });
    },

    set_painter_from_config: function () {
        if (this.config.get_value("connector_style") === "arcs") {
            this.painter = painters.ArcLinkedFeaturePainter;
        } else {
            this.painter = painters.LinkedFeaturePainter;
        }
    },

    /**
     * Actions to be taken after draw has been completed. Draw is completed when all tiles have been
     * drawn/fetched and shown.
     */
    postdraw_actions: function (tiles, width, w_scale, clear_after) {
        TiledTrack.prototype.postdraw_actions.call(this, tiles, width, w_scale, clear_after);

        var line_track_tiles = _.filter(tiles, (t) => t instanceof LineTrackTile);

        //
        // Finish drawing of features that span multiple tiles. Features that span multiple tiles
        // are labeled incomplete on the tile level because they cannot be completely drawn.
        //
        if (line_track_tiles.length === 0) {
            // Gather incomplete features together.
            var all_incomplete_features = {};
            _.each(_.pluck(tiles, "incomplete_features"), (inc_features) => {
                _.each(inc_features, (feature) => {
                    all_incomplete_features[feature[0]] = feature;
                });
            });

            // Draw incomplete features on each tile.
            _.each(tiles, (tile) => {
                // Remove features already drawn on tile originally.
                var tile_incomplete_features = _.omit(
                    all_incomplete_features,
                    _.map(tile.incomplete_features, (f) => f[0])
                );

                // Remove features already drawn on tile in past postdraw actions.
                tile_incomplete_features = _.omit(tile_incomplete_features, _.keys(tile.other_tiles_features_drawn));

                // Draw tile's incomplete features.
                if (_.size(tile_incomplete_features) !== 0) {
                    // To draw incomplete features, create new canvas, copy original canvas/tile onto new
                    // canvas, and then draw incomplete features on the new canvas.
                    var features = {
                        data: _.values(tile_incomplete_features),
                    };

                    var new_canvas = this.view.canvas_manager.new_canvas();
                    var new_canvas_ctx = new_canvas.getContext("2d");
                    new_canvas.height = Math.max(
                        tile.canvas.height,
                        this.get_canvas_height(features, tile.mode, tile.w_scale, 100)
                    );
                    new_canvas.width = tile.canvas.width;
                    new_canvas_ctx.drawImage(tile.canvas, 0, 0);
                    new_canvas_ctx.translate(this.left_offset, 0);
                    var new_tile = this.draw_tile(
                        features,
                        new_canvas_ctx,
                        tile.mode,
                        tile.region,
                        tile.w_scale,
                        tile.seq_data
                    );
                    $(tile.canvas).replaceWith($(new_tile.canvas));
                    tile.canvas = new_canvas;
                    _.extend(tile.other_tiles_features_drawn, all_incomplete_features);
                }
            });
        }

        // If mode is Coverage and tiles do not share max, redraw tiles as necessary using new max.
        /*
        This code isn't used right now because Coverage mode uses predefined max in preferences.
        if (track.mode === "Coverage") {
            // Get global max.
            var global_max = -1;
            for (i = 0; i < tiles.length; i++) {
                var cur_max = tiles[i].max_val;
                if (cur_max > global_max) {
                    global_max = cur_max;
                }
            }

            for (i = 0; i < tiles.length; i++) {
                var tile = tiles[i];
                if (tile.max_val !== global_max) {
                    tile.html_elt.remove();
                    track.draw_helper(tile.index, w_scale, { more_tile_data: { force: true, max: global_max } } );
                }
            }
        }
        */

        //
        // Update filter attributes, UI.
        //

        // Update filtering UI.
        if (this.filters_manager) {
            var filters = this.filters_manager.filters;
            var f;
            for (f = 0; f < filters.length; f++) {
                filters[f].update_ui_elt();
            }

            // Determine if filters are available; this is based on the tiles' data.
            // Criteria for filter to be available: (a) it is applicable to tile data and (b) filter min != filter max.
            var filters_available = false;

            var example_feature;
            var filter;
            for (let i = 0; i < tiles.length; i++) {
                if (tiles[i].data.length) {
                    example_feature = tiles[i].data[0];
                    for (f = 0; f < filters.length; f++) {
                        filter = filters[f];
                        if (filter.applies_to(example_feature) && filter.min !== filter.max) {
                            filters_available = true;
                            break;
                        }
                    }
                }
            }

            // If filter availability changed, hide filter div if necessary and update menu.
            if (this.filters_available !== filters_available) {
                this.filters_available = filters_available;
                if (!this.filters_available) {
                    this.filters_manager.hide();
                }
                this.update_icons();
            }
        }

        //
        // If not all features slotted, show icon for showing more rows (slots).
        //
        if (tiles[0] instanceof FeatureTrackTile) {
            var all_slotted = true;
            for (let i = 0; i < tiles.length; i++) {
                if (!tiles[i].all_slotted) {
                    all_slotted = false;
                    break;
                }
            }
            this.action_icons.show_more_rows_icon.toggle(!all_slotted);
        } else {
            this.action_icons.show_more_rows_icon.hide();
        }
    },

    /**
     * Update track interface to show display mode being used.
     */
    update_auto_mode: function (mode) {
        if (this.mode === "Auto") {
            if (mode === "no_detail") {
                mode = "feature spans";
            }
            this.action_icons.mode_icon.attr("title", `Set display mode (now: Auto/${mode})`);
        }
    },

    /**
     * Place features in slots for drawing (i.e. pack features).
     * this.slotters[level] is created in this method. this.slotters[level]
     * is a Slotter object. Returns the number of slots used to pack features.
     */
    incremental_slots: function (level, features, mode) {
        // Get/create incremental slots for level. If display mode changed,
        // need to create new slots.

        var dummy_context = this.view.canvas_manager.dummy_context;

        var slotter = this.slotters[level];
        if (!slotter || slotter.mode !== mode) {
            slotter = new slotting.FeatureSlotter(level, mode, MAX_FEATURE_DEPTH, (x) => dummy_context.measureText(x));
            this.slotters[level] = slotter;
        }

        return slotter.slot_features(features);
    },

    /**
     * Returns appropriate display mode based on data.
     */
    get_mode: function (data) {
        var mode;
        // HACK: use no_detail mode track is in overview to prevent overview from being too large.
        if (data.extra_info === "no_detail" || this.is_overview) {
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
            //var data = result.data;
            // if ( (data.length && data.length < 4) ||
            //      (this.view.high - this.view.low > MIN_SQUISH_VIEW_WIDTH) ) {
            if (this.view.high - this.view.low > MIN_SQUISH_VIEW_WIDTH) {
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
    get_canvas_height: function (result, mode, w_scale, canvas_width) {
        if (mode === "Coverage" || result.dataset_type === "bigwig") {
            return this.summary_draw_height;
        } else {
            // All other modes require slotting.
            var rows_required = this.incremental_slots(w_scale, result.data, mode);
            // HACK: use dummy painter to get required height. Painter should be extended so that get_required_height
            // works as a static function.
            var dummy_painter = new this.painter(null, null, null, this.config.to_key_value_dict(), mode);
            return Math.max(this.min_height_px, dummy_painter.get_required_height(rows_required, canvas_width));
        }
    },

    /**
     * Draw FeatureTrack tile.
     * @param result result from server
     * @param cxt canvas context to draw on
     * @param mode mode to draw in
     * @param region region to draw on tile
     * @param w_scale pixels per base
     * @param ref_seq reference sequence data
     * @param cur_tile true if drawing is occurring on a currently visible tile.
     */
    draw_tile: function (result, ctx, mode, region, w_scale, ref_seq, cur_tile) {
        var track = this;
        var canvas = ctx.canvas;
        var tile_low = region.get("start");
        var tile_high = region.get("end");
        var left_offset = this.left_offset;

        // If data is line track data, draw line track tile.
        if (result.dataset_type === "bigwig") {
            return this._draw_line_track_tile(result, ctx, mode, region, w_scale);
        }

        // Handle row-by-row tracks

        // Preprocessing: filter features and determine whether all unfiltered features have been slotted.
        var filtered = [];

        var slots = this.slotters[w_scale].slots;
        var all_slotted = true;
        if (result.data) {
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
                    if (!(feature[0] in slots)) {
                        all_slotted = false;
                    }
                }
            }
        }

        // Create painter.
        var filter_alpha_scaler = this.filters_manager.alpha_filter
            ? new FilterScaler(this.filters_manager.alpha_filter)
            : null;

        var filter_height_scaler = this.filters_manager.height_filter
            ? new FilterScaler(this.filters_manager.height_filter)
            : null;

        var painter = new this.painter(
            filtered,
            tile_low,
            tile_high,
            this.config.to_key_value_dict(),
            mode,
            filter_alpha_scaler,
            filter_height_scaler,
            // HACK: ref_seq only be defined for ReadTracks, and only the ReadPainter accepts that argument
            ref_seq,
            (b) => track.view.get_base_color(b)
        );

        var feature_mapper = null;
        var incomplete_features = null;

        ctx.fillStyle = this.config.get_value("block_color");
        ctx.font = ctx.canvas.manager.default_font;
        ctx.textAlign = "right";

        if (result.data) {
            // Draw features.
            var draw_results = painter.draw(ctx, canvas.width, canvas.height, w_scale, slots);
            feature_mapper = draw_results.feature_mapper;
            incomplete_features = draw_results.incomplete_features;
            feature_mapper.translation = -left_offset;
        }

        // If not drawing on current tile, create new tile.
        if (!cur_tile) {
            return new FeatureTrackTile(
                track,
                region,
                w_scale,
                canvas,
                result.data,
                mode,
                result.message,
                all_slotted,
                feature_mapper,
                incomplete_features,
                ref_seq
            );
        }
    },
});

/**
 * Displays variant data.
 */
var VariantTrack = function (view, container, obj_dict) {
    TiledTrack.call(this, view, container, obj_dict);
    this.painter = painters.VariantPainter;
    this.summary_draw_height = 30;

    // Maximum resolution is ~45 pixels/base, so use this size left offset to ensure that full
    // variant is drawn when variant is at start of tile.
    this.left_offset = 30;
};

extend(VariantTrack.prototype, Drawable.prototype, TiledTrack.prototype, {
    display_modes: ["Auto", "Coverage", "Dense", "Squish", "Pack"],

    build_config_params: function () {
        return _.union(Drawable.prototype.config_params, [
            {
                key: "color",
                label: "Histogram color",
                type: "color",
            },
            {
                key: "show_sample_data",
                label: "Show sample data",
                type: "bool",
                default_value: true,
            },
            {
                key: "show_labels",
                label: "Show summary and sample labels",
                type: "bool",
                default_value: true,
            },
            {
                key: "summary_height",
                label: "Locus summary height",
                type: "float",
                default_value: 20,
            },
            {
                key: "mode",
                type: "string",
                default_value: this.mode,
                hidden: true,
            },
            {
                key: "height",
                type: "int",
                default_value: 0,
                hidden: true,
            },
        ]);
    },

    config_onchange: function () {
        this.set_name(this.config.get_value("name"));
        this.request_draw({ clear_tile_cache: true });
    },

    /**
     * Draw tile.
     */
    draw_tile: function (result, ctx, mode, region, w_scale) {
        // Data could be coverage data or variant data.
        if (result.dataset_type === "bigwig") {
            return this._draw_line_track_tile(result, ctx, "Histogram", region, w_scale);
        } else {
            // result.dataset_type === 'variant'
            var view = this.view;

            var painter = new this.painter(
                result.data,
                region.get("start"),
                region.get("end"),
                this.config.to_key_value_dict(),
                mode,
                (b) => view.get_base_color(b)
            );

            painter.draw(ctx, ctx.canvas.width, ctx.canvas.height, w_scale);
            return new Tile(this, region, w_scale, ctx.canvas, result.data);
        }
    },

    /**
     * Returns canvas height needed to display data; return value is an integer that denotes the
     * number of pixels required.
     */
    get_canvas_height: function (result, mode, w_scale, canvas_width) {
        if (result.dataset_type === "bigwig") {
            return this.summary_draw_height;
        } else {
            // HACK: sample_names is not be defined when dataset definition is fetched before
            // dataset is complete (as is done when running tools). In that case, fall back on
            // # of samples in data. This can be fixed by re-requesting dataset definition
            // in init.
            var num_samples = this.dataset.get_metadata("sample_names")
                ? this.dataset.get_metadata("sample_names").length
                : 0;
            if (num_samples === 0 && result.data.length !== 0) {
                // Sample data is separated by commas, so this computes # of samples:
                num_samples = result.data[0][7].match(/,/g);
                if (num_samples === null) {
                    num_samples = 1;
                } else {
                    num_samples = num_samples.length + 1;
                }
            }

            var dummy_painter = new this.painter(null, null, null, this.config.to_key_value_dict(), mode);
            return dummy_painter.get_required_height(num_samples);
        }
    },

    /**
     * Additional initialization required before drawing track for the first time.
     */
    predraw_init: function () {
        var deferreds = [Track.prototype.predraw_init.call(this)];
        // FIXME: updating dataset metadata is only needed for visual analysis. Can
        // this be moved somewhere else?
        if (!this.dataset.get_metadata("sample_names")) {
            deferreds.push(this.dataset.fetch());
        }
        return deferreds;
    },

    /**
     * Actions to be taken after draw has been completed. Draw is completed when all tiles have been
     * drawn/fetched and shown.
     */
    postdraw_actions: function (tiles, width, w_scale, clear_after) {
        TiledTrack.prototype.postdraw_actions.call(this, tiles, width, w_scale, clear_after);

        var line_track_tiles = _.filter(tiles, (t) => t instanceof LineTrackTile);

        // Add summary/sample labels if needed and not already included.
        var sample_names = this.dataset.get_metadata("sample_names");
        if (
            line_track_tiles.length === 0 &&
            this.config.get_value("show_labels") &&
            sample_names &&
            sample_names.length > 1
        ) {
            var font_size;

            // Add and/or style labels.
            if (this.container_div.find(".yaxislabel.variant").length === 0) {
                // Add summary and sample labels.

                // Add summary label to middle of summary area.
                font_size = this.config.get_value("summary_height") / 2;
                this.tiles_div.prepend(
                    $("<div/>")
                        .text("Summary")
                        .addClass("yaxislabel variant top")
                        .css({
                            "font-size": `${font_size}px`,
                            top: `${(this.config.get_value("summary_height") - font_size) / 2}px`,
                        })
                );

                // Show sample labels.
                if (this.config.get_value("show_sample_data")) {
                    var samples_div_html = sample_names.join("<br/>");

                    this.tiles_div.prepend(
                        $("<div/>")
                            .html(samples_div_html)
                            .addClass("yaxislabel variant top sample")
                            .css({
                                top: this.config.get_value("summary_height"),
                            })
                    );
                }
            }

            // Style labels.

            // Match sample font size to mode.
            font_size = `${this.mode === "Squish" ? 5 : 10}px`;
            $(this.tiles_div).find(".sample").css({
                "font-size": font_size,
                "line-height": font_size,
            });
            // Color labels to preference color.
            $(this.tiles_div).find(".yaxislabel").css("color", this.config.get_value("label_color"));
        } else {
            // Remove all labels.
            this.container_div.find(".yaxislabel.variant").remove();
        }
    },
});

/**
 * Track that displays mapped reads. Track expects position data in 1-based, closed format, i.e. SAM/BAM format.
 */
var ReadTrack = function (view, container, obj_dict) {
    FeatureTrack.call(this, view, container, obj_dict);
    this.painter = painters.ReadPainter;
    this.update_icons();
};

extend(ReadTrack.prototype, Drawable.prototype, TiledTrack.prototype, FeatureTrack.prototype, {
    build_config_params: function () {
        return _.union(Drawable.prototype.config_params, [
            {
                key: "block_color",
                label: "Histogram color",
                type: "color",
            },
            {
                key: "detail_block_color",
                label: "Sense strand block color",
                type: "color",
                default_value: "#AAAAAA",
            },
            {
                key: "reverse_strand_color",
                label: "Antisense strand block color",
                type: "color",
                default_value: "#DDDDDD",
            },
            {
                key: "label_color",
                label: "Label color",
                type: "color",
                default_value: "black",
            },
            {
                key: "show_insertions",
                label: "Show insertions",
                type: "bool",
                default_value: false,
            },
            {
                key: "show_differences",
                label: "Show differences only",
                type: "bool",
                default_value: true,
            },
            {
                key: "show_counts",
                label: "Show summary counts",
                type: "bool",
                default_value: true,
            },
            {
                key: "mode",
                type: "string",
                default_value: this.mode,
                hidden: true,
            },
            {
                key: "min_value",
                label: "Histogram minimum",
                type: "float",
                default_value: undefined,
                help: "clear value to set automatically",
            },
            {
                key: "max_value",
                label: "Histogram maximum",
                type: "float",
                default_value: undefined,
                help: "clear value to set automatically",
            },
            {
                key: "height",
                type: "int",
                default_value: 0,
                hidden: true,
            },
        ]);
    },

    config_onchange: function () {
        this.set_name(this.config.get_value("name"));
        this.request_draw({ clear_tile_cache: true });
    },
});

/**
 * Objects that can be added to a view.
 */
var addable_objects = {
    CompositeTrack: CompositeTrack,
    DrawableGroup: DrawableGroup,
    DiagonalHeatmapTrack: DiagonalHeatmapTrack,
    FeatureTrack: FeatureTrack,
    LineTrack: LineTrack,
    ReadTrack: ReadTrack,
    VariantTrack: VariantTrack,
    // For backward compatibility, map vcf track to variant.
    VcfTrack: VariantTrack,
};

/**
 * Create new object from a template. A template can be either an object dictionary or an
 * object itself.
 */
var object_from_template = (template, view, container) => {
    if ("copy" in template) {
        // Template is an object.
        return template.copy(container);
    } else {
        // Template is a dictionary.
        var drawable_type = template.obj_type;
        // For backward compatibility:
        if (!drawable_type) {
            drawable_type = template.track_type;
        }
        return new addable_objects[drawable_type](view, container, template);
    }
};

export default {
    TracksterView: TracksterView,
    DrawableGroup: DrawableGroup,
    LineTrack: LineTrack,
    FeatureTrack: FeatureTrack,
    DiagonalHeatmapTrack: DiagonalHeatmapTrack,
    ReadTrack: ReadTrack,
    VariantTrack: VariantTrack,
    CompositeTrack: CompositeTrack,
    object_from_template: object_from_template,
};
