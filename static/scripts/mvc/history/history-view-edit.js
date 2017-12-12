define("mvc/history/history-view-edit", ["exports", "mvc/history/history-view", "mvc/history/history-contents", "mvc/dataset/states", "mvc/history/hda-model", "mvc/history/hda-li-edit", "mvc/history/hdca-li-edit", "mvc/tag", "mvc/annotation", "mvc/collection/list-collection-creator", "mvc/collection/pair-collection-creator", "mvc/collection/list-of-pairs-collection-creator", "ui/fa-icon-button", "mvc/ui/popup-menu", "mvc/base-mvc", "utils/localization", "ui/editable-text"], function(exports, _historyView, _historyContents, _states, _hdaModel, _hdaLiEdit, _hdcaLiEdit, _tag, _annotation, _listCollectionCreator, _pairCollectionCreator, _listOfPairsCollectionCreator, _faIconButton, _popupMenu, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _historyView2 = _interopRequireDefault(_historyView);

    var _historyContents2 = _interopRequireDefault(_historyContents);

    var _states2 = _interopRequireDefault(_states);

    var _hdaModel2 = _interopRequireDefault(_hdaModel);

    var _hdaLiEdit2 = _interopRequireDefault(_hdaLiEdit);

    var _hdcaLiEdit2 = _interopRequireDefault(_hdcaLiEdit);

    var _tag2 = _interopRequireDefault(_tag);

    var _annotation2 = _interopRequireDefault(_annotation);

    var _listCollectionCreator2 = _interopRequireDefault(_listCollectionCreator);

    var _pairCollectionCreator2 = _interopRequireDefault(_pairCollectionCreator);

    var _listOfPairsCollectionCreator2 = _interopRequireDefault(_listOfPairsCollectionCreator);

    var _faIconButton2 = _interopRequireDefault(_faIconButton);

    var _popupMenu2 = _interopRequireDefault(_popupMenu);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /* =============================================================================
    TODO:
    
    ============================================================================= */
    var _super = _historyView2.default.HistoryView;
    // base class for history-view-edit-current and used as-is in history/view.mako
    /** @class Editable View/Controller for the history model.
     *
     *  Allows:
     *      (everything HistoryView allows)
     *      changing the name
     *      displaying and editing tags and annotations
     *      multi-selection and operations on mulitple content items
     */
    var HistoryViewEdit = _super.extend(
        /** @lends HistoryViewEdit.prototype */
        {
            /** class to use for constructing the HistoryDatasetAssociation views */
            HDAViewClass: _hdaLiEdit2.default.HDAListItemEdit,
            /** class to use for constructing the HistoryDatasetCollectionAssociation views */
            HDCAViewClass: _hdcaLiEdit2.default.HDCAListItemEdit,

            // ......................................................................... SET UP
            /** Set up the view, set up storage, bind listeners to HistoryContents events
             *  @param {Object} attributes
             */
            initialize: function initialize(attributes) {
                attributes = attributes || {};
                _super.prototype.initialize.call(this, attributes);

                // ---- set up instance vars
                /** editor for tags - sub-view */
                this.tagsEditor = null;

                /** enable drag and drop - sub-view */
                this.dragItems = true;

                /** editor for annotations - sub-view */
                this.annotationEditor = null;

                /** allow user purge of dataset files? */
                this.purgeAllowed = attributes.purgeAllowed || false;

                // states/modes the panel can be in
                /** is the panel currently showing the dataset selection controls? */
                this.annotationEditorShown = attributes.annotationEditorShown || false;
                this.tagsEditorShown = attributes.tagsEditorShown || false;
            },

            /** Override to handle history as drag-drop target */
            _setUpListeners: function _setUpListeners() {
                _super.prototype._setUpListeners.call(this);
                return this.on({
                    "droptarget:drop": function droptargetDrop(ev, data) {
                        // process whatever was dropped and re-hide the drop target
                        this.dataDropped(data);
                        this.dropTargetOff();
                    },
                    "view:attached view:removed": function viewAttachedViewRemoved() {
                        this._renderCounts();
                    },
                    "search:loading-progress": this._renderSearchProgress,
                    "search:searching": this._renderSearchFindings
                });
            },

            // ------------------------------------------------------------------------ listeners
            /** listening for history and HDA events */
            _setUpModelListeners: function _setUpModelListeners() {
                _super.prototype._setUpModelListeners.call(this);
                this.listenTo(this.model, "change:size", this.updateHistoryDiskSize);
                return this;
            },

            /** listening for collection events */
            _setUpCollectionListeners: function _setUpCollectionListeners() {
                _super.prototype._setUpCollectionListeners.call(this);
                this.listenTo(this.collection, {
                    "change:deleted": this._handleItemDeletedChange,
                    "change:visible": this._handleItemVisibleChange,
                    "change:purged": function changePurged(model) {
                        // hafta get the new nice-size w/o the purged model
                        this.model.fetch();
                    },
                    // loading indicators for deleted/hidden
                    "fetching-deleted": function fetchingDeleted(collection) {
                        this.$("> .controls .deleted-count").html("<i>" + (0, _localization2.default)("loading...") + "</i>");
                    },
                    "fetching-hidden": function fetchingHidden(collection) {
                        this.$("> .controls .hidden-count").html("<i>" + (0, _localization2.default)("loading...") + "</i>");
                    },
                    "fetching-deleted-done fetching-hidden-done": this._renderCounts
                });
                return this;
            },

            // ------------------------------------------------------------------------ panel rendering
            /** In this override, add tag and annotation editors and a btn to toggle the selectors */
            _buildNewRender: function _buildNewRender() {
                // create a new render using a skeleton template, render title buttons, render body, and set up events, etc.
                var $newRender = _super.prototype._buildNewRender.call(this);
                if (!this.model) {
                    return $newRender;
                }

                if (Galaxy && Galaxy.user && Galaxy.user.id && Galaxy.user.id === this.model.get("user_id")) {
                    this._renderTags($newRender);
                    this._renderAnnotation($newRender);
                }
                return $newRender;
            },

            /** Update the history size display (curr. upper right of panel). */
            updateHistoryDiskSize: function updateHistoryDiskSize() {
                this.$(".history-size").text(this.model.get("nice_size"));
            },

            /** override to render counts when the items are rendered */
            renderItems: function renderItems($whereTo) {
                var views = _super.prototype.renderItems.call(this, $whereTo);
                if (!this.searchFor) {
                    this._renderCounts($whereTo);
                } else {
                    this._renderSearchFindings($whereTo);
                }
                return views;
            },

            /** override to show counts, what's deleted/hidden, and links to toggle those */
            _renderCounts: function _renderCounts($whereTo) {
                $whereTo = $whereTo instanceof jQuery ? $whereTo : this.$el;
                var html = this.templates.counts(this.model.toJSON(), this);
                return $whereTo.find("> .controls .subtitle").html(html);
            },

            /** render the tags sub-view controller */
            _renderTags: function _renderTags($where) {
                var panel = this;
                this.tagsEditor = new _tag2.default.TagsEditor({
                    model: this.model,
                    el: $where.find(".controls .tags-display"),
                    onshowFirstTime: function onshowFirstTime() {
                        this.render();
                    },
                    // show hide sub-view tag editors when this is shown/hidden
                    onshow: function onshow() {
                        panel.toggleHDATagEditors(true, panel.fxSpeed);
                    },
                    onhide: function onhide() {
                        panel.toggleHDATagEditors(false, panel.fxSpeed);
                    },
                    $activator: (0, _faIconButton2.default)({
                        title: (0, _localization2.default)("Edit history tags"),
                        classes: "history-tag-btn",
                        faIcon: "fa-tags"
                    }).appendTo($where.find(".controls .actions"))
                });
            },
            /** render the annotation sub-view controller */
            _renderAnnotation: function _renderAnnotation($where) {
                var panel = this;
                this.annotationEditor = new _annotation2.default.AnnotationEditor({
                    model: this.model,
                    el: $where.find(".controls .annotation-display"),
                    onshowFirstTime: function onshowFirstTime() {
                        this.render();
                    },
                    // show hide sub-view view annotation editors when this is shown/hidden
                    onshow: function onshow() {
                        panel.toggleHDAAnnotationEditors(true, panel.fxSpeed);
                    },
                    onhide: function onhide() {
                        panel.toggleHDAAnnotationEditors(false, panel.fxSpeed);
                    },
                    $activator: (0, _faIconButton2.default)({
                        title: (0, _localization2.default)("Edit history annotation"),
                        classes: "history-annotate-btn",
                        faIcon: "fa-comment"
                    }).appendTo($where.find(".controls .actions"))
                });
            },

            /** Set up HistoryViewEdit js/widget behaviours
             *  In this override, make the name editable
             */
            _setUpBehaviors: function _setUpBehaviors($where) {
                $where = $where || this.$el;
                _super.prototype._setUpBehaviors.call(this, $where);
                if (!this.model) {
                    return;
                }

                // anon users shouldn't have access to any of the following
                if (!Galaxy.user || Galaxy.user.isAnonymous() || Galaxy.user.id !== this.model.get("user_id")) {
                    return;
                }

                var panel = this;
                var nameSelector = "> .controls .name";
                $where.find(nameSelector).attr("title", (0, _localization2.default)("Click to rename history")).tooltip({
                    placement: "bottom"
                }).make_text_editable({
                    on_finish: function on_finish(newName) {
                        var previousName = panel.model.get("name");
                        if (newName && newName !== previousName) {
                            panel.$el.find(nameSelector).text(newName);
                            panel.model.save({
                                name: newName
                            }).fail(function() {
                                panel.$el.find(nameSelector).text(panel.model.previous("name"));
                            });
                        } else {
                            panel.$el.find(nameSelector).text(previousName);
                        }
                    }
                });
            },

            /** return a new popup menu for choosing a multi selection action
             *  ajax calls made for multiple datasets are queued
             */
            multiselectActions: function multiselectActions() {
                var panel = this;

                var actions = [{
                    html: (0, _localization2.default)("Hide datasets"),
                    func: function func() {
                        var action = _hdaModel2.default.HistoryDatasetAssociation.prototype.hide;
                        panel.getSelectedModels().ajaxQueue(action);
                    }
                }, {
                    html: (0, _localization2.default)("Unhide datasets"),
                    func: function func() {
                        var action = _hdaModel2.default.HistoryDatasetAssociation.prototype.unhide;
                        panel.getSelectedModels().ajaxQueue(action);
                    }
                }, {
                    html: (0, _localization2.default)("Delete datasets"),
                    func: function func() {
                        var action = _hdaModel2.default.HistoryDatasetAssociation.prototype["delete"];
                        panel.getSelectedModels().ajaxQueue(action);
                    }
                }, {
                    html: (0, _localization2.default)("Undelete datasets"),
                    func: function func() {
                        var action = _hdaModel2.default.HistoryDatasetAssociation.prototype.undelete;
                        panel.getSelectedModels().ajaxQueue(action);
                    }
                }];

                if (panel.purgeAllowed) {
                    actions.push({
                        html: (0, _localization2.default)("Permanently delete datasets"),
                        func: function func() {
                            if (confirm((0, _localization2.default)("This will permanently remove the data in your datasets. Are you sure?"))) {
                                var action = _hdaModel2.default.HistoryDatasetAssociation.prototype.purge;
                                panel.getSelectedModels().ajaxQueue(action);
                            }
                        }
                    });
                }
                actions = actions.concat(panel._collectionActions());
                return actions;
            },

            /**   */
            _collectionActions: function _collectionActions() {
                var panel = this;
                return [{
                        html: (0, _localization2.default)("Build Dataset List"),
                        func: function func() {
                            panel.buildCollection("list");
                        }
                    },
                    // TODO: Only show quick pair if two things selected.
                    {
                        html: (0, _localization2.default)("Build Dataset Pair"),
                        func: function func() {
                            panel.buildCollection("paired");
                        }
                    }, {
                        html: (0, _localization2.default)("Build List of Dataset Pairs"),
                        func: function func() {
                            panel.buildCollection("list:paired");
                        }
                    }
                ];
            },

            buildCollection: function buildCollection(collectionType, selection, hideSourceItems) {
                var panel = this;
                var selection = selection || panel.getSelectedModels();
                var hideSourceItems = hideSourceItems || false;
                var createFunc;
                if (collectionType == "list") {
                    createFunc = _listCollectionCreator2.default.createListCollection;
                } else if (collectionType == "paired") {
                    createFunc = _pairCollectionCreator2.default.createPairCollection;
                } else if (collectionType == "list:paired") {
                    createFunc = _listOfPairsCollectionCreator2.default.createListOfPairsCollection;
                } else {
                    console.warn("Unknown collectionType encountered " + collectionType);
                }
                createFunc(selection, hideSourceItems).done(function() {
                    panel.model.refresh();
                });
            },

            // ------------------------------------------------------------------------ sub-views
            /** In this override, add purgeAllowed and whether tags/annotation editors should be shown */
            _getItemViewOptions: function _getItemViewOptions(model) {
                var options = _super.prototype._getItemViewOptions.call(this, model);
                _.extend(options, {
                    purgeAllowed: this.purgeAllowed,
                    tagsEditorShown: this.tagsEditor && !this.tagsEditor.hidden,
                    annotationEditorShown: this.annotationEditor && !this.annotationEditor.hidden
                });
                return options;
            },

            /** If this item is deleted and we're not showing deleted items, remove the view
             *  @param {Model} the item model to check
             */
            _handleItemDeletedChange: function _handleItemDeletedChange(itemModel) {
                if (itemModel.get("deleted")) {
                    this._handleItemDeletion(itemModel);
                } else {
                    this._handleItemUndeletion(itemModel);
                }
                this._renderCounts();
            },

            _handleItemDeletion: function _handleItemDeletion(itemModel) {
                var contentsShown = this.model.get("contents_active");
                contentsShown.deleted += 1;
                contentsShown.active -= 1;
                if (!this.model.contents.includeDeleted) {
                    this.removeItemView(itemModel);
                }
                this.model.set("contents_active", contentsShown);
            },

            _handleItemUndeletion: function _handleItemUndeletion(itemModel) {
                var contentsShown = this.model.get("contents_active");
                contentsShown.deleted -= 1;
                if (!this.model.contents.includeDeleted) {
                    contentsShown.active -= 1;
                }
                this.model.set("contents_active", contentsShown);
            },

            /** If this item is hidden and we're not showing hidden items, remove the view
             *  @param {Model} the item model to check
             */
            _handleItemVisibleChange: function _handleItemVisibleChange(itemModel) {
                if (itemModel.hidden()) {
                    this._handleItemHidden(itemModel);
                } else {
                    this._handleItemUnhidden(itemModel);
                }
                this._renderCounts();
            },

            _handleItemHidden: function _handleItemHidden(itemModel) {
                var contentsShown = this.model.get("contents_active");
                contentsShown.hidden += 1;
                contentsShown.active -= 1;
                if (!this.model.contents.includeHidden) {
                    this.removeItemView(itemModel);
                }
                this.model.set("contents_active", contentsShown);
            },

            _handleItemUnhidden: function _handleItemUnhidden(itemModel) {
                var contentsShown = this.model.get("contents_active");
                contentsShown.hidden -= 1;
                if (!this.model.contents.includeHidden) {
                    contentsShown.active -= 1;
                }
                this.model.set("contents_active", contentsShown);
            },

            /** toggle the visibility of each content's tagsEditor applying all the args sent to this function */
            toggleHDATagEditors: function toggleHDATagEditors(showOrHide, speed) {
                _.each(this.views, function(view) {
                    if (view.tagsEditor) {
                        view.tagsEditor.toggle(showOrHide, speed);
                    }
                });
            },

            /** toggle the visibility of each content's annotationEditor applying all the args sent to this function */
            toggleHDAAnnotationEditors: function toggleHDAAnnotationEditors(showOrHide, speed) {
                _.each(this.views, function(view) {
                    if (view.annotationEditor) {
                        view.annotationEditor.toggle(showOrHide, speed);
                    }
                });
            },

            // ------------------------------------------------------------------------ panel events
            /** event map */
            events: _.extend(_.clone(_super.prototype.events), {
                "click .show-selectors-btn": "toggleSelectors",
                "click .toggle-deleted-link": function clickToggleDeletedLink(ev) {
                    this.toggleShowDeleted();
                },
                "click .toggle-hidden-link": function clickToggleHiddenLink(ev) {
                    this.toggleShowHidden();
                }
            }),

            // ------------------------------------------------------------------------ search
            _renderSearchProgress: function _renderSearchProgress(limit, offset) {
                var stop = limit + offset;
                return this.$("> .controls .subtitle").html(["<i>", (0, _localization2.default)("Searching "), stop, "/", this.model.contentsShown(), "</i>"].join(""));
            },

            /** override to display number found in subtitle */
            _renderSearchFindings: function _renderSearchFindings($whereTo) {
                $whereTo = $whereTo instanceof jQuery ? $whereTo : this.$el;
                var html = this.templates.found(this.model.toJSON(), this);
                $whereTo.find("> .controls .subtitle").html(html);
                return this;
            },

            // ------------------------------------------------------------------------ as drop target
            /** turn all the drag and drop handlers on and add some help text above the drop area */
            dropTargetOn: function dropTargetOn() {
                if (this.dropTarget) {
                    return this;
                }
                this.dropTarget = true;

                //TODO: to init
                var dropHandlers = {
                    dragenter: _.bind(this.dragenter, this),
                    dragover: _.bind(this.dragover, this),
                    dragleave: _.bind(this.dragleave, this),
                    drop: _.bind(this.drop, this)
                };

                var $dropTarget = this._renderDropTarget();
                this.$list().before([this._renderDropTargetHelp(), $dropTarget]);
                for (var evName in dropHandlers) {
                    if (dropHandlers.hasOwnProperty(evName)) {
                        //console.debug( evName, dropHandlers[ evName ] );
                        $dropTarget.on(evName, dropHandlers[evName]);
                    }
                }
                return this;
            },

            /** render a box to serve as a 'drop here' area on the history */
            _renderDropTarget: function _renderDropTarget() {
                this.$(".history-drop-target").remove();
                return $("<div/>").addClass("history-drop-target");
            },

            /** tell the user how it works  */
            _renderDropTargetHelp: function _renderDropTargetHelp() {
                this.$(".history-drop-target-help").remove();
                return $("<div/>").addClass("history-drop-target-help").text((0, _localization2.default)("Drag datasets here to copy them to the current history"));
            },

            /** shut down drag and drop event handlers and remove drop target */
            dropTargetOff: function dropTargetOff() {
                if (!this.dropTarget) {
                    return this;
                }
                //this.log( 'dropTargetOff' );
                this.dropTarget = false;
                var dropTarget = this.$(".history-drop-target").get(0);
                for (var evName in this._dropHandlers) {
                    if (this._dropHandlers.hasOwnProperty(evName)) {
                        dropTarget.off(evName, this._dropHandlers[evName]);
                    }
                }
                this.$(".history-drop-target").remove();
                this.$(".history-drop-target-help").remove();
                return this;
            },
            /** toggle the target on/off */
            dropTargetToggle: function dropTargetToggle() {
                if (this.dropTarget) {
                    this.dropTargetOff();
                } else {
                    this.dropTargetOn();
                }
                return this;
            },

            dragenter: function dragenter(ev) {
                //console.debug( 'dragenter:', this, ev );
                ev.preventDefault();
                ev.stopPropagation();
                this.$(".history-drop-target").css("border", "2px solid black");
            },
            dragover: function dragover(ev) {
                ev.preventDefault();
                ev.stopPropagation();
            },
            dragleave: function dragleave(ev) {
                //console.debug( 'dragleave:', this, ev );
                ev.preventDefault();
                ev.stopPropagation();
                this.$(".history-drop-target").css("border", "1px dashed black");
            },
            /** when (text) is dropped try to parse as json and trigger an event */
            drop: function drop(ev) {
                ev.preventDefault();
                //ev.stopPropagation();

                var self = this;
                var dataTransfer = ev.originalEvent.dataTransfer;
                var data = dataTransfer.getData("text");

                dataTransfer.dropEffect = "move";
                try {
                    data = JSON.parse(data);
                } catch (err) {
                    self.warn("error parsing JSON from drop:", data);
                }

                self.trigger("droptarget:drop", ev, data, self);
                return false;
            },

            /** handler that copies data into the contents */
            dataDropped: function dataDropped(data) {
                var self = this;
                // HDA: dropping will copy it to the history
                if (_.isObject(data) && data.model_class === "HistoryDatasetAssociation" && data.id) {
                    if (self.contents.currentPage !== 0) {
                        return self.contents.fetchPage(0).then(function() {
                            return self.model.contents.copy(data.id);
                        });
                    }
                    return self.model.contents.copy(data.id);
                }
                return jQuery.when();
            },

            // ........................................................................ misc
            /** Return a string rep of the history */
            toString: function toString() {
                return "HistoryViewEdit(" + (this.model ? this.model.get("name") : "") + ")";
            }
        });

    //------------------------------------------------------------------------------ TEMPLATES
    HistoryViewEdit.prototype.templates = function() {
        var countsTemplate = _baseMvc2.default.wrapTemplate(["<% var shown = Math.max( view.views.length, history.contents_active.active ) %>", "<% if( shown ){ %>", '<span class="shown-count">', "<%- shown %> ", (0, _localization2.default)("shown"), "</span>", "<% } %>", "<% if( history.contents_active.deleted ){ %>", '<span class="deleted-count">', "<% if( view.model.contents.includeDeleted ){ %>", '<a class="toggle-deleted-link" href="javascript:void(0);">', (0, _localization2.default)("hide deleted"), "</a>", "<% } else { %>", "<%- history.contents_active.deleted %> ", '<a class="toggle-deleted-link" href="javascript:void(0);">', (0, _localization2.default)("deleted"), "</a>", "<% } %>", "</span>", "<% } %>", "<% if( history.contents_active.hidden ){ %>", '<span class="hidden-count">', "<% if( view.model.contents.includeHidden ){ %>", '<a class="toggle-hidden-link" href="javascript:void(0);">', (0, _localization2.default)("hide hidden"), "</a>", "<% } else { %>", "<%- history.contents_active.hidden %> ", '<a class="toggle-hidden-link" href="javascript:void(0);">', (0, _localization2.default)("hidden"), "</a>", "<% } %>", "</span>", "<% } %>"], "history");

        var foundTemplate = _baseMvc2.default.wrapTemplate([(0, _localization2.default)("Found"), " <%- view.views.length %>, ", "<% if( history.contents_active.deleted ){ %>", "<% if( view.model.contents.includeDeleted ){ %>", '<a class="toggle-deleted-link" href="javascript:void(0);">', (0, _localization2.default)("hide deleted"), "</a>, ", "<% } else { %>", '<a class="toggle-deleted-link" href="javascript:void(0);">', (0, _localization2.default)("show deleted"), "</a>, ", "<% } %>", "<% } %>", "<% if( history.contents_active.hidden ){ %>", "<% if( view.model.contents.includeHidden ){ %>", '<a class="toggle-hidden-link" href="javascript:void(0);">', (0, _localization2.default)("hide hidden"), "</a>", "<% } else { %>", '<a class="toggle-hidden-link" href="javascript:void(0);">', (0, _localization2.default)("show hidden"), "</a>", "<% } %>", "<% } %>"], "history");

        return _.extend(_.clone(_super.prototype.templates), {
            counts: countsTemplate,
            found: foundTemplate
        });
    }();

    //==============================================================================
    exports.default = {
        HistoryViewEdit: HistoryViewEdit
    };
});
//# sourceMappingURL=../../../maps/mvc/history/history-view-edit.js.map
