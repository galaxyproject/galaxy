import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import HISTORY_VIEW_EDIT from "mvc/history/history-view-edit";
import BASE_MVC from "mvc/base-mvc";
import _l from "utils/localization";

// ============================================================================
/** session storage for history panel preferences (and to maintain state)
 */
var HistoryViewPrefs = BASE_MVC.SessionStorageModel.extend(
    /** @lends HistoryViewPrefs.prototype */ {
        defaults: {
            /** should the tags editor be shown or hidden initially? */
            tagsEditorShown: false,
            /** should the annotation editor be shown or hidden initially? */
            annotationEditorShown: false,
            ///** what is the currently focused content (dataset or collection) in the current history?
            // *      (the history panel will highlight and scroll to the focused content view)
            // */
            //focusedContentId : null
            /** Current scroll position */
            scrollPosition: 0
        },
        toString: function() {
            return `HistoryViewPrefs(${JSON.stringify(this.toJSON())})`;
        }
    }
);

/** key string to store panel prefs (made accessible on class so you can access sessionStorage directly) */
HistoryViewPrefs.storageKey = function storageKey() {
    return "history-panel";
};

/* =============================================================================
TODO:

============================================================================= */
var _super = HISTORY_VIEW_EDIT.HistoryViewEdit;
// used in root/index.mako
/** @class View/Controller for the user's current history model as used in the history
 *      panel (current right hand panel) of the analysis page.
 *
 *  The only history panel that:
 *      will poll for updates.
 *      displays datasets in reverse hid order.
 */
var CurrentHistoryView = _super.extend(
    /** @lends CurrentHistoryView.prototype */ {
        className: `${_super.prototype.className} current-history-panel`,

        /** override to use drilldown (and not foldout) for how collections are displayed */
        HDCAViewClass: _super.prototype.HDCAViewClass.extend({
            foldoutStyle: "drilldown"
        }),

        emptyMsg: [
            _l("This history is empty"),
            ". ",
            _l("You can "),
            '<a class="uploader-link" href="javascript:void(0)">',
            _l("load your own data"),
            "</a>",
            _l(" or "),
            '<a class="get-data-link" href="javascript:void(0)">',
            _l("get data from an external source"),
            "</a>"
        ].join(""),

        // ......................................................................... SET UP
        /** Set up the view, set up storage, bind listeners to HistoryContents events */
        initialize: function(attributes) {
            attributes = attributes || {};

            // ---- persistent preferences
            /** maintain state / preferences over page loads */
            this.preferences = new HistoryViewPrefs(
                _.extend(
                    {
                        id: HistoryViewPrefs.storageKey()
                    },
                    _.pick(attributes, _.keys(HistoryViewPrefs.prototype.defaults))
                )
            );

            _super.prototype.initialize.call(this, attributes);

            /** sub-views that will overlay this panel (collections) */
            this.panelStack = [];

            /** id of currently focused content */
            this.currentContentId = attributes.currentContentId || null;
            //NOTE: purposely not sent to localstorage since panel recreation roughly lines up with a reset of this value
        },

        /** Override to cache the current scroll position with a listener */
        _setUpListeners: function() {
            _super.prototype._setUpListeners.call(this);

            var panel = this;
            // reset scroll position when there's a new history
            this.on("new-model", () => {
                panel.preferences.set("scrollPosition", 0);
            });
        },

        // ------------------------------------------------------------------------ loading history/item models
        // TODO: next three more appropriate moved to the app level
        /** (re-)loads the user's current history & contents w/ details */
        loadCurrentHistory: function() {
            return this.loadHistory(null, {
                url: `${getAppRoot()}history/current_history_json`
            });
        },

        /** loads a history & contents w/ details and makes them the current history */
        switchToHistory: function(historyId, attributes) {
            let Galaxy = getGalaxyInstance();
            if (Galaxy.user.isAnonymous()) {
                this.trigger("error", _l("You must be logged in to switch histories"), _l("Anonymous user"));
                return $.when();
            }
            return this.loadHistory(historyId, {
                url: `${getAppRoot()}history/set_as_current?id=${historyId}`
            });
        },

        /** creates a new history on the server and sets it as the user's current history */
        createNewHistory: function(attributes) {
            let Galaxy = getGalaxyInstance();
            if (Galaxy.user.isAnonymous()) {
                this.trigger("error", _l("You must be logged in to create histories"), _l("Anonymous user"));
                return $.when();
            }
            return this.loadHistory(null, {
                url: `${getAppRoot()}history/create_new_current`
            });
        },

        /** release/free/shutdown old models and set up panel for new models */
        setModel: function(model, attributes, render) {
            _super.prototype.setModel.call(this, model, attributes, render);
            if (this.model && this.model.id) {
                this.log("checking for updates");
                this.model.checkForUpdates();
            }
            return this;
        },

        // ------------------------------------------------------------------------ history/content event listening
        /** listening for history events */
        _setUpModelListeners: function() {
            _super.prototype._setUpModelListeners.call(this);
            // re-broadcast any model change events so that listeners don't have to re-bind to each history
            return this.listenTo(this.model, {
                "change:nice_size change:size": function() {
                    this.trigger("history-size-change", this, this.model, arguments);
                },
                "change:id": function() {
                    this.once("loading-done", function() {
                        this.model.checkForUpdates();
                    });
                }
            });
        },

        /** listening for collection events */
        _setUpCollectionListeners: function() {
            _super.prototype._setUpCollectionListeners.call(this);
            // if a hidden item is created (gen. by a workflow), moves thru the updater to the ready state,
            //  then: remove it from the collection if the panel is set to NOT show hidden datasets
            this.listenTo(this.collection, "state:ready", function(model, newState, oldState) {
                if (!model.get("visible") && !this.collection.storage.includeHidden()) {
                    this.removeItemView(model);
                }
            });
        },

        // ------------------------------------------------------------------------ panel rendering
        /** override to add a handler to capture the scroll position when the parent scrolls */
        _setUpBehaviors: function($where) {
            $where = $where || this.$el;
            // console.log( '_setUpBehaviors', this.$scrollContainer( $where ).get(0), this.$list( $where ) );
            // we need to call this in _setUpBehaviors which is called after render since the $el
            // may not be attached to $el.parent and $scrollContainer() may not work
            var panel = this;
            _super.prototype._setUpBehaviors.call(panel, $where);

            // cache the handler to remove and re-add so we don't pile up the handlers
            if (!this._debouncedScrollCaptureHandler) {
                this._debouncedScrollCaptureHandler = _.debounce(function scrollCapture() {
                    // cache the scroll position (only if visible)
                    if (panel.$el.is(":visible")) {
                        panel.preferences.set("scrollPosition", $(this).scrollTop());
                    }
                }, 40);
            }

            panel
                .$scrollContainer($where)
                .off("scroll", this._debouncedScrollCaptureHandler)
                .on("scroll", this._debouncedScrollCaptureHandler);
            return panel;
        },

        /** In this override, handle null models and move the search input to the top */
        _buildNewRender: function() {
            if (!this.model) {
                return $();
            }
            var $newRender = _super.prototype._buildNewRender.call(this);
            $newRender.find(".search").prependTo($newRender.find("> .controls"));
            this._renderQuotaMessage($newRender);
            return $newRender;
        },

        /** render the message displayed when a user is over quota and can't run jobs */
        _renderQuotaMessage: function($whereTo) {
            $whereTo = $whereTo || this.$el;
            return $(this.templates.quotaMsg({}, this)).prependTo($whereTo.find(".messages"));
        },

        /** In this override, get and set current panel preferences when editor is used */
        _renderTags: function($where) {
            var panel = this;
            // render tags and show/hide based on preferences
            _super.prototype._renderTags.call(panel, $where);
            if (panel.preferences.get("tagsEditorShown")) {
                panel.tagsEditor.toggle(true);
            }
            // store preference when shown or hidden
            panel.listenTo(panel.tagsEditor, "hiddenUntilActivated:shown hiddenUntilActivated:hidden", tagsEditor => {
                panel.preferences.set("tagsEditorShown", tagsEditor.hidden);
            });
        },

        /** In this override, get and set current panel preferences when editor is used */
        _renderAnnotation: function($where) {
            var panel = this;
            // render annotation and show/hide based on preferences
            _super.prototype._renderAnnotation.call(panel, $where);
            if (panel.preferences.get("annotationEditorShown")) {
                panel.annotationEditor.toggle(true);
            }
            // store preference when shown or hidden
            panel.listenTo(
                panel.annotationEditor,
                "hiddenUntilActivated:shown hiddenUntilActivated:hidden",
                annotationEditor => {
                    panel.preferences.set("annotationEditorShown", annotationEditor.hidden);
                }
            );
        },

        /** Override to scroll to cached position (in prefs) after swapping */
        _swapNewRender: function($newRender) {
            _super.prototype._swapNewRender.call(this, $newRender);
            var panel = this;
            _.delay(() => {
                var pos = panel.preferences.get("scrollPosition");
                if (pos) {
                    panel.scrollTo(pos, 0);
                }
            }, 10);
            //TODO: is this enough of a delay on larger histories?

            return this;
        },

        // ------------------------------------------------------------------------ sub-views
        /** Override to add the current-content highlight class to currentContentId's view */
        _attachItems: function($whereTo) {
            _super.prototype._attachItems.call(this, $whereTo);
            var panel = this;
            if (panel.currentContentId) {
                panel._setCurrentContentById(panel.currentContentId);
            }
            return this;
        },

        /** Override to remove any drill down panels */
        addItemView: function(model, collection, options) {
            var view = _super.prototype.addItemView.call(this, model, collection, options);
            if (!view) {
                return view;
            }
            if (this.panelStack.length) {
                return this._collapseDrilldownPanel();
            }
            return view;
        },

        // ------------------------------------------------------------------------ collection sub-views
        /** In this override, add/remove expanded/collapsed model ids to/from web storage */
        _setUpItemViewListeners: function(view) {
            var panel = this;
            _super.prototype._setUpItemViewListeners.call(panel, view);
            // use pub-sub to: handle drilldown expansion and collapse
            return panel.listenTo(view, {
                "expanded:drilldown": function(v, drilldown) {
                    this._expandDrilldownPanel(drilldown);
                },
                "collapsed:drilldown": function(v, drilldown) {
                    this._collapseDrilldownPanel(drilldown);
                }
            });
        },

        /** display 'current content': add a visible highlight and store the id of a content item */
        setCurrentContent: function(view) {
            this.$(".history-content.current-content").removeClass("current-content");
            if (view) {
                view.$el.addClass("current-content");
                this.currentContentId = view.model.id;
            } else {
                this.currentContentId = null;
            }
        },

        /** find the view with the id and then call setCurrentContent on it */
        _setCurrentContentById: function(id) {
            var view = this.viewFromModelId(id) || null;
            this.setCurrentContent(view);
        },

        /** Handle drill down by hiding this panels list and controls and showing the sub-panel */
        _expandDrilldownPanel: function(drilldown) {
            this.panelStack.push(drilldown);
            // hide this panel's controls and list, set the name for back navigation, and attach to the $el
            this.$controls()
                .add(this.$list())
                .hide();
            drilldown.parentName = this.model.get("name");
            drilldown
                .delegateEvents()
                .render()
                .$el.appendTo(this.$el);
        },

        /** Handle drilldown close by freeing the panel and re-rendering this panel */
        _collapseDrilldownPanel: function(drilldown) {
            this.panelStack.pop();
            //TODO: MEM: free the panel
            this.$controls()
                .add(this.$list())
                .show();
        },

        // ........................................................................ panel events
        /** event map */
        events: _.extend(_.clone(_super.prototype.events), {
            // the two links in the empty message
            "click .uploader-link": function(ev) {
                let Galaxy = getGalaxyInstance();
                Galaxy.upload.show(ev);
            },
            "click .get-data-link": function(ev) {
                var $toolMenu = $(".toolMenuContainer");
                $toolMenu.parent().scrollTop(0);
                $toolMenu.find('span:contains("Get Data")').click();
            }
        }),

        // ........................................................................ external objects/MVC
        listenToGalaxy: function(galaxy) {
            this.listenTo(galaxy, {
                // when the galaxy_main iframe is loaded with a new page,
                // compare the url to the following list and if there's a match
                // pull the id from url and indicate in the history view that
                // the dataset with that id is the 'current'ly active dataset
                "center-frame:load": function(data) {
                    var pathToMatch = data.fullpath;
                    var hdaId = null;
                    var useToURLRegexMap = {
                        display: /datasets\/([a-f0-9]+)\/display/,
                        edit: /datasets\/([a-f0-9]+)\/edit/,
                        report_error: /dataset\/errors\?id=([a-f0-9]+)/,
                        rerun: /tool_runner\/rerun\?id=([a-f0-9]+)/,
                        show_params: /datasets\/([a-f0-9]+)\/show_params/
                        // no great way to do this here? (leave it in the dataset event handlers above?)
                        // 'visualization' : 'visualization',
                    };
                    _.find(useToURLRegexMap, (regex, use) => {
                        // grab the more specific match result (1), save, and use it as the find flag
                        hdaId = _.result(pathToMatch.match(regex), 1);
                        return hdaId;
                    });
                    // need to type mangle to go from web route to history contents
                    this._setCurrentContentById(hdaId ? `dataset-${hdaId}` : null);
                },
                // when the center panel is given a new view, clear the current indicator
                "center-panel:load": function(view) {
                    try {
                        let hdaId = view.model.attributes.dataset_id || null;
                        if (hdaId === null) {
                            throw "Invalid id";
                        }
                        this._setCurrentContentById(`dataset-${hdaId}`);
                    } catch (e) {
                        this._setCurrentContentById();
                    }
                },
                "activate-hda": function(hdaId) {
                    this._setCurrentContentById(`dataset-${hdaId}`);
                }
            });
        },

        //TODO: remove quota meter from panel and remove this
        /** add listeners to an external quota meter (mvc/user/user-quotameter.js) */
        connectToQuotaMeter: function(quotaMeter) {
            if (!quotaMeter) {
                return this;
            }
            // show/hide the 'over quota message' in the history when the meter tells it to
            this.listenTo(quotaMeter, "quota:over", this.showQuotaMessage);
            this.listenTo(quotaMeter, "quota:under", this.hideQuotaMessage);

            // having to add this to handle re-render of hview while overquota (the above do not fire)
            this.on("rendered rendered:initial", function() {
                if (quotaMeter && quotaMeter.isOverQuota()) {
                    this.showQuotaMessage();
                }
            });
            return this;
        },

        /** Override to preserve the quota message */
        clearMessages: function(ev) {
            var $target = !_.isUndefined(ev) ? $(ev.currentTarget) : this.$messages().children('[class$="message"]');
            $target = $target.not(".quota-message");
            $target.fadeOut(this.fxSpeed, function() {
                $(this).remove();
            });
            return this;
        },

        /** Show the over quota message (which happens to be in the history panel).
         */
        showQuotaMessage: function() {
            var $msg = this.$(".quota-message");
            if ($msg.is(":hidden")) {
                $msg.slideDown(this.fxSpeed);
            }
        },

        /** Hide the over quota message (which happens to be in the history panel).
         */
        hideQuotaMessage: function() {
            var $msg = this.$(".quota-message");
            if (!$msg.is(":hidden")) {
                $msg.slideUp(this.fxSpeed);
            }
        },

        // ........................................................................ options menu
        //TODO: remove to batch
        /** unhide any hidden datasets */
        unhideHidden: function() {
            var self = this;
            if (window.confirm(_l("Really unhide all hidden datasets?"))) {
                // get all hidden, regardless of deleted/purged
                return self.model.contents
                    ._filterAndUpdate({ visible: false, deleted: "", purged: "" }, { visible: true })
                    .done(() => {
                        // TODO: would be better to render these as they're unhidden instead of all at once
                        if (!self.model.contents.includeHidden) {
                            self.renderItems();
                        }
                    });
            }
            return $.when();
        },

        /** delete any hidden datasets */
        deleteHidden: function() {
            var self = this;
            if (window.confirm(_l("Really delete all hidden datasets?"))) {
                return self.model.contents._filterAndUpdate(
                    // get all hidden, regardless of deleted/purged
                    { visible: false, deleted: "", purged: "" },
                    // both delete *and* unhide them
                    { deleted: true, visible: true }
                );
            }
            return $.when();
        },

        /** Return a string rep of the history */
        toString: function() {
            return `CurrentHistoryView(${this.model ? this.model.get("name") : ""})`;
        }
    }
);

//------------------------------------------------------------------------------ TEMPLATES
CurrentHistoryView.prototype.templates = (() => {
    var quotaMsgTemplate = BASE_MVC.wrapTemplate(
        [
            '<div class="quota-message errormessage">',
            _l("You are over your disk quota"),
            ". ",
            _l("Tool execution is on hold until your disk usage drops below your allocated quota"),
            ".",
            "</div>"
        ],
        "history"
    );
    return _.extend(_.clone(_super.prototype.templates), {
        quotaMsg: quotaMsgTemplate
    });
})();

//==============================================================================
export default {
    CurrentHistoryView: CurrentHistoryView
};
