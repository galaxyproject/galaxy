define("mvc/history/options-menu", ["exports", "mvc/ui/popup-menu", "mvc/history/copy-dialog", "mvc/base-mvc", "utils/localization", "mvc/webhooks"], function(exports, _popupMenu, _copyDialog, _baseMvc, _localization, _webhooks) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _popupMenu2 = _interopRequireDefault(_popupMenu);

    var _copyDialog2 = _interopRequireDefault(_copyDialog);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    var _webhooks2 = _interopRequireDefault(_webhooks);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    // ============================================================================
    var menu = [{
        html: (0, _localization2.default)("History Lists"),
        header: true
    }, {
        html: (0, _localization2.default)("Saved Histories"),
        href: "histories/list",
        target: "_top"
    }, {
        html: (0, _localization2.default)("Histories Shared with Me"),
        href: "histories/list_shared",
        target: "_top"
    }, {
        html: (0, _localization2.default)("Current History"),
        header: true,
        anon: true
    }, {
        html: (0, _localization2.default)("Create New"),
        func: function func() {
            if (Galaxy && Galaxy.currHistoryPanel) {
                Galaxy.currHistoryPanel.createNewHistory();
            }
        }
    }, {
        html: (0, _localization2.default)("Copy History"),
        func: function func() {
            (0, _copyDialog2.default)(Galaxy.currHistoryPanel.model).done(function() {
                Galaxy.currHistoryPanel.loadCurrentHistory();
            });
        }
    }, {
        html: (0, _localization2.default)("Share or Publish"),
        href: "history/sharing"
    }, {
        html: (0, _localization2.default)("Show Structure"),
        href: "history/display_structured",
        anon: true
    }, {
        html: (0, _localization2.default)("Extract Workflow"),
        href: "workflow/build_from_current_history"
    }, {
        html: (0, _localization2.default)("Delete"),
        anon: true,
        func: function func() {
            if (Galaxy && Galaxy.currHistoryPanel && confirm((0, _localization2.default)("Really delete the current history?"))) {
                Galaxy.currHistoryPanel.model._delete().done(function() {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        }
    }, {
        html: (0, _localization2.default)("Delete Permanently"),
        purge: true,
        anon: true,
        func: function func() {
            if (Galaxy && Galaxy.currHistoryPanel && confirm((0, _localization2.default)("Really delete the current history permanently? This cannot be undone."))) {
                Galaxy.currHistoryPanel.model.purge().done(function() {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        }
    }, {
        html: (0, _localization2.default)("Dataset Actions"),
        header: true,
        anon: true
    }, {
        html: (0, _localization2.default)("Copy Datasets"),
        href: "dataset/copy_datasets"
    }, {
        html: (0, _localization2.default)("Dataset Security"),
        func: function func() {
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push("/histories/permissions?id=" + Galaxy.currHistoryPanel.model.id);
            }
        }
    }, {
        html: (0, _localization2.default)("Resume Paused Jobs"),
        href: "history/resume_paused_jobs?current=True",
        anon: true
    }, {
        html: (0, _localization2.default)("Collapse Expanded Datasets"),
        func: function func() {
            if (Galaxy && Galaxy.currHistoryPanel) {
                Galaxy.currHistoryPanel.collapseAll();
            }
        }
    }, {
        html: (0, _localization2.default)("Unhide Hidden Datasets"),
        anon: true,
        func: function func() {
            // TODO: Deprecate this functionality and replace with group dataset selector and action combination
            if (Galaxy && Galaxy.currHistoryPanel && confirm((0, _localization2.default)("Really unhide all hidden datasets?"))) {
                $.post(Galaxy.root + "history/adjust_hidden", {
                    user_action: "unhide"
                }, function() {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        }
    }, {
        html: (0, _localization2.default)("Delete Hidden Datasets"),
        anon: true,
        func: function func() {
            // TODO: Deprecate this functionality and replace with group dataset selector and action combination
            if (Galaxy && Galaxy.currHistoryPanel && confirm((0, _localization2.default)("Really delete all hidden datasets?"))) {
                $.post(Galaxy.root + "history/adjust_hidden", {
                    user_action: "delete"
                }, function() {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                });
            }
        }
    }, {
        html: (0, _localization2.default)("Purge Deleted Datasets"),
        confirm: (0, _localization2.default)("Really delete all deleted datasets permanently? This cannot be undone."),
        href: "history/purge_deleted_datasets",
        purge: true,
        anon: true
    }, {
        html: (0, _localization2.default)("Downloads"),
        header: true
    }, {
        html: (0, _localization2.default)("Export Tool Citations"),
        anon: true,
        func: function func() {
            if (Galaxy && Galaxy.currHistoryPanel && Galaxy.router) {
                Galaxy.router.push("/histories/citations?id=" + Galaxy.currHistoryPanel.model.id);
            }
        }
    }, {
        html: (0, _localization2.default)("Export History to File"),
        href: "history/export_archive?preview=True",
        anon: true
    }, {
        html: (0, _localization2.default)("Other Actions"),
        header: true
    }, {
        html: (0, _localization2.default)("Import from File"),
        href: "histories/import",
        target: "_top"
    }];

    // Webhooks
    _webhooks2.default.add({
        url: "api/webhooks/history-menu/all",
        async: false, // (hypothetically) slows down the performance
        callback: function callback(webhooks) {
            var webhooks_menu = [];

            $.each(webhooks.models, function(index, model) {
                var webhook = model.toJSON();
                if (webhook.activate) {
                    webhooks_menu.push({
                        html: (0, _localization2.default)(webhook.config.title),
                        // func: function() {},
                        anon: true
                    });
                }
            });

            if (webhooks_menu.length > 0) {
                webhooks_menu.unshift({
                    html: (0, _localization2.default)("Webhooks"),
                    header: true
                });
                $.merge(menu, webhooks_menu);
            }
        }
    });

    function buildMenu(isAnon, purgeAllowed, urlRoot) {
        return _.clone(menu).filter(function(menuOption) {
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
                menuOption.func = function() {
                    if (confirm(menuOption.confirm)) {
                        galaxy_main.location = menuOption.href;
                    }
                };
            }
            return true;
        });
    }

    var create = function create($button, options) {
        options = options || {};
        var isAnon = options.anonymous === undefined ? true : options.anonymous;
        var purgeAllowed = options.purgeAllowed || false;
        var menu = buildMenu(isAnon, purgeAllowed, Galaxy.root);
        //console.debug( 'menu:', menu );
        return new _popupMenu2.default($button, menu);
    };

    // ============================================================================
    exports.default = create;
});
//# sourceMappingURL=../../../maps/mvc/history/options-menu.js.map
