/**
 * Top-level trackster code, used for creating/loading visualizations and user interface elements.
 */

import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import tracks from "viz/trackster/tracks";
import visualization from "viz/visualization";
import IconButton from "mvc/ui/icon-button";
import query_string from "utils/query-string-parsing";
import GridView from "mvc/grid/grid-view";
// import Utils from "utils/utils";
import "libs/jquery/jquery.event.drag";
import "libs/jquery/jquery.event.hover";
import "jquery-mousewheel";
import "libs/jquery/jquery-ui";
import "libs/jquery/select2";
import "libs/farbtastic";
import "libs/jquery/jquery.form";
import "libs/jquery/jquery.rating";
import "ui/editable-text";

//import "style/scss/autocomplete_tagging.scss";
//import "static/style/jquery-ui/smoothness/jquery-ui.css";
//import "static/style/library.css";
//import "static/style/trackster.css";

/**
 * User interface controls for trackster
 */
export class TracksterUI extends Backbone.Model {
    constructor(options) {
        super(options);
    }

    initialize(baseURL) {
        this.baseURL = baseURL;
    }

    /**
     * Save visualization, returning a Deferred object for the remote call to save.
     */
    save_viz() {
        const Galaxy = getGalaxyInstance();

        // show dialog
        Galaxy.modal.show({ title: "Saving...", body: "progress" });

        // Save bookmarks.
        var bookmarks = [];
        $(".bookmark").each(() => {
            bookmarks.push({
                position: $(this).children(".position").text(),
                annotation: $(this).children(".annotation").text(),
            });
        });

        // FIXME: give unique IDs to Drawables and save overview as ID.
        var overview_track_name = this.view.overview_drawable
            ? this.view.overview_drawable.config.get_value("name")
            : null;

        var viz_config = {
            view: this.view.to_dict(),
            viewport: {
                chrom: this.view.chrom,
                start: this.view.low,
                end: this.view.high,
                overview: overview_track_name,
            },
            bookmarks: bookmarks,
        };

        // Make call to save visualization.
        return $.ajax({
            url: `${getAppRoot()}visualization/save`,
            type: "POST",
            dataType: "json",
            data: {
                id: this.view.vis_id,
                title: this.view.config.get_value("name"),
                dbkey: this.view.dbkey,
                type: "trackster",
                vis_json: JSON.stringify(viz_config),
            },
        })
            .success((vis_info) => {
                Galaxy.modal.hide();
                this.view.vis_id = vis_info.vis_id;
                this.view.has_changes = false;

                // Needed to set URL when first saving a visualization.
                window.history.pushState({}, "", vis_info.url + window.top.location.hash);
            })
            .error(() => {
                // show dialog
                Galaxy.modal.show({
                    title: _l("Could Not Save"),
                    body: "Could not save visualization. Please try again later.",
                    buttons: {
                        Cancel: () => {
                            Galaxy.modal.hide();
                        },
                    },
                });
            });
    }

    /**
     * Create button menu
     */
    createButtonMenu() {
        var menu = IconButton.create_icon_buttons_menu(
            [
                {
                    icon_class: "plus-button",
                    title: _l("Add tracks"),
                    on_click: () => {
                        visualization.select_datasets({ dbkey: this.view.dbkey }, (new_tracks) => {
                            _.each(new_tracks, (track) => {
                                this.view.add_drawable(tracks.object_from_template(track, this.view, this.view));
                            });
                        });
                    },
                },
                {
                    icon_class: "block--plus",
                    title: _l("Add group"),
                    on_click: () => {
                        this.view.add_drawable(
                            new tracks.DrawableGroup(this.view, this.view, {
                                name: "New Group",
                            })
                        );
                    },
                },
                {
                    icon_class: "bookmarks",
                    title: _l("Bookmarks"),
                    on_click: () => {
                        // HACK -- use style to determine if panel is hidden and hide/show accordingly.
                        window.force_right_panel($("div#right").css("right") == "0px" ? "hide" : "show");
                    },
                },
                {
                    icon_class: "globe",
                    title: _l("Circster"),
                    on_click: () => {
                        const vis_id = this.view.vis_id;
                        var circster_q = "id=" + vis_id;
                        if (vis_id == undefined) {
                            circster_q = `dataset_id=${this.view.drawables[0].dataset.id}&hda_ldda=${this.view.drawables[0].dataset.attributes.hda_ldda}`;
                        }
                        window.top.location = `${this.baseURL}visualization/circster?${circster_q}`;
                    },
                },
                {
                    icon_class: "disk--arrow",
                    title: _l("Save"),
                    on_click: () => {
                        this.save_viz();
                    },
                },
                {
                    icon_class: "cross-circle",
                    title: _l("Close"),
                    on_click: () => {
                        this.handle_unsaved_changes(this.view);
                    },
                },
            ],
            {
                tooltip_config: { placement: "bottom" },
            }
        );

        this.buttonMenu = menu;
        return menu;
    }

    /**
     * Add bookmark.
     */
    add_bookmark(position, annotation, editable) {
        // Create HTML.
        var bookmarks_container = $("#right .unified-panel-body");

        var new_bookmark = $("<div/>").addClass("bookmark").appendTo(bookmarks_container);

        var position_div = $("<div/>").addClass("position").appendTo(new_bookmark);

        //position_link
        $("<a href='javascript:void(0)'/>")
            .text(position)
            .appendTo(position_div)
            .click(() => {
                this.view.go_to(position);
                return false;
            });

        var annotation_div = $("<div/>").text(annotation).appendTo(new_bookmark);

        // If editable, enable bookmark deletion and annotation editing.
        if (editable) {
            var delete_icon_container = $("<div/>")
                .addClass("delete-icon-container")
                .prependTo(new_bookmark)
                .click(() => {
                    // Remove bookmark.
                    new_bookmark.slideUp("fast");
                    new_bookmark.remove();
                    this.view.has_changes = true;
                    return false;
                });

            // delete_icon
            $("<a href='javascript:void(0)'/>").addClass("icon-button delete").appendTo(delete_icon_container);

            annotation_div
                .make_text_editable({
                    num_rows: 3,
                    use_textarea: true,
                    help_text: "Edit bookmark note",
                })
                .addClass("annotation");
        }

        this.view.has_changes = true;
        return new_bookmark;
    }

    /**
     * Create a complete Trackster visualization. Returns view.
     */
    create_visualization(view_config, viewport_config, drawables_config, bookmarks_config, editable) {
        // Create view.
        this.view = new tracks.TracksterView(_.extend(view_config, { header: false }));
        this.view.editor = true;

        $.when(this.view.load_chroms_deferred).then((chrom_info) => {
            var overview_drawable_name = null;
            // Viewport config.
            if (viewport_config) {
                var chrom = viewport_config.chrom;
                var start = viewport_config.start;
                var end = viewport_config.end;
                overview_drawable_name = viewport_config.overview;

                if (chrom && start !== undefined && end) {
                    this.view.change_chrom(chrom, start, end);
                } else {
                    // No valid viewport, so use first chromosome.
                    this.view.change_chrom(chrom_info[0].chrom);
                }
            } else {
                // No viewport, so use first chromosome.
                this.view.change_chrom(chrom_info[0].chrom);
            }

            // Add drawables to view.
            if (drawables_config) {
                // FIXME: can from_dict() be used to create view and add drawables?
                for (let i = 0; i < drawables_config.length; i++) {
                    this.view.add_drawable(tracks.object_from_template(drawables_config[i], this.view, this.view));
                }
            }

            // Set overview.
            for (let i = 0; i < this.view.drawables.length; i++) {
                if (this.view.drawables[i].config.get_value("name") === overview_drawable_name) {
                    this.view.set_overview(this.view.drawables[i]);
                    break;
                }
            }

            // Load bookmarks.
            if (bookmarks_config) {
                var bookmark;
                for (let i = 0; i < bookmarks_config.length; i++) {
                    bookmark = bookmarks_config[i];
                    this.add_bookmark(bookmark.position, bookmark.annotation, editable);
                }
            }

            // View has no changes as of yet.
            this.view.has_changes = false;
        });

        // Final initialization.
        this.set_up_router({ view: this.view });

        // TODO: This is hopefully not necessary anymore, since we're using the instance view.  Do it for compatibility for now.
        return this.view;
    }

    /**
     * Set up location router to use hashes as track browser locations.
     */
    set_up_router(options) {
        new visualization.TrackBrowserRouter(options);
        Backbone.history.start();
    }

    /**
     * Set up keyboard navigation for a visualization.
     */
    init_keyboard_nav(view) {
        // Keyboard navigation. Scroll ~7% of height when scrolling up/down.
        $(document).keyup((e) => {
            // Do not navigate if arrow keys used in input element.
            if ($(e.srcElement).is(":input")) {
                return;
            }

            // Key codes: left == 37, up == 38, right == 39, down == 40
            switch (e.which) {
                case 37:
                    view.move_fraction(0.25);
                    break;
                case 38:
                    // var change = Math.round(view.viewport_container.height() / 15.0);
                    view.viewport_container.scrollTop(view.viewport_container.scrollTop() - 20);
                    break;
                case 39:
                    view.move_fraction(-0.25);
                    break;
                case 40:
                    // var change = Math.round(view.viewport_container.height() / 15.0);
                    view.viewport_container.scrollTop(view.viewport_container.scrollTop() + 20);
                    break;
            }
        });
    }

    /**
     * Handle unsaved changes in visualization.
     */
    handle_unsaved_changes(view) {
        const Galaxy = getGalaxyInstance();
        if (view.has_changes) {
            Galaxy.modal.show({
                title: _l("Close visualization"),
                body: "There are unsaved changes to your visualization which will be lost if you do not save them.",
                buttons: {
                    Cancel: () => {
                        Galaxy.modal.hide();
                    },
                    "Leave without Saving": () => {
                        $(window).off("beforeunload");
                        window.top.location = `${getAppRoot()}visualizations/list`;
                    },
                    Save: () => {
                        $.when(this.save_viz()).then(() => {
                            window.top.location = `${getAppRoot()}visualizations/list`;
                        });
                    },
                },
            });
        } else {
            window.top.location = `${getAppRoot()}visualizations/list`;
        }
    }
}

export class TracksterUIView extends Backbone.View {
    constructor(options) {
        super(options);
    }
    // initalize trackster
    initialize() {
        // load ui
        this.ui = new TracksterUI(getAppRoot());

        // create button menu
        this.ui.createButtonMenu();

        // attach the button menu to the panel header and float it left
        this.ui.buttonMenu.$el.attr("style", "float: right");

        // add to center panel
        $("#center .unified-panel-header-inner").append(this.ui.buttonMenu.$el);

        // configure right panel
        $("#right .unified-panel-title").append("Bookmarks");
        $("#right .unified-panel-icons").append(
            "<a id='add-bookmark-button' class='icon-button menu-button plus-button' href='javascript:void(0);' title='Add bookmark'></a>"
        );

        // resize view when showing/hiding right panel (bookmarks for now).
        $("#right-border").click(() => {
            this.ui.view.resize_window();
        });

        // hide right panel
        window.force_right_panel("hide");

        // check if id is available
        if (window.galaxy_config.app.id) {
            this.view_existing();
        } else if (query_string.get("dataset_id")) {
            this.choose_existing_or_new();
        } else {
            this.view_new();
        }
    }

    choose_existing_or_new() {
        const Galaxy = getGalaxyInstance();
        var dbkey = query_string.get("dbkey");
        var listTracksParams = {};

        var dataset_params = {
            dbkey: dbkey,
            dataset_id: query_string.get("dataset_id"),
            hda_ldda: query_string.get("hda_ldda"),
            gene_region: query_string.get("gene_region"),
        };

        if (dbkey) {
            listTracksParams["f-dbkey"] = dbkey;
        }

        Galaxy.modal.show({
            title: "View Data in a New or Saved Visualization?",
            // either have text in here or have to remove body and the header/footer margins
            body: `<p><ul style='list-style: disc inside none'>You can add this dataset as:<li>a new track to one of your existing, saved Trackster sessions if they share the genome build: <b>${
                dbkey || "Not available."
            }</b></li><li>or create a new session with this dataset as the only track</li></ul></p>`,
            buttons: {
                Cancel: () => {
                    window.top.location = `${getAppRoot()}visualizations/list`;
                },
                "View in saved visualization": () => {
                    this.view_in_saved(dataset_params);
                },
                "View in new visualization": () => {
                    this.view_new();
                },
            },
        });
    }

    // view
    view_in_saved(dataset_params) {
        const Galaxy = getGalaxyInstance();
        var tracks_grid = new GridView({
            url_base: `${getAppRoot()}visualization/list_tracks`,
            embedded: true,
        });
        Galaxy.modal.show({
            title: _l("Add Data to Saved Visualization"),
            body: tracks_grid.$el,
            buttons: {
                Cancel: () => {
                    window.top.location = `${getAppRoot()}visualizations/list`;
                },
                "Add to visualization": () => {
                    $(window.parent.document)
                        .find("input[name=id]:checked")
                        .each(() => {
                            dataset_params.id = $(this).val();
                            window.top.location = `${getAppRoot()}visualization/trackster?${$.param(dataset_params)}`;
                        });
                },
            },
        });
    }

    // view
    view_existing() {
        // get config
        var viz_config = window.galaxy_config.app.viz_config;

        // view
        this.ui.create_visualization(
            {
                container: $("#center .unified-panel-body"),
                name: viz_config.title,
                vis_id: viz_config.vis_id,
                dbkey: viz_config.dbkey,
            },
            viz_config.viewport,
            viz_config.tracks,
            viz_config.bookmarks,
            true
        );

        // initialize editor
        this.init_editor();
    }

    // view
    view_new() {
        const Galaxy = getGalaxyInstance();
        // ajax
        $.ajax({
            url: `${getAppRoot()}api/genomes?chrom_info=True`,
            data: {},
            error: () => {
                alert("Couldn't create new browser.");
            },
            success: (response) => {
                // show dialog
                Galaxy.modal.show({
                    title: _l("New Visualization"),
                    body: this.template_view_new(response),
                    buttons: {
                        Cancel: () => {
                            window.top.location = `${getAppRoot()}visualizations/list`;
                        },
                        Create: () => {
                            this.create_browser($("#new-title").val(), $("#new-dbkey").val());
                            Galaxy.modal.hide();
                        },
                    },
                });

                // select default
                var dbkeys_in_genomes = response.map((r) => r[1]);
                if (
                    window.galaxy_config.app.default_dbkey &&
                    _.contains(dbkeys_in_genomes, window.galaxy_config.app.default_dbkey)
                ) {
                    $("#new-dbkey").val(window.galaxy_config.app.default_dbkey);
                }

                // change focus
                $("#new-title").focus();
                $("select[name='dbkey']").select2();

                // to support the large number of options for dbkey, enable scrolling in overlay.
                $("#overlay").css("overflow", "auto");
            },
        });
    }

    // new browser form
    template_view_new(response) {
        // start template
        var html =
            '<form id="new-browser-form" action="javascript:void(0);" method="post" onsubmit="return false;">' +
            '<div class="form-row">' +
            '<label for="new-title">Browser name:</label>' +
            '<div class="form-row-input">' +
            '<input type="text" name="title" id="new-title" value="Unnamed"></input>' +
            "</div>" +
            '<div style="clear: both;"></div>' +
            "</div>" +
            '<div class="form-row">' +
            '<label for="new-dbkey">Reference genome build (dbkey): </label>' +
            '<div class="form-row-input">' +
            '<select name="dbkey" id="new-dbkey">';

        // add dbkeys
        for (let i = 0; i < response.length; i++) {
            html += `<option value="${response[i][1]}">${response[i][0]}</option>`;
        }

        // close selection/finalize template
        html += `</select></div><div style="clear: both;"></div></div><div class="form-row">Is the build not listed here? <a href="${getAppRoot()}custom_builds" target="_top">Add a Custom Build</a></div></form>`;

        // return
        return html;
    }

    // initialization for editor-specific functions.
    init_editor() {
        // set title
        $("#center .unified-panel-title").text(`${this.ui.view.config.get_value("name")} (${this.ui.view.dbkey})`);

        // add dataset
        if (window.galaxy_config.app.add_dataset) {
            $.ajax({
                url: `${getAppRoot()}api/datasets/${window.galaxy_config.app.add_dataset}`,
                data: { hda_ldda: "hda", data_type: "track_config" },
                dataType: "json",
                success: (track_data) => {
                    this.ui.view.add_drawable(tracks.object_from_template(track_data, this.ui.view, this.ui.view));
                },
            });
        }

        // initialize icons
        $("#add-bookmark-button").click(() => {
            // add new bookmark.
            var position = `${this.ui.view.chrom}:${this.ui.view.low}-${this.ui.view.high}`;

            var annotation = "Bookmark description";
            return this.ui.add_bookmark(position, annotation, true);
        });

        // initialize keyboard
        this.ui.init_keyboard_nav(this.ui.view);

        $(window).on("beforeunload", () => {
            if (this.ui.view.has_changes) {
                return "There are unsaved changes to your visualization that will be lost if you leave this page.";
            }
        });
    }

    // create
    create_browser(name, dbkey) {
        $(document).trigger("convert_to_values");

        this.ui.create_visualization(
            {
                container: $("#center .unified-panel-body"),
                name: name,
                dbkey: dbkey,
            },
            window.galaxy_config.app.gene_region
        );

        // initialize editor
        this.init_editor();

        // modify view setting
        this.ui.view.editor = true;
    }
}
