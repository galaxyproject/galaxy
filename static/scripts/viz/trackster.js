define("viz/trackster", ["exports", "utils/localization", "libs/underscore", "viz/trackster/tracks", "viz/visualization", "mvc/ui/icon-button", "utils/query-string-parsing", "mvc/grid/grid-view", "utils/utils", "libs/jquery/jquery.event.drag", "libs/jquery/jquery.event.hover", "libs/jquery/jquery.mousewheel", "libs/jquery/jquery-ui", "libs/jquery/select2", "libs/farbtastic", "libs/jquery/jquery.form", "libs/jquery/jquery.rating", "ui/editable-text"], function(exports, _localization, _underscore, _tracks, _visualization, _iconButton, _queryStringParsing, _gridView, _utils) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _ = _interopRequireWildcard(_underscore);

    var _tracks2 = _interopRequireDefault(_tracks);

    var _visualization2 = _interopRequireDefault(_visualization);

    var _iconButton2 = _interopRequireDefault(_iconButton);

    var _queryStringParsing2 = _interopRequireDefault(_queryStringParsing);

    var _gridView2 = _interopRequireDefault(_gridView);

    var _utils2 = _interopRequireDefault(_utils);

    function _interopRequireWildcard(obj) {
        if (obj && obj.__esModule) {
            return obj;
        } else {
            var newObj = {};

            if (obj != null) {
                for (var key in obj) {
                    if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key];
                }
            }

            newObj.default = obj;
            return newObj;
        }
    }

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /**
     * Top-level trackster code, used for creating/loading visualizations and user interface elements.
     */

    // global variables
    var ui = null;
    var view = null;
    var browser_router = null;

    // trackster viewer

    /**
     * Base Object/Model for inhertiance.
     */
    var Base = function Base() {
        if (this.initialize) {
            this.initialize.apply(this, arguments);
        }
    };
    Base.extend = Backbone.Model.extend;

    /**
     * User interface controls for trackster
     */
    var TracksterUI = Base.extend({
        initialize: function initialize(baseURL) {
            _utils2.default.cssLoadFile("static/style/jquery.rating.css");
            _utils2.default.cssLoadFile("static/style/autocomplete_tagging.css");
            _utils2.default.cssLoadFile("static/style/jquery-ui/smoothness/jquery-ui.css");
            _utils2.default.cssLoadFile("static/style/library.css");
            _utils2.default.cssLoadFile("static/style/trackster.css");
            this.baseURL = baseURL;
        },

        /**
         * Save visualization, returning a Deferred object for the remote call to save.
         */
        save_viz: function save_viz() {
            // show dialog
            Galaxy.modal.show({
                title: "Saving...",
                body: "progress"
            });

            // Save bookmarks.
            var bookmarks = [];
            $(".bookmark").each(function() {
                bookmarks.push({
                    position: $(this).children(".position").text(),
                    annotation: $(this).children(".annotation").text()
                });
            });

            // FIXME: give unique IDs to Drawables and save overview as ID.
            var overview_track_name = view.overview_drawable ? view.overview_drawable.config.get_value("name") : null;

            var viz_config = {
                view: view.to_dict(),
                viewport: {
                    chrom: view.chrom,
                    start: view.low,
                    end: view.high,
                    overview: overview_track_name
                },
                bookmarks: bookmarks
            };

            // Make call to save visualization.
            return $.ajax({
                url: Galaxy.root + "visualization/save",
                type: "POST",
                dataType: "json",
                data: {
                    id: view.vis_id,
                    title: view.config.get_value("name"),
                    dbkey: view.dbkey,
                    type: "trackster",
                    vis_json: JSON.stringify(viz_config)
                }
            }).success(function(vis_info) {
                Galaxy.modal.hide();
                view.vis_id = vis_info.vis_id;
                view.has_changes = false;

                // Needed to set URL when first saving a visualization.
                window.history.pushState({}, "", vis_info.url + window.location.hash);
            }).error(function() {
                // show dialog
                Galaxy.modal.show({
                    title: (0, _localization2.default)("Could Not Save"),
                    body: "Could not save visualization. Please try again later.",
                    buttons: {
                        Cancel: function Cancel() {
                            Galaxy.modal.hide();
                        }
                    }
                });
            });
        },

        /**
         * Create button menu
         */
        createButtonMenu: function createButtonMenu() {
            var self = this;

            var menu = _iconButton2.default.create_icon_buttons_menu([{
                icon_class: "plus-button",
                title: (0, _localization2.default)("Add tracks"),
                on_click: function on_click() {
                    _visualization2.default.select_datasets({
                        dbkey: view.dbkey
                    }, function(new_tracks) {
                        _.each(new_tracks, function(track) {
                            view.add_drawable(_tracks2.default.object_from_template(track, view, view));
                        });
                    });
                }
            }, {
                icon_class: "block--plus",
                title: (0, _localization2.default)("Add group"),
                on_click: function on_click() {
                    view.add_drawable(new _tracks2.default.DrawableGroup(view, view, {
                        name: "New Group"
                    }));
                }
            }, {
                icon_class: "bookmarks",
                title: (0, _localization2.default)("Bookmarks"),
                on_click: function on_click() {
                    // HACK -- use style to determine if panel is hidden and hide/show accordingly.
                    force_right_panel($("div#right").css("right") == "0px" ? "hide" : "show");
                }
            }, {
                icon_class: "globe",
                title: (0, _localization2.default)("Circster"),
                on_click: function on_click() {
                    window.location = self.baseURL + "visualization/circster?id=" + view.vis_id;
                }
            }, {
                icon_class: "disk--arrow",
                title: (0, _localization2.default)("Save"),
                on_click: function on_click() {
                    self.save_viz();
                }
            }, {
                icon_class: "cross-circle",
                title: (0, _localization2.default)("Close"),
                on_click: function on_click() {
                    self.handle_unsaved_changes(view);
                }
            }], {
                tooltip_config: {
                    placement: "bottom"
                }
            });

            this.buttonMenu = menu;
            return menu;
        },

        /**
         * Add bookmark.
         */
        add_bookmark: function add_bookmark(position, annotation, editable) {
            // Create HTML.
            var bookmarks_container = $("#right .unified-panel-body");

            var new_bookmark = $("<div/>").addClass("bookmark").appendTo(bookmarks_container);

            var position_div = $("<div/>").addClass("position").appendTo(new_bookmark);

            var position_link = $("<a href=''/>").text(position).appendTo(position_div).click(function() {
                view.go_to(position);
                return false;
            });

            var annotation_div = $("<div/>").text(annotation).appendTo(new_bookmark);

            // If editable, enable bookmark deletion and annotation editing.
            if (editable) {
                var delete_icon_container = $("<div/>").addClass("delete-icon-container").prependTo(new_bookmark).click(function() {
                    // Remove bookmark.
                    new_bookmark.slideUp("fast");
                    new_bookmark.remove();
                    view.has_changes = true;
                    return false;
                });

                var delete_icon = $("<a href=''/>").addClass("icon-button delete").appendTo(delete_icon_container);

                annotation_div.make_text_editable({
                    num_rows: 3,
                    use_textarea: true,
                    help_text: "Edit bookmark note"
                }).addClass("annotation");
            }

            view.has_changes = true;
            return new_bookmark;
        },

        /**
         * Create a complete Trackster visualization. Returns view.
         */
        create_visualization: function create_visualization(view_config, viewport_config, drawables_config, bookmarks_config, editable) {
            // Create view.
            var self = this;

            var view = new _tracks2.default.TracksterView(_.extend(view_config, {
                header: false
            }));

            view.editor = true;
            $.when(view.load_chroms_deferred).then(function(chrom_info) {
                // Viewport config.
                if (viewport_config) {
                    var chrom = viewport_config.chrom;
                    var start = viewport_config.start;
                    var end = viewport_config.end;
                    var overview_drawable_name = viewport_config.overview;

                    if (chrom && start !== undefined && end) {
                        view.change_chrom(chrom, start, end);
                    } else {
                        // No valid viewport, so use first chromosome.
                        view.change_chrom(chrom_info[0].chrom);
                    }
                } else {
                    // No viewport, so use first chromosome.
                    view.change_chrom(chrom_info[0].chrom);
                }

                // Add drawables to view.
                if (drawables_config) {
                    // FIXME: can from_dict() be used to create view and add drawables?
                    var drawable_config;

                    var drawable_type;
                    var drawable;
                    for (var i = 0; i < drawables_config.length; i++) {
                        view.add_drawable(_tracks2.default.object_from_template(drawables_config[i], view, view));
                    }
                }

                // Set overview.
                var overview_drawable;
                for (var i = 0; i < view.drawables.length; i++) {
                    if (view.drawables[i].config.get_value("name") === overview_drawable_name) {
                        view.set_overview(view.drawables[i]);
                        break;
                    }
                }

                // Load bookmarks.
                if (bookmarks_config) {
                    var bookmark;
                    for (var i = 0; i < bookmarks_config.length; i++) {
                        bookmark = bookmarks_config[i];
                        self.add_bookmark(bookmark["position"], bookmark["annotation"], editable);
                    }
                }

                // View has no changes as of yet.
                view.has_changes = false;
            });

            // Final initialization.
            this.set_up_router({
                view: view
            });

            return view;
        },

        /**
         * Set up location router to use hashes as track browser locations.
         */
        set_up_router: function set_up_router(options) {
            new _visualization2.default.TrackBrowserRouter(options);
            Backbone.history.start();
        },

        /**
         * Set up keyboard navigation for a visualization.
         */
        init_keyboard_nav: function init_keyboard_nav(view) {
            // Keyboard navigation. Scroll ~7% of height when scrolling up/down.
            $(document).keyup(function(e) {
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
                        var change = Math.round(view.viewport_container.height() / 15.0);
                        view.viewport_container.scrollTop(view.viewport_container.scrollTop() - 20);
                        break;
                    case 39:
                        view.move_fraction(-0.25);
                        break;
                    case 40:
                        var change = Math.round(view.viewport_container.height() / 15.0);
                        view.viewport_container.scrollTop(view.viewport_container.scrollTop() + 20);
                        break;
                }
            });
        },

        /**
         * Handle unsaved changes in visualization.
         */
        handle_unsaved_changes: function handle_unsaved_changes(view) {
            if (view.has_changes) {
                var self = this;
                Galaxy.modal.show({
                    title: (0, _localization2.default)("Close visualization"),
                    body: "There are unsaved changes to your visualization which will be lost if you do not save them.",
                    buttons: {
                        Cancel: function Cancel() {
                            Galaxy.modal.hide();
                        },
                        "Leave without Saving": function LeaveWithoutSaving() {
                            $(window).off("beforeunload");
                            window.location = Galaxy.root + "visualization";
                        },
                        Save: function Save() {
                            $.when(self.save_viz()).then(function() {
                                window.location = Galaxy.root + "visualization";
                            });
                        }
                    }
                });
            } else {
                window.location = Galaxy.root + "visualization";
            }
        }
    });

    var TracksterView = Backbone.View.extend({
        // initalize trackster
        initialize: function initialize() {
            // load ui
            ui = new TracksterUI(Galaxy.root);

            // create button menu
            ui.createButtonMenu();

            // attach the button menu to the panel header and float it left
            ui.buttonMenu.$el.attr("style", "float: right");

            // add to center panel
            $("#center .unified-panel-header-inner").append(ui.buttonMenu.$el);

            // configure right panel
            $("#right .unified-panel-title").append("Bookmarks");
            $("#right .unified-panel-icons").append("<a id='add-bookmark-button' class='icon-button menu-button plus-button' href='javascript:void(0);' title='Add bookmark'></a>");

            // resize view when showing/hiding right panel (bookmarks for now).
            $("#right-border").click(function() {
                view.resize_window();
            });

            // hide right panel
            force_right_panel("hide");

            // check if id is available
            if (galaxy_config.app.id) {
                this.view_existing();
            } else if (_queryStringParsing2.default.get("dataset_id")) {
                this.choose_existing_or_new();
            } else {
                this.view_new();
            }
        },

        choose_existing_or_new: function choose_existing_or_new() {
            var self = this;
            var dbkey = _queryStringParsing2.default.get("dbkey");
            var listTracksParams = {};

            var dataset_params = {
                dbkey: dbkey,
                dataset_id: _queryStringParsing2.default.get("dataset_id"),
                hda_ldda: _queryStringParsing2.default.get("hda_ldda"),
                gene_region: _queryStringParsing2.default.get("gene_region")
            };

            if (dbkey) {
                listTracksParams["f-dbkey"] = dbkey;
            }

            Galaxy.modal.show({
                title: "View Data in a New or Saved Visualization?",
                // either have text in here or have to remove body and the header/footer margins
                body: "<p><ul style='list-style: disc inside none'>You can add this dataset as:<li>a new track to one of your existing, saved Trackster sessions if they share the genome build: <b>" + (dbkey || "Not available.") + "</b></li><li>or create a new session with this dataset as the only track</li></ul></p>",
                buttons: {
                    Cancel: function Cancel() {
                        window.location = Galaxy.root + "visualizations/list";
                    },
                    "View in saved visualization": function ViewInSavedVisualization() {
                        self.view_in_saved(dataset_params);
                    },
                    "View in new visualization": function ViewInNewVisualization() {
                        self.view_new();
                    }
                }
            });
        },

        // view
        view_in_saved: function view_in_saved(dataset_params) {
            var tracks_grid = new _gridView2.default({
                url_base: Galaxy.root + "visualization/list_tracks",
                dict_format: true,
                embedded: true
            });
            Galaxy.modal.show({
                title: (0, _localization2.default)("Add Data to Saved Visualization"),
                body: tracks_grid.$el,
                buttons: {
                    Cancel: function Cancel() {
                        window.location = Galaxy.root + "visualizations/list";
                    },
                    "Add to visualization": function AddToVisualization() {
                        $(parent.document).find("input[name=id]:checked").each(function() {
                            dataset_params.id = $(this).val();
                            window.location = Galaxy.root + "visualization/trackster?" + $.param(dataset_params);
                        });
                    }
                }
            });
        },

        // view
        view_existing: function view_existing() {
            // get config
            var viz_config = galaxy_config.app.viz_config;

            // view
            view = ui.create_visualization({
                container: $("#center .unified-panel-body"),
                name: viz_config.title,
                vis_id: viz_config.vis_id,
                dbkey: viz_config.dbkey
            }, viz_config.viewport, viz_config.tracks, viz_config.bookmarks, true);

            // initialize editor
            this.init_editor();
        },

        // view
        view_new: function view_new() {
            // reference this
            var self = this;

            // ajax
            $.ajax({
                url: Galaxy.root + "api/genomes?chrom_info=True",
                data: {},
                error: function error() {
                    alert("Couldn't create new browser.");
                },
                success: function success(response) {
                    // show dialog
                    Galaxy.modal.show({
                        title: (0, _localization2.default)("New Visualization"),
                        body: self.template_view_new(response),
                        buttons: {
                            Cancel: function Cancel() {
                                window.location = Galaxy.root + "visualizations/list";
                            },
                            Create: function Create() {
                                self.create_browser($("#new-title").val(), $("#new-dbkey").val());
                                Galaxy.modal.hide();
                            }
                        }
                    });

                    // select default
                    var dbkeys_in_genomes = response.map(function(r) {
                        return r[1];
                    });
                    if (galaxy_config.app.default_dbkey && _.contains(dbkeys_in_genomes, galaxy_config.app.default_dbkey)) {
                        $("#new-dbkey").val(galaxy_config.app.default_dbkey);
                    }

                    // change focus
                    $("#new-title").focus();
                    $("select[name='dbkey']").select2();

                    // to support the large number of options for dbkey, enable scrolling in overlay.
                    $("#overlay").css("overflow", "auto");
                }
            });
        },

        // new browser form
        template_view_new: function template_view_new(response) {
            // start template
            var html = '<form id="new-browser-form" action="javascript:void(0);" method="post" onsubmit="return false;">' + '<div class="form-row">' + '<label for="new-title">Browser name:</label>' + '<div class="form-row-input">' + '<input type="text" name="title" id="new-title" value="Unnamed"></input>' + "</div>" + '<div style="clear: both;"></div>' + "</div>" + '<div class="form-row">' + '<label for="new-dbkey">Reference genome build (dbkey): </label>' + '<div class="form-row-input">' + '<select name="dbkey" id="new-dbkey">';

            // add dbkeys
            for (var i = 0; i < response.length; i++) {
                html += "<option value=\"" + response[i][1] + "\">" + response[i][0] + "</option>";
            }

            // close selection/finalize template
            html += "</select></div><div style=\"clear: both;\"></div></div><div class=\"form-row\">Is the build not listed here? <a href=\"" + Galaxy.root + "custom_builds\">Add a Custom Build</a></div></form>";

            // return
            return html;
        },

        // create
        create_browser: function create_browser(name, dbkey) {
            $(document).trigger("convert_to_values");

            view = ui.create_visualization({
                container: $("#center .unified-panel-body"),
                name: name,
                dbkey: dbkey
            }, galaxy_config.app.gene_region);

            // initialize editor
            this.init_editor();

            // modify view setting
            view.editor = true;
        },

        // initialization for editor-specific functions.
        init_editor: function init_editor() {
            // set title
            $("#center .unified-panel-title").text(view.config.get_value("name") + " (" + view.dbkey + ")");

            // add dataset
            if (galaxy_config.app.add_dataset) $.ajax({
                url: Galaxy.root + "api/datasets/" + galaxy_config.app.add_dataset,
                data: {
                    hda_ldda: "hda",
                    data_type: "track_config"
                },
                dataType: "json",
                success: function success(track_data) {
                    view.add_drawable(_tracks2.default.object_from_template(track_data, view, view));
                }
            });

            // initialize icons
            $("#add-bookmark-button").click(function() {
                // add new bookmark.
                var position = view.chrom + ":" + view.low + "-" + view.high;

                var annotation = "Bookmark description";
                return ui.add_bookmark(position, annotation, true);
            });

            // initialize keyboard
            ui.init_keyboard_nav(view);

            $(window).on("beforeunload", function() {
                if (view.has_changes) {
                    return "There are unsaved changes to your visualization that will be lost if you leave this page.";
                }
            });
        }
    });

    exports.default = {
        TracksterUI: TracksterUI,
        GalaxyApp: TracksterView
    };
});
//# sourceMappingURL=../../maps/viz/trackster.js.map
