import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import PopupMenu from "mvc/ui/popup-menu";
import historyCopyDialog from "mvc/history/copy-dialog";
import Webhooks from "mvc/webhooks";
import { switchToBetaHistoryPanel } from "../../components/History/adapters/betaToggle";

// ============================================================================
var menu = [
    {
        html: _l("History Actions"),
        header: true,
        anon: true,
    },
    {
        html: _l("Copy"),
        func: function () {
            const Galaxy = getGalaxyInstance();
            historyCopyDialog(Galaxy.currHistoryPanel.model).done(() => {
                Galaxy.currHistoryPanel.loadCurrentHistory();
            });
        },
    },
    {
        html: _l("Share or Publish"),
        func: function () {
            const Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push(`/histories/sharing?id=${Galaxy.currHistoryPanel.model.id}`);
            }
        },
        singleUserDisable: true,
    },
    {
        html: _l("Show Structure"),
        anon: true,
        func: function () {
            const Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push("/histories/show_structure");
            }
        },
    },
    {
        html: _l("Extract Workflow"),
        href: "workflow/build_from_current_history",
    },
    {
        html: _l("Set Permissions"),
        func: function () {
            const Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push(`/histories/permissions?id=${Galaxy.currHistoryPanel.model.id}`);
            }
        },
        singleUserDisable: true,
    },
    {
        html: _l("Make Private"),
        anon: true,
        func: function () {
            const Galaxy = getGalaxyInstance();
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
        },
    },
    {
        html: _l("Resume Paused Jobs"),
        href: "history/resume_paused_jobs?current=True",
        anon: true,
    },
    {
        html: _l("Dataset Actions"),
        header: true,
        anon: true,
    },
    {
        html: _l("Copy Datasets"),
        href: "dataset/copy_datasets",
    },
    {
        html: _l("Collapse Expanded Datasets"),
        func: function () {
            const Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel) {
                Galaxy.currHistoryPanel.collapseAll();
            }
        },
    },
    {
        html: _l("Unhide Hidden Datasets"),
        anon: true,
        func: function () {
            const Galaxy = getGalaxyInstance();
            // TODO: Deprecate this functionality and replace with group dataset selector and action combination
            if (Galaxy && Galaxy.currHistoryPanel && confirm(_l("Really unhide all hidden datasets?"))) {
                $.post(`${getAppRoot()}history/adjust_hidden`, { user_action: "unhide" }, () => {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        },
    },
    {
        html: _l("Delete Hidden Datasets"),
        anon: true,
        func: function () {
            const Galaxy = getGalaxyInstance();
            // TODO: Deprecate this functionality and replace with group dataset selector and action combination
            if (Galaxy && Galaxy.currHistoryPanel && confirm(_l("Really delete all hidden datasets?"))) {
                $.post(`${getAppRoot()}history/adjust_hidden`, { user_action: "delete" }, () => {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        },
    },
    {
        html: _l("Purge Deleted Datasets"),
        confirm: _l("Really delete all deleted datasets permanently? This cannot be undone."),
        href: "history/purge_deleted_datasets",
        purge: true,
        anon: true,
    },

    {
        html: _l("Downloads"),
        header: true,
    },
    {
        html: _l("Export Tool Citations"),
        anon: true,
        func: function () {
            const Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push(`/histories/citations?id=${Galaxy.currHistoryPanel.model.id}`);
            }
        },
    },
    {
        html: _l("Export History to File"),
        anon: true,
        func: function () {
            const Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push(`/histories/${Galaxy.currHistoryPanel.model.id}/export`);
            }
        },
    },
    {
        html: _l("Beta Features"),
        anon: false,
        header: true,
    },
    {
        html: _l("Use Beta History Panel"),
        anon: false,
        func: function () {
            switchToBetaHistoryPanel();
        },
    },
];

// Webhooks
Webhooks.load({
    type: "history-menu",
    async: false, // (hypothetically) slows down the performance
    callback: function (webhooks) {
        var webhooks_menu = [];

        webhooks.each((model) => {
            var webhook = model.toJSON();
            if (webhook.activate) {
                webhooks_menu.push({
                    html: _l(webhook.config.title),
                    func: webhook.config.function && new Function(webhook.config.function),
                    anon: true,
                });
            }
        });

        if (webhooks_menu.length > 0) {
            webhooks_menu.unshift({
                html: _l("Webhooks"),
                header: true,
            });
            $.merge(menu, webhooks_menu);
        }
    },
});

function buildMenu(isAnon, purgeAllowed, urlRoot) {
    const Galaxy = getGalaxyInstance();
    return _.clone(menu).filter((menuOption) => {
        if (Galaxy.config.single_user && menuOption.singleUserDisable) {
            return false;
        }
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
        menuOption.title = menuOption.html;

        if (menuOption.confirm) {
            menuOption.func = () => {
                const galaxy_main = window.parent.document.getElementById("galaxy_main");
                if (confirm(menuOption.confirm) && galaxy_main) {
                    galaxy_main.src = menuOption.href;
                }
            };
        }
        return true;
    });
}

var create = ($button, options) => {
    options = options || {};
    var isAnon = options.anonymous === undefined ? true : options.anonymous;
    var purgeAllowed = options.purgeAllowed || false;
    var menu = buildMenu(isAnon, purgeAllowed, getAppRoot());
    return new PopupMenu($button, menu);
};

// ============================================================================
export default create;
