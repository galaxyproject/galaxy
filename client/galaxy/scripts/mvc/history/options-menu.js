import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import PopupMenu from "mvc/ui/popup-menu";
import historyCopyDialog from "mvc/history/copy-dialog";
import Webhooks from "mvc/webhooks";

// ============================================================================
var menu = [
    {
        html: _l("History Lists"),
        header: true
    },
    {
        html: _l("Saved Histories"),
        func: function() {
            _gatherClick("saved_histories");
            window.top.location = "histories/list";
        }
    },
    {
        html: _l("Histories Shared with Me"),
        func: function() {
            _gatherClick("histories_shared_with_me");
            window.top.location = "histories/list_shared";
        }
    },
    {
        html: _l("Current History"),
        header: true,
        anon: true
    },
    {
        html: _l("Create New"),
        func: function() {
            _gatherClick("create_new");
            let Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel) {
                Galaxy.currHistoryPanel.createNewHistory();
            }
        }
    },
    {
        html: _l("Copy History"),
        func: function() {
            _gatherClick("copy_history");
            let Galaxy = getGalaxyInstance();
            historyCopyDialog(Galaxy.currHistoryPanel.model).done(() => {
                Galaxy.currHistoryPanel.loadCurrentHistory();
            });
        }
    },
    {
        html: _l("Share or Publish"),
        func: function() {
            _gatherClick("share_or_publish");
            let Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push(`/histories/sharing?id=${Galaxy.currHistoryPanel.model.id}`);
            }
        }
    },
    {
        html: _l("Show Structure"),
        anon: true,
        func: function() {
            _gatherClick("show_structure");
            let Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push("/histories/show_structure");
            }
        }
    },
    {
        html: _l("Extract Workflow"),
        func: function() {
            _gatherClick("extract_workflow");
            window.location = "workflow/build_from_current_history";
        }
    },
    {
        html: _l("Delete"),
        anon: true,
        func: function() {
            _gatherClick("delete");
            let Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && confirm(_l("Really delete the current history?"))) {
                Galaxy.currHistoryPanel.model._delete().done(() => {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        }
    },
    {
        html: _l("Delete Permanently"),
        purge: true,
        anon: true,
        func: function() {
            _gatherClick("delete_permanently");
            let Galaxy = getGalaxyInstance();
            if (
                Galaxy &&
                Galaxy.currHistoryPanel &&
                confirm(_l("Really delete the current history permanently? This cannot be undone."))
            ) {
                Galaxy.currHistoryPanel.model.purge().done(() => {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        }
    },
    {
        html: _l("Make Data Private"),
        anon: true,
        func: function() {
            _gatherClick("make_data_private");
            if (
                Galaxy &&
                Galaxy.currHistoryPanel &&
                confirm(
                    _l(
                        "This will make all the data in this history private (excluding library datasets), and will set permissions such that all new data is created as private.  Any datasets within that are currently shared will need to be re-shared or published.  Are you sure you want to do this?"
                    )
                )
            ) {
                $.post(`${Galaxy.root}history/make_private`, { history_id: Galaxy.currHistoryPanel.model.id }, () => {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        }
    },
    {
        html: _l("Dataset Actions"),
        header: true,
        anon: true
    },
    {
        html: _l("Copy Datasets"),
        func: function() {
            _gatherClick("copy_datasets");
            window.location = "dataset/copy_datasets";
        }
    },
    {
        html: _l("Dataset Security"),
        func: function() {
            _gatherClick("dataset_security");
            let Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push(`/histories/permissions?id=${Galaxy.currHistoryPanel.model.id}`);
            }
        }
    },
    {
        html: _l("Resume Paused Jobs"),
        anon: true,
        func: function() {
            _gatherClick("resume_paused_jobs");
            window.location = "history/resume_paused_jobs?current=True";
        }
    },
    {
        html: _l("Collapse Expanded Datasets"),
        func: function() {
            _gatherClick("collapse_expanded_datasets");
            let Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel) {
                Galaxy.currHistoryPanel.collapseAll();
            }
        }
    },
    {
        html: _l("Unhide Hidden Datasets"),
        anon: true,
        func: function() {
            _gatherClick("unhide_hidden_datasets");
            let Galaxy = getGalaxyInstance();
            // TODO: Deprecate this functionality and replace with group dataset selector and action combination
            if (Galaxy && Galaxy.currHistoryPanel && confirm(_l("Really unhide all hidden datasets?"))) {
                $.post(`${getAppRoot()}history/adjust_hidden`, { user_action: "unhide" }, () => {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        }
    },
    {
        html: _l("Delete Hidden Datasets"),
        anon: true,
        func: function() {
            _gatherClick("delete_hidden_datasets");
            let Galaxy = getGalaxyInstance();
            // TODO: Deprecate this functionality and replace with group dataset selector and action combination
            if (Galaxy && Galaxy.currHistoryPanel && confirm(_l("Really delete all hidden datasets?"))) {
                $.post(`${getAppRoot()}history/adjust_hidden`, { user_action: "delete" }, () => {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        }
    },
    {
        html: _l("Purge Deleted Datasets"),
        purge: true,
        anon: true,
        func: function() {
            _gatherClick("purge_deleted_datasets");
            let Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && confirm(_l("Really delete all deleted datasets permanently? This cannot be undone."))) {
                window.parent.location = "history/purge_deleted_datasets"
            }
        }
    },

    {
        html: _l("Downloads"),
        header: true
    },
    {
        html: _l("Export Tool Citations"),
        anon: true,
        func: function() {
            _gatherClick("export_tool_citations");
            let Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push(`/histories/citations?id=${Galaxy.currHistoryPanel.model.id}`);
            }
        }
    },
    {
        html: _l("Export History to File"),
        anon: true,
        func: function() {
            _gatherClick("export_history_to_file");
            window.location = "history/export_archive?preview=True";
        }
    },

    {
        html: _l("Other Actions"),
        header: true
    },
    {
        html: _l("Import from File"),
        func: function() {
            _gatherClick("import_from_file");
            window.top.location = "histories/import";
        }
    }
];

// Webhooks
Webhooks.load({
    type: "history-menu",
    async: false, // (hypothetically) slows down the performance
    callback: function(webhooks) {
        var webhooks_menu = [];

        webhooks.each(model => {
            var webhook = model.toJSON();
            if (webhook.activate) {
                webhooks_menu.push({
                    html: _l(webhook.config.title),
                    // func: function() {},
                    anon: true
                });
            }
        });

        if (webhooks_menu.length > 0) {
            webhooks_menu.unshift({
                html: _l("Webhooks"),
                header: true
            });
            $.merge(menu, webhooks_menu);
        }
    }
});

function _gatherClick(menu_option) {
    if (typeof ga !== "undefined") {
        let event_name = "history_cog_" + menu_option;
        ga('send', 'event', 'link', 'click', event_name);
    }
};

function buildMenu(isAnon, purgeAllowed, urlRoot) {
    return _.clone(menu).filter(menuOption => {
        if (isAnon && !menuOption.anon) {
            return false;
        }
        if (!purgeAllowed && menuOption.purge) {
            return false;
        }

        //TODO:?? hard-coded galaxy_main
        if (menuOption.href) {
            menuOption.href = urlRoot + menuOption.href;
            menuOption.target = menuOption.target || "galaxy_main";
        }

        if (menuOption.confirm) {
            menuOption.func = () => {
                if (confirm(menuOption.confirm)) {
                    /* galaxy_main is a global here: TODO: Fix it! */
                    galaxy_main.location = menuOption.href;
                }
            };
        }
        return true;
    });
};

var create = ($button, options) => {
    options = options || {};
    var isAnon = options.anonymous === undefined ? true : options.anonymous;
    var purgeAllowed = options.purgeAllowed || false;
    var menu = buildMenu(isAnon, purgeAllowed, getAppRoot());
    //console.debug( 'menu:', menu );
    return new PopupMenu($button, menu);
};

// ============================================================================
export default create;
