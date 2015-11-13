/**
 * Top-level trackster code, used for creating/loading visualizations and user interface elements.
 */

// global variables
var ui              = null;
var view            = null;
var browser_router  = null;

// load required libraries
require(
[
    // load js libraries
    'utils/utils',
    'libs/jquery/jquery.event.drag',
    'libs/jquery/jquery.event.hover',
    'libs/jquery/jquery.mousewheel',
    'libs/jquery/jquery-ui',
    'libs/jquery/select2',
    'libs/farbtastic',
    'libs/jquery/jquery.form',
    'libs/jquery/jquery.rating',
    "ui/editable-text",
], function(mod_utils, mod_icon_btn)
{
    // load css
    mod_utils.cssLoadFile("static/style/jquery.rating.css");
    mod_utils.cssLoadFile("static/style/autocomplete_tagging.css");
    mod_utils.cssLoadFile("static/style/jquery-ui/smoothness/jquery-ui.css");
    mod_utils.cssLoadFile("static/style/library.css");
    mod_utils.cssLoadFile("static/style/trackster.css");
});

// trackster viewer
define([
    "libs/underscore",
    "viz/trackster/tracks",
    "viz/visualization",
    "mvc/ui/icon-button",
    "utils/query-string-parsing"
], function(_, tracks, visualization, mod_icon_btn, query_string) {

/**
 * Base Object/Model for inhertiance.
 */
var Base = function() {
    if( this.initialize ) {
        this.initialize.apply(this, arguments);
    }
};
Base.extend = Backbone.Model.extend;

/**
 * User interface controls for trackster
 */
var TracksterUI = Base.extend({
    initialize: function( baseURL ) {
        this.baseURL = baseURL;
    },

    /**
     * Save visualization, returning a Deferred object for the remote call to save.
     */
    save_viz: function() {
        // show dialog
        Galaxy.modal.show({title: "Saving...", body: "progress" });

        // Save bookmarks.
        var bookmarks = [];
        $(".bookmark").each(function() {
            bookmarks.push({
                position: $(this).children(".position").text(),
                annotation: $(this).children(".annotation").text()
            });
        });

        // FIXME: give unique IDs to Drawables and save overview as ID.
        var overview_track_name = (view.overview_drawable ? view.overview_drawable.config.get_value('name') : null),
            viz_config = {
                'view': view.to_dict(),
                'viewport': { 'chrom': view.chrom, 'start': view.low , 'end': view.high, 'overview': overview_track_name },
                'bookmarks': bookmarks
            };

        // Make call to save visualization.
        return $.ajax({
            url: Galaxy.root + "visualization/save",
            type: "POST",
            dataType: "json",
            data: {
                'id'        : view.vis_id,
                'title'     : view.config.get_value('name'),
                'dbkey'     : view.dbkey,
                'type'      : 'trackster',
                'vis_json'  : JSON.stringify(viz_config)
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
                title   : "Could Not Save",
                body    : "Could not save visualization. Please try again later.",
                buttons : { "Cancel": function() { Galaxy.modal.hide(); } }
            });
        });
    },

    /**
     * Create button menu
     */
    createButtonMenu: function() {
        var self = this,
            menu = mod_icon_btn.create_icon_buttons_menu([
            { icon_class: 'plus-button', title: 'Add tracks', on_click: function() {
                visualization.select_datasets(Galaxy.root + "visualization/list_current_history_datasets", Galaxy.root + "api/datasets", { 'f-dbkey': view.dbkey },
                function(new_tracks) {
                    _.each(new_tracks, function(track) {
                        view.add_drawable( tracks.object_from_template(track, view, view) );
                    });
                });
            } },
            { icon_class: 'block--plus', title: 'Add group', on_click: function() {
                view.add_drawable( new tracks.DrawableGroup(view, view, { name: "New Group" }) );
            } },
            { icon_class: 'bookmarks', title: 'Bookmarks', on_click: function() {
                // HACK -- use style to determine if panel is hidden and hide/show accordingly.
                force_right_panel(($("div#right").css("right") == "0px" ? "hide" : "show"));
            } },
            {
                icon_class: 'globe',
                title: 'Circster',
                on_click: function() {
                    window.location = self.baseURL + 'visualization/circster?id=' + view.vis_id;
                }
            },
            { icon_class: 'disk--arrow', title: 'Save', on_click: function() {
                self.save_viz();
            } },
            {
                icon_class: 'cross-circle',
                title: 'Close',
                on_click: function() {
                    self.handle_unsaved_changes(view);
                }
            }
        ],
        {
            tooltip_config: { placement: 'bottom' }
        });
        this.buttonMenu = menu;
        return menu;
    },

    /**
     * Use a popup to select a dataset of create bookmarks from
     */
    add_bookmarks: function() {
        var self = this,
            baseURL = this.baseURL;

        // show modal while loading history
        Galaxy.modal.show({title: "Select dataset for new bookmarks", body: "progress" });

        $.ajax({
            url: this.baseURL + "/visualization/list_histories",
            data: { "f-dbkey": view.dbkey },
            error: function() { alert( "Grid failed" ); },
            success: function(table_html) {

                // show modal to select bookmarks
                Galaxy.modal.show(
                {
                    title   : "Select dataset for new bookmarks",
                    body    : table_html,
                    buttons :
                    {
                        "Cancel": function()
                        {
                            Galaxy.modal.hide();
                        },

                        "Insert": function()
                        {
                            // Just use the first selected
                            $('input[name=id]:checked,input[name=ldda_ids]:checked').first().each(function()
                            {
                                var data, id = $(this).val();
                                if ($(this).attr("name") === "id")
                                    data = { hda_id: id };
                                else
                                    data = { ldda_id: id};

                                $.ajax({
                                    url: this.baseURL + "/visualization/bookmarks_from_dataset",
                                    data: data,
                                    dataType: "json"
                                }).then( function(data) {
                                    for( i = 0; i < data.data.length; i++ ) {
                                        var row = data.data[i];
                                        self.add_bookmark( row[0], row[1] );
                                    }
                                });
                            });
                            Galaxy.modal.hide();
                        }
                    }
                });
            }
        });
    },

    /**
     * Add bookmark.
     */
    add_bookmark: function(position, annotation, editable) {
        // Create HTML.
        var bookmarks_container = $("#right .unified-panel-body"),
            new_bookmark = $("<div/>").addClass("bookmark").appendTo(bookmarks_container);

        var position_div = $("<div/>").addClass("position").appendTo(new_bookmark),
            position_link = $("<a href=''/>").text(position).appendTo(position_div).click(function() {
                view.go_to(position);
                return false;
            }),
            annotation_div = $("<div/>").text(annotation).appendTo(new_bookmark);

        // If editable, enable bookmark deletion and annotation editing.
        if (editable) {
            var delete_icon_container = $("<div/>").addClass("delete-icon-container").prependTo(new_bookmark).click(function (){
                    // Remove bookmark.
                    new_bookmark.slideUp("fast");
                    new_bookmark.remove();
                    view.has_changes = true;
                    return false;
                }),
                delete_icon = $("<a href=''/>").addClass("icon-button delete").appendTo(delete_icon_container);
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
    create_visualization: function(view_config, viewport_config, drawables_config, bookmarks_config, editable) {

        // Create view.
        var self = this,
            view = new tracks.TracksterView(_.extend(view_config, {header: false}));
        view.editor = true;
        $.when( view.load_chroms_deferred ).then(function(chrom_info) {
            // Viewport config.
            if (viewport_config) {
                var chrom = viewport_config.chrom,
                    start = viewport_config.start,
                    end = viewport_config.end,
                    overview_drawable_name = viewport_config.overview;

                if (chrom && (start !== undefined) && end) {
                    view.change_chrom(chrom, start, end);
                }
                else {
                    // No valid viewport, so use first chromosome.
                    view.change_chrom(chrom_info[0].chrom);
                }
            }
            else {
                // No viewport, so use first chromosome.
                view.change_chrom(chrom_info[0].chrom);
            }

            // Add drawables to view.
            if (drawables_config) {
                // FIXME: can from_dict() be used to create view and add drawables?
                var drawable_config,
                    drawable_type,
                    drawable;
                for (var i = 0; i < drawables_config.length; i++) {
                    view.add_drawable( tracks.object_from_template( drawables_config[i], view, view ) );
                }
            }

            // Set overview.
            var overview_drawable;
            for (var i = 0; i < view.drawables.length; i++) {
                if (view.drawables[i].config.get_value('name') === overview_drawable_name) {
                    view.set_overview(view.drawables[i]);
                    break;
                }
            }

            // Load bookmarks.
            if (bookmarks_config) {
                var bookmark;
                for (var i = 0; i < bookmarks_config.length; i++) {
                    bookmark = bookmarks_config[i];
                    self.add_bookmark(bookmark['position'], bookmark['annotation'], editable);
                }
            }

            // View has no changes as of yet.
            view.has_changes = false;
        });

        // Final initialization.
        this.set_up_router({view: view});

        return view;
    },

    /**
     * Set up location router to use hashes as track browser locations.
     */
    set_up_router : function(options)
    {
        new visualization.TrackBrowserRouter(options);
        Backbone.history.start();
    },

    /**
     * Set up keyboard navigation for a visualization.
     */
    init_keyboard_nav: function(view) {
        // Keyboard navigation. Scroll ~7% of height when scrolling up/down.
        $(document).keyup(function(e) {
            // Do not navigate if arrow keys used in input element.
            if ($(e.srcElement).is(':input')) {
                return;
            }

            // Key codes: left == 37, up == 38, right == 39, down == 40
            switch(e.which) {
                case 37:
                    view.move_fraction(0.25);
                    break;
                case 38:
                    var change = Math.round(view.viewport_container.height()/15.0);
                    view.viewport_container.scrollTop( view.viewport_container.scrollTop() - 20);
                    break;
                case 39:
                    view.move_fraction(-0.25);
                    break;
                case 40:
                    var change = Math.round(view.viewport_container.height()/15.0);
                    view.viewport_container.scrollTop( view.viewport_container.scrollTop() + 20);
                    break;
            }
        });
    },

    /**
     * Handle unsaved changes in visualization.
     */
    handle_unsaved_changes: function(view) {
        if (view.has_changes) {
            var self = this;
            Galaxy.modal.show({
                title: "Close visualization",
                body: "There are unsaved changes to your visualization which will be lost if you do not save them.",
                buttons: {
                    "Cancel": function() { Galaxy.modal.hide(); },
                    "Leave without Saving" : function() {
                        $(window).off('beforeunload');
                        window.location = Galaxy.root + 'visualization';
                    },
                    "Save" : function() {
                        $.when(self.save_viz()).then(function() {
                            window.location = Galaxy.root + 'visualization';
                        });
                    }
                }
            });

        }
        else {
            window.location = Galaxy.root + 'visualization';
        }
    }

});

var TracksterView = Backbone.View.extend(
{
    // initalize trackster
    initialize : function ()
    {
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
        $("#right-border").click(function() { view.resize_window(); });

        // hide right panel
        force_right_panel("hide");


        // check if id is available
        if (galaxy_config.app.id){
            this.view_existing();
        } else if( query_string.get( 'dataset_id' ) ){
            this.choose_existing_or_new();
        } else {
            this.view_new();
        }
    },

    choose_existing_or_new : function () {
        var self = this;
        var dbkey = query_string.get( 'dbkey' ),
            listTracksParams = {},
            dataset_params = {
                dbkey       : dbkey,
                dataset_id  : query_string.get( 'dataset_id' ),
                hda_ldda    : query_string.get( 'hda_ldda' )
            };
        if (dbkey){
            listTracksParams[ 'f-dbkey' ] = dbkey;
        }
        $.ajax({
            url: Galaxy.root + 'visualization/list_tracks?' + $.param( listTracksParams ),
            dataType: "html",
            error: function() { alert( "Could not add this dataset to browser." ); },

            success: function(table_html) {
                console.debug( 'success' );
                function view_in_saved(){
                    // Show new modal with saved visualizations.
                    Galaxy.modal.show({
                        title : "Add Data to Saved Visualization",
                        body : table_html,
                        buttons : {
                            "Cancel": function() {
                                // go back to the first choice
                                show_choice();
                            },
                            "Add to visualization": function() {
                                $(parent.document).find('input[name=id]:checked').each(function() {
                                    var vis_id = $(this).val();
                                    dataset_params.id = vis_id;
                                    window.location = Galaxy.root + "visualization/trackster?" + $.param(dataset_params);
                                });
                            }
                        }
                    });
                }
                function show_choice(){
                    Galaxy.modal.show({
                        title : "View Data in a New or Saved Visualization?",
                        // either have text in here or have to remove body and the header/footer margins
                        body  : (
                            // TODO: yay. inline styles. thanks, galaxy
                            '<p><ul style="list-style: disc inside none">You can add this dataset as:' +
                                "<li>a new track to one of your existing, saved Trackster " +
                                "sessions if they share the genome build: <b>" + dbkey + "</b></li>" +
                                "<li>or create a new session with this dataset as the only track</li>" +
                            "</ul></p>"
                        ),
                        buttons : {
                            "Cancel": function() {
                                window.location = Galaxy.root + "visualization/list";
                            },
                            "View in saved visualization": function() {
                                view_in_saved();
                            },
                            "View in new visualization": function() {
                                self.view_new();
                            }
                        }
                    });
                }
                show_choice();
            }
        });
    },

    // view
    view_existing : function ()
    {
        // get config
        var viz_config = galaxy_config.app.viz_config;

        // view
        view = ui.create_visualization(
        {
            container: $("#center .unified-panel-body"),
            name: viz_config.title,
            vis_id: viz_config.vis_id,
            dbkey: viz_config.dbkey
        }, viz_config.viewport, viz_config.tracks, viz_config.bookmarks, true);

        // initialize editor
        this.init_editor();
    },

    // view
    view_new : function ()
    {
        // availability of default database key
        /*if (galaxy_config.app.default_dbkey !== undefined)
        {
            this.create_browser("Unnamed", galaxy_config.app.default_dbkey);
            return;
        }*/

        // reference this
        var self = this;

        // ajax
        $.ajax(
        {
            url: Galaxy.root + "api/genomes?chrom_info=True",
            data: {},
            error: function() { alert( "Couldn't create new browser." ); },
            success: function(response)
            {
                // show dialog
                Galaxy.modal.show({
                    title   : "New Visualization",
                    body    : self.template_view_new(response),
                    buttons : {
                        "Cancel": function() { window.location = Galaxy.root + "visualization/list"; },
                        "Create": function() { self.create_browser($("#new-title").val(), $("#new-dbkey").val()); Galaxy.modal.hide(); }
                    }
                });

                // select default
                var dbkeys_in_genomes = response.map( function( r ){ return r[1]; });
                if (galaxy_config.app.default_dbkey && _.contains(dbkeys_in_genomes,galaxy_config.app.default_dbkey)) {
                    $("#new-dbkey").val( galaxy_config.app.default_dbkey );
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
    template_view_new: function(response)
    {
        // start template
        var html =  '<form id="new-browser-form" action="javascript:void(0);" method="post" onsubmit="return false;">' +
                        '<div class="form-row">' +
                            '<label for="new-title">Browser name:</label>' +
                            '<div class="form-row-input">' +
                                '<input type="text" name="title" id="new-title" value="Unnamed"></input>' +
                            '</div>' +
                            '<div style="clear: both;"></div>' +
                        '</div>' +
                        '<div class="form-row">' +
                            '<label for="new-dbkey">Reference genome build (dbkey): </label>' +
                            '<div class="form-row-input">' +
                                '<select name="dbkey" id="new-dbkey">';

        // add dbkeys
        for (var i = 0; i < response.length; i++) {
            html += '<option value="' + response[i][1] + '">' + response[i][0] + '</option>';
        }

        // close selection/finalize template
        html +=                 '</select>' +
                            '</div>' +
                            '<div style="clear: both;"></div>' +
                        '</div>' +
                        '<div class="form-row">' +
                            'Is the build not listed here? ' +
                            '<a href="' + Galaxy.root + 'user/dbkeys?use_panels=True">Add a Custom Build</a>' +
                        '</div>' +
                    '</form>';

        // return
        return html;
    },

    // create
    create_browser : function(name, dbkey)
    {
        $(document).trigger("convert_to_values");

        view = ui.create_visualization (
        {
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
    init_editor : function ()
    {
        // set title
        $("#center .unified-panel-title").text(view.config.get_value('name') + " (" + view.dbkey + ")");

        // add dataset
        if (galaxy_config.app.add_dataset)
            $.ajax({
                url: Galaxy.root + "api/datasets/" + galaxy_config.app.add_dataset,
                data: { hda_ldda: 'hda', data_type: 'track_config' },
                dataType: "json",
                success: function(track_data) { view.add_drawable( tracks.object_from_template(track_data, view, view) ); }
            });

        // initialize icons
        $("#add-bookmark-button").click(function()
        {
            // add new bookmark.
            var position = view.chrom + ":" + view.low + "-" + view.high,
                annotation = "Bookmark description";
            return ui.add_bookmark(position, annotation, true);
        });

        // initialize keyboard
        ui.init_keyboard_nav(view);

        $(window).on('beforeunload', function() {
            if (view.has_changes) {
                return "There are unsaved changes to your visualization that will be lost if you leave this page.";
            }
        });
    }
});

return {
    TracksterUI: TracksterUI,
    GalaxyApp : TracksterView
};

});
