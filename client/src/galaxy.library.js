// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === MAIN GALAXY LIBRARY MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

/* global ga */
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import mod_baseMVC from "mvc/base-mvc";
import mod_library_dataset_view from "mvc/library/library-dataset-view";
import mod_library_library_view from "mvc/library/library-library-view";
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
        "": "libraries",
        "page/:show_page": "libraries_page",
        "library/:library_id/permissions": "library_permissions",
        "folders/:folder_id/permissions": "folder_permissions",
        "folders/:folder_id/datasets/:dataset_id": "dataset_detail",
        "folders/:folder_id/datasets/:dataset_id/permissions": "dataset_permissions",
        "folders/:folder_id/datasets/:dataset_id/versions/:ldda_id": "dataset_version",
    },

    /**
     * If more than one route has been hit the user did not land on current
     * page directly so we can go back safely. Otherwise go to the home page.
     * Use replaceState if available so the navigation doesn't create an
     * extra history entry
     */
    back: function () {
        if (this.routesHit > 1) {
            window.history.back();
        } else {
            this.navigate("#", { trigger: true, replace: true });
        }
    },

    /**
     * Track every route change as a page view in Google Analytics or Plausible
     */
    trackPageview: function () {
        var url = Backbone.history.getFragment();
        //prepend slash
        if (!/^\//.test(url) && url != "") {
            url = `/${url}`;
        }
        if (typeof ga !== "undefined") {
            ga("send", "pageview", `${getAppRoot()}library/list${url}`);
        }
        if (typeof window.plausible !== "undefined") {
            window.plausible(`pageview ${getAppRoot()}library/list${url}`);
        }
        if (typeof window._paq !== "undefined") {
            window._paq.push(["setCustomUrl", `${getAppRoot()}library/list${url}`]);
            window._paq.push(["trackPageView"]);
        }
    },
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
        folder_page_size: 15,
    },
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

    initialize: function () {
        // This should go upstream in the js app once available
        const Galaxy = getGalaxyInstance();
        if (Galaxy.config.ga_code) {
            ((i, s, o, g, r, a, m) => {
                i["GoogleAnalyticsObject"] = r;
                (i[r] =
                    i[r] ||
                    function () {
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
        if (Galaxy.config.plausible_server && Galaxy.config.plausible_domain) {
            document.write(
                '<script async defer data-domain="' +
                    Galaxy.config.plausible_domain +
                    '" src="' +
                    Galaxy.config.plausible_server +
                    '/js/plausible.js"></script>'
            );
        }
        if (Galaxy.config.matomo_server && Galaxy.config.matomo_site_id) {
            var _paq = (window._paq = window._paq || []);
            /* tracker methods like "setCustomDimension" should be called before "trackPageView" */
            _paq.push(["trackPageView"]);
            _paq.push(["enableLinkTracking"]);
            (function () {
                var u = Galaxy.config.matomo_server + "/";
                _paq.push(["setTrackerUrl", u + "matomo.php"]);
                _paq.push(["setSiteId", Galaxy.config.matomo_site_id]);
                var d = document;
                var g = d.createElement("script");
                var s = d.getElementsByTagName("script")[0];
                g.type = "text/javascript";
                g.async = true;
                g.src = u + "matomo.js";
                s.parentNode.insertBefore(g, s);
            })();
        }

        Galaxy.libraries = this;

        this.preferences = new LibraryPrefs({ id: "global-lib-prefs" });

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

        this.library_router.on("route:dataset_version", (folder_id, dataset_id, ldda_id) => {
            if (Galaxy.libraries.datasetView) {
                Galaxy.libraries.datasetView.$el.unbind("click");
            }
            Galaxy.libraries.datasetView = new mod_library_dataset_view.LibraryDatasetView({
                id: dataset_id,
                ldda_id: ldda_id,
                show_version: true,
            });
        });

        this.library_router.on("route:dataset_permissions", (folder_id, dataset_id) => {
            if (Galaxy.libraries.datasetView) {
                Galaxy.libraries.datasetView.$el.unbind("click");
            }
            Galaxy.libraries.datasetView = new mod_library_dataset_view.LibraryDatasetView({
                id: dataset_id,
                show_permissions: true,
            });
        });

        this.library_router.on("route:library_permissions", (library_id) => {
            if (Galaxy.libraries.libraryView) {
                Galaxy.libraries.libraryView.$el.unbind("click");
            }
            Galaxy.libraries.libraryView = new mod_library_library_view.LibraryView({
                id: library_id,
                show_permissions: true,
            });
        });

        Backbone.history.start({ pushState: false });
    },
});

export default {
    GalaxyApp: GalaxyLibrary,
};
