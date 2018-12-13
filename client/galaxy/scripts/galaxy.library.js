// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === MAIN GALAXY LIBRARY MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

/* global ga */
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
// import mod_utils from "utils/utils";
import mod_toastr from "libs/toastr";
import mod_baseMVC from "mvc/base-mvc";
// import mod_library_model from "mvc/library/library-model";
import mod_folderlist_view from "mvc/library/library-folderlist-view";
import mod_librarylist_view from "mvc/library/library-librarylist-view";
import mod_librarytoolbar_view from "mvc/library/library-librarytoolbar-view";
import mod_foldertoolbar_view from "mvc/library/library-foldertoolbar-view";
import mod_library_dataset_view from "mvc/library/library-dataset-view";
import mod_library_library_view from "mvc/library/library-library-view";
import mod_library_folder_view from "mvc/library/library-folder-view";
// ============================================================================
/**
 * The Data Libraries router. Takes care about triggering routes
 * and sends users to proper pieces of the application.
 */
var LibraryRouter = Backbone.Router.extend({
    initialize: function() {
        this.routesHit = 0;
        // keep count of number of routes handled by the application
        Backbone.history.on(
            "route",
            function() {
                this.routesHit++;
            },
            this
        );

        this.bind("route", this.trackPageview);
    },

    routes: {
        "": "libraries",
        "page/:show_page": "libraries_page",
        "library/:library_id/permissions": "library_permissions",
        "folders/:folder_id/permissions": "folder_permissions",
        "folders/:id": "folder_content",
        "folders/:id/page/:show_page": "folder_page",
        "folders/:folder_id/datasets/:dataset_id": "dataset_detail",
        "folders/:folder_id/datasets/:dataset_id/permissions": "dataset_permissions",
        "folders/:folder_id/datasets/:dataset_id/versions/:ldda_id": "dataset_version",
        "folders/:folder_id/download/:format": "download",
        "folders/:folder_id/import/:source": "import_datasets"
    },

    /**
     * If more than one route has been hit the user did not land on current
     * page directly so we can go back safely. Otherwise go to the home page.
     * Use replaceState if available so the navigation doesn't create an
     * extra history entry
     */
    back: function() {
        if (this.routesHit > 1) {
            window.history.back();
        } else {
            this.navigate("#", { trigger: true, replace: true });
        }
    },

    /**
     * Track every route change as a page view in Google Analytics.
     */
    trackPageview: function() {
        var url = Backbone.history.getFragment();
        //prepend slash
        if (!/^\//.test(url) && url != "") {
            url = `/${url}`;
        }
        if (typeof ga !== "undefined") {
            ga("send", "pageview", `${getAppRoot()}library/list${url}`);
        }
    }
});

// ============================================================================
/** session storage for library preferences */
var LibraryPrefs = mod_baseMVC.SessionStorageModel.extend({
    defaults: {
        with_deleted: false,
        without_restricted: false,
        sort_order: "asc",
        sort_by: "name",
        library_page_size: 20,
        folder_page_size: 15
    }
});

// ============================================================================
/**
 * Main view of the Galaxy Data Libraries. Stores pointers to other subviews
 * and defines what router should do on the route triggers.
 */
var GalaxyLibrary = Backbone.View.extend({
    libraryToolbarView: null,
    libraryListView: null,
    library_router: null,
    libraryView: null,
    folderToolbarView: null,
    folderListView: null,
    datasetView: null,

    initialize: function() {
        // This should go upstream in the js app once available
        let Galaxy = getGalaxyInstance();
        if (Galaxy.config.ga_code) {
            ((i, s, o, g, r, a, m) => {
                i["GoogleAnalyticsObject"] = r;
                (i[r] =
                    i[r] ||
                    function() {
                        (i[r].q = i[r].q || []).push(arguments);
                    }),
                    (i[r].l = 1 * new Date());
                (a = s.createElement(o)), (m = s.getElementsByTagName(o)[0]);
                a.async = 1;
                a.src = g;
                m.parentNode.insertBefore(a, m);
            })(window, document, "script", "//www.google-analytics.com/analytics.js", "ga");
            ga("create", Galaxy.config.ga_code, "auto");
            ga("send", "pageview");
        }

        Galaxy.libraries = this;

        this.preferences = new LibraryPrefs({ id: "global-lib-prefs" });

        this.library_router = new LibraryRouter();

        this.library_router.on("route:libraries", () => {
            if (Galaxy.libraries.libraryToolbarView) {
                Galaxy.libraries.libraryToolbarView.$el.unbind("click");
            }
            Galaxy.libraries.libraryToolbarView = new mod_librarytoolbar_view.LibraryToolbarView();
            Galaxy.libraries.libraryListView = new mod_librarylist_view.LibraryListView();
        });

        this.library_router.on("route:libraries_page", show_page => {
            if (Galaxy.libraries.libraryToolbarView === null) {
                Galaxy.libraries.libraryToolbarView = new mod_librarytoolbar_view.LibraryToolbarView();
                Galaxy.libraries.libraryListView = new mod_librarylist_view.LibraryListView({ show_page: show_page });
            } else {
                Galaxy.libraries.libraryListView.render({
                    show_page: show_page
                });
            }
        });

        this.library_router.on("route:folder_content", id => {
            if (Galaxy.libraries.folderToolbarView) {
                Galaxy.libraries.folderToolbarView.$el.unbind("click");
            }
            Galaxy.libraries.folderToolbarView = new mod_foldertoolbar_view.FolderToolbarView({ id: id });
            Galaxy.libraries.folderListView = new mod_folderlist_view.FolderListView({ id: id });
        });

        this.library_router.on("route:folder_page", (id, show_page) => {
            if (Galaxy.libraries.folderToolbarView === null) {
                Galaxy.libraries.folderToolbarView = new mod_foldertoolbar_view.FolderToolbarView({ id: id });
                Galaxy.libraries.folderListView = new mod_folderlist_view.FolderListView({
                    id: id,
                    show_page: show_page
                });
            } else {
                Galaxy.libraries.folderListView.render({
                    id: id,
                    show_page: parseInt(show_page)
                });
            }
        });

        this.library_router.on("route:download", (folder_id, format) => {
            if ($("#folder_list_body").find(":checked").length === 0) {
                mod_toastr.info("You must select at least one dataset to download");
                Galaxy.libraries.library_router.navigate(`folders/${folder_id}`, { trigger: true, replace: true });
            } else {
                Galaxy.libraries.folderToolbarView.download(format);
                Galaxy.libraries.library_router.navigate(`folders/${folder_id}`, { trigger: false, replace: true });
            }
        });

        this.library_router.on("route:dataset_detail", (folder_id, dataset_id) => {
            if (Galaxy.libraries.datasetView) {
                Galaxy.libraries.datasetView.$el.unbind("click");
            }
            Galaxy.libraries.datasetView = new mod_library_dataset_view.LibraryDatasetView({
                id: dataset_id,
                show_version: false,
                show_permissions: false
            });
        });

        this.library_router.on("route:dataset_version", (folder_id, dataset_id, ldda_id) => {
            if (Galaxy.libraries.datasetView) {
                Galaxy.libraries.datasetView.$el.unbind("click");
            }
            Galaxy.libraries.datasetView = new mod_library_dataset_view.LibraryDatasetView({
                id: dataset_id,
                ldda_id: ldda_id,
                show_version: true
            });
        });

        this.library_router.on("route:dataset_permissions", (folder_id, dataset_id) => {
            if (Galaxy.libraries.datasetView) {
                Galaxy.libraries.datasetView.$el.unbind("click");
            }
            Galaxy.libraries.datasetView = new mod_library_dataset_view.LibraryDatasetView({
                id: dataset_id,
                show_permissions: true
            });
        });

        this.library_router.on("route:library_permissions", library_id => {
            if (Galaxy.libraries.libraryView) {
                Galaxy.libraries.libraryView.$el.unbind("click");
            }
            Galaxy.libraries.libraryView = new mod_library_library_view.LibraryView({
                id: library_id,
                show_permissions: true
            });
        });

        this.library_router.on("route:folder_permissions", folder_id => {
            if (Galaxy.libraries.folderView) {
                Galaxy.libraries.folderView.$el.unbind("click");
            }
            Galaxy.libraries.folderView = new mod_library_folder_view.FolderView({
                id: folder_id,
                show_permissions: true
            });
        });

        this.library_router.on("route:import_datasets", (folder_id, source) => {
            if (Galaxy.libraries.folderToolbarView && Galaxy.libraries.folderListView) {
                Galaxy.libraries.folderToolbarView.showImportModal({
                    source: source
                });
            } else {
                Galaxy.libraries.folderToolbarView = new mod_foldertoolbar_view.FolderToolbarView({ id: folder_id });
                Galaxy.libraries.folderListView = new mod_folderlist_view.FolderListView({ id: folder_id });
                Galaxy.libraries.folderToolbarView.showImportModal({
                    source: source
                });
            }
        });

        Backbone.history.start({ pushState: false });
    }
});

export default {
    GalaxyApp: GalaxyLibrary
};
