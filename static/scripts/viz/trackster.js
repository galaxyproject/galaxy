// global variables
var ui              = null;
var view            = null;
var browser_router  = null;

// load required libraries
require(
[
    // load js libraries
    'utils/galaxy.css',
    'libs/jquery/jstorage',
    'libs/jquery/jquery.event.drag',
    'libs/jquery/jquery.event.hover',
    'libs/jquery/jquery.mousewheel',
    'libs/jquery/jquery-ui',
    'libs/jquery/jquery-ui-combobox',
    'libs/farbtastic',
    'libs/jquery/jquery.form',
    'libs/jquery/jquery.rating',
    'mvc/ui'
], function(css)
{
    // load css
    css.load_file("/static/style/jquery.rating.css");
    css.load_file("/static/style/history.css");
    css.load_file("/static/style/autocomplete_tagging.css");
    css.load_file("/static/style/jquery-ui/smoothness/jquery-ui.css");
    css.load_file("/static/style/library.css");
    css.load_file("/static/style/trackster.css");
});

// trackster viewer
define( ["libs/backbone/backbone-relational", "viz/visualization", "viz/trackster_ui"],
        function(backbone, visualization, trackster_ui)
{

var TracksterView = Backbone.View.extend(
{
    // initalize trackster
    initialize : function ()
    {
        // load ui
        ui = new trackster_ui.TracksterUI(config.root);

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
        if (config.app.id)
            this.view_existing();
        else
            this.view_new();
    },

    // set up router
    set_up_router : function(options)
    {
        browser_router = new visualization.TrackBrowserRouter(options);
        Backbone.history.start();   
    },

    // view
    view_existing : function ()
    {
        // get config
        var viz_config = config.app.viz_config;

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
        /*if (config.app.default_dbkey !== undefined)
        {
            this.create_browser("Unnamed", config.app.default_dbkey);
            return;
        }*/

        // reference this
        var self = this;

        // ajax
        $.ajax(
        {
            url: config.app.new_browser,
            data: {},
            error: function() { alert( "Couldn't create new browser." ); },
            success: function(form_html)
            {
                show_modal("New Visualization", form_html,
                {
                    "Cancel": function() { window.location = config.root + "visualization/list"; },
                    "Create": function() { self.create_browser($("#new-title").val(), $("#new-dbkey").val()); }
                });

                $("#new-title").focus();
                $("select[name='dbkey']").combobox(
                {
                    appendTo: $("#overlay"),
                    size: 40
                });

                // to support the large number of options for dbkey, enable scrolling in overlay.
                $("#overlay").css("overflow", "auto");
            }
        });
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
        }, config.app.gene_region);
      
        // initialize editor
        this.init_editor();
        
        // modify view setting
        view.editor = true;

        // hide modal dialog
        hide_modal();
    },

    // initialization for editor-specific functions.
    init_editor : function ()
    {
        // set title
        $("#center .unified-panel-title").text(view.name + " (" + view.dbkey + ")");
        
        // add dataset
        if (config.app.add_dataset)
            $.ajax({
                url: config.root + "api/datasets/" + config.app.add_dataset,
                data: { hda_ldda: 'hda', data_type: 'track_config' },
                dataType: "json",
                success: function(track_data) { view.add_drawable( trackster_ui.object_from_template(track_data, view, view) ); }
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

        // set up router
        this.set_up_router({view: view});
    }
});

// return
return {
    GalaxyApp : TracksterView
};

// done
});