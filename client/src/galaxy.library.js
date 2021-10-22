// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === LEGACY GALAXY LIBRARY MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

import Backbone from "backbone";
import { getGalaxyInstance } from "app";
import mod_library_dataset_view from "mvc/library/library-dataset-view";
// ============================================================================
/**
 * The Data Libraries router. Takes care about triggering routes
 * and sends users to proper pieces of the application.
 */
var LibraryRouter = Backbone.Router.extend({
    initialize: function () {
        this.routesHit = 0;
        // keep count of number of routes handled by the application
        Backbone.history.on(
            "route",
            function () {
                this.routesHit++;
            },
            this
        );

        this.bind("route", this.trackPageview);
    },

    routes: {
        "folders/:folder_id/datasets/:dataset_id": "dataset_detail",
    },
});

// ============================================================================
/**
 * Main view of the Galaxy Data Libraries. Stores pointers to other subviews
 * and defines what router should do on the route triggers.
 */
var GalaxyLibrary = Backbone.View.extend({
    library_router: null,
    datasetView: null,

    initialize: function () {
        // This should go upstream in the js app once available
        const Galaxy = getGalaxyInstance();

        Galaxy.libraries = this;

        this.library_router = new LibraryRouter();

        this.library_router.on("route:dataset_detail", (folder_id, dataset_id) => {
            if (Galaxy.libraries.datasetView) {
                Galaxy.libraries.datasetView.$el.unbind("click");
            }
            Galaxy.libraries.datasetView = new mod_library_dataset_view.LibraryDatasetView({
                id: dataset_id,
                show_version: false,
                show_permissions: false,
            });
        });

        Backbone.history.start({ pushState: false });
    },
});

export default {
    GalaxyApp: GalaxyLibrary,
};
