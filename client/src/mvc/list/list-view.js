import $ from "jquery";
import Backbone from "backbone";
import _ from "underscore";
import LIST_ITEM from "mvc/list/list-item";
import LoadingIndicator from "ui/loading-indicator";
import BASE_MVC from "mvc/base-mvc";
import _l from "utils/localization";
import "ui/search-input";

var logNamespace = "list";
/* ============================================================================
TODO:

============================================================================ */
/** @class View for a list/collection of models and the sub-views of those models.
 *      Sub-views must (at least have the interface if not) inherit from ListItemView.
 *      (For a list panel that also includes some 'container' model (History->HistoryContents)
 *      use ModelWithListPanel)
 *
 *  Allows for:
 *      searching collection/sub-views
 *      selecting/multi-selecting sub-views
 *
 *  Currently used:
 *      for dataset/dataset-choice
 *      as superclass of ModelListPanel
 */
var ListPanel = Backbone.View.extend(BASE_MVC.LoggableMixin).extend(
    /** @lends ListPanel.prototype */ {
        _logNamespace: logNamespace,

        /** class to use for constructing the sub-views */
        viewClass: LIST_ITEM.ListItemView,
        /** class to used for constructing collection of sub-view models */
        collectionClass: Backbone.Collection,

        tagName: "div",
        className: "list-panel",
        actionButtonClass: "list-action-menu-btn",

        /** (in ms) that jquery effects will use */
        fxSpeed: "fast",

        /** string to display when the collection has no contents */
        emptyMsg: _l("This list is empty"),
        /** displayed when no items match the search terms */
        noneFoundMsg: _l("No matching items found"),
        /** string used for search placeholder */
        searchPlaceholder: _l("search"),

        // ......................................................................... SET UP
        /** Set up the view, set up storage, bind listeners to HistoryContents events
         *  @param {Object} attributes optional settings for the list
         */
        initialize: function (attributes, options) {
            attributes = attributes || {};
            // set the logger if requested
            if (attributes.logger) {
                this.logger = attributes.logger;
            }
            this.log(`${this}.initialize:`, attributes);

            // ---- instance vars
            /** how quickly should jquery fx run? */
            this.fxSpeed = _.has(attributes, "fxSpeed") ? attributes.fxSpeed : this.fxSpeed;

            /** filters for displaying subviews */
            this.filters = [];
            /** current search terms */
            this.searchFor = attributes.searchFor || "";

            /** loading indicator */
            // this.indicator = new LoadingIndicator( this.$el );

            /** currently showing selectors on items? */
            this.selecting = attributes.selecting !== undefined ? attributes.selecting : true;
            //this.selecting = false;

            /** cached selected item.model.ids to persist btwn renders */
            this.selected = attributes.selected || [];
            /** the last selected item.model.id */
            this.lastSelected = null;

            /** are sub-views draggable */
            this.dragItems = attributes.dragItems || false;

            /** list item view class (when passed models) */
            this.viewClass = attributes.viewClass || this.viewClass;

            /** list item views */
            this.views = [];
            /** list item models */
            this.collection = attributes.collection || this._createDefaultCollection();

            /** filter fns run over collection items to see if they should show in the list */
            this.filters = attributes.filters || [];

            /** override $scrollContainer fn via attributes - fn should return jq for elem to call scrollTo on */
            this.$scrollContainer = attributes.$scrollContainer || this.$scrollContainer;

            /** @type {String} generic title */
            this.title = attributes.title || "";
            /** @type {String} generic subtitle */
            this.subtitle = attributes.subtitle || "";

            this._setUpListeners();
        },

        // ------------------------------------------------------------------------ listeners
        /** create any event listeners for the list */
        _setUpListeners: function () {
            this.off();

            //TODO: move errorHandler down into list-view from history-view or
            //  pass to global error handler (Galaxy)
            this.on({
                error: function (model, xhr, options, msg, details) {
                    //this.errorHandler( model, xhr, options, msg, details );
                    console.error(model, xhr, options, msg, details);
                },
                // show hide the loading indicator
                loading: function () {
                    this._showLoadingIndicator("loading...", 40);
                },
                "loading-done": function () {
                    this._hideLoadingIndicator(40);
                },
            });

            // throw the first render up as a diff namespace using once (for outside consumption)
            this.once("rendered", function () {
                this.trigger("rendered:initial", this);
            });

            this._setUpCollectionListeners();
            this._setUpViewListeners();
            return this;
        },

        /** create and return a collection for when none is initially passed */
        _createDefaultCollection: function () {
            // override
            return new this.collectionClass([]);
        },

        /** listening for collection events */
        _setUpCollectionListeners: function () {
            this.log(`${this}._setUpCollectionListeners`, this.collection);
            this.stopListening(this.collection);

            // bubble up error events
            this.listenTo(this.collection, {
                error: function (model, xhr, options, msg, details) {
                    this.trigger("error", model, xhr, options, msg, details);
                },
                update: function (collection, options) {
                    var changes = options.changes;
                    // console.info( collection + ', update:', changes, '\noptions:', options );
                    // more than one: render everything
                    if (options.renderAll || changes.added.length + changes.removed.length > 1) {
                        return this.renderItems();
                    }
                    // otherwise, let the single add/remove handlers do it
                    if (changes.added.length === 1) {
                        return this.addItemView(_.first(changes.added), collection, options);
                    }
                    if (changes.removed.length === 1) {
                        return this.removeItemView(_.first(changes.removed), collection, options);
                    }
                },
            });
            return this;
        },

        /** listening for sub-view events that bubble up with the 'view:' prefix */
        _setUpViewListeners: function () {
            this.log(`${this}._setUpViewListeners`);

            // shift to select a range
            this.on({
                "view:selected": function (view, ev) {
                    if (ev && ev.shiftKey && this.lastSelected) {
                        var lastSelectedView = this.viewFromModelId(this.lastSelected);
                        if (lastSelectedView) {
                            this.selectRange(view, lastSelectedView);
                        }
                    } else if (ev && ev.altKey && !this.selecting) {
                        this.showSelectors();
                    }
                    this.selected.push(view.model.id);
                    this.lastSelected = view.model.id;
                },

                "view:de-selected": function (view, ev) {
                    this.selected = _.without(this.selected, view.model.id);
                },
            });
        },

        // ------------------------------------------------------------------------ rendering
        /** Render this content, set up ui.
         *  @param {Number or String} speed   the speed of the render
         */
        render: function (speed) {
            this.log(`${this}.render`, speed);
            var $newRender = this._buildNewRender();
            this._setUpBehaviors($newRender);
            this._queueNewRender($newRender, speed);
            return this;
        },

        /** Build a temp div containing the new children for the view's $el. */
        _buildNewRender: function () {
            this.debug(`${this}(ListPanel)._buildNewRender`);
            var $newRender = $(this.templates.el({}, this));
            this._renderControls($newRender);
            this._renderTitle($newRender);
            this._renderSubtitle($newRender);
            this._renderSearch($newRender);
            this.renderItems($newRender);
            return $newRender;
        },

        /** Build a temp div containing the new children for the view's $el. */
        _renderControls: function ($newRender) {
            this.debug(`${this}(ListPanel)._renderControls`);
            var $controls = $(this.templates.controls({}, this));
            $newRender.find(".controls").replaceWith($controls);
            return $controls;
        },

        /** return a jQuery object containing the title DOM */
        _renderTitle: function ($where) {
            //$where = $where || this.$el;
            //$where.find( '.title' ).replaceWith( ... )
        },

        /** return a jQuery object containing the subtitle DOM (if any) */
        _renderSubtitle: function ($where) {
            //$where = $where || this.$el;
            //$where.find( '.title' ).replaceWith( ... )
        },

        /** Fade out the old el, swap in the new contents, then fade in.
         *  @param {Number or String} speed   jq speed to use for rendering effects
         *  @fires rendered when rendered
         */
        _queueNewRender: function ($newRender, speed) {
            speed = speed === undefined ? this.fxSpeed : speed;
            var panel = this;
            panel.log("_queueNewRender:", $newRender, speed);

            $(panel).queue("fx", [
                (next) => {
                    panel.$el.fadeOut(speed, next);
                },
                (next) => {
                    panel._swapNewRender($newRender);
                    next();
                },
                (next) => {
                    panel.$el.fadeIn(speed, next);
                },
                (next) => {
                    panel.trigger("rendered", panel);
                    next();
                },
            ]);
        },

        /** empty out the current el, move the $newRender's children in */
        _swapNewRender: function ($newRender) {
            this.$el.empty().attr("class", this.className).append($newRender.children());
            if (this.selecting) {
                this.showSelectors(0);
            }
            return this;
        },

        /** Set up any behaviors, handlers (ep. plugins) that need to be called when the entire view has been built but
         *  not attached to the page yet.
         */
        _setUpBehaviors: function ($where) {
            $where = $where || this.$el;
            this.$controls($where).find("[title]").tooltip();
            // set up the pupup for actions available when multi selecting
            this._renderMultiselectActionMenu($where);
            return this;
        },

        /** render a menu containing the actions available to sets of selected items */
        _renderMultiselectActionMenu: function ($where) {
            $where = $where || this.$el;
            var $menu = $where.find(".list-action-menu");
            var actions = this.multiselectActions();
            if (!actions.length) {
                return $menu.empty();
            }
            var $newMenu = $(
                `<div class="list-action-menu btn-group dropdown">
                    <button class="${
                        this.actionButtonClass
                    } btn btn-secondary dropdown-toggle" data-boundary="viewport" data-toggle="dropdown">
                        ${_l("For all selected")}...
                    </button>
                    <div class="dropdown-menu" role="menu"/>
                </div>`
            );
            var $actions = actions.map((action) => {
                var html = `<a class="dropdown-item" href="javascript:void(0);">${action.html}</a>`;
                return $(html).click((ev) => {
                    ev.preventDefault();
                    return action.func(ev);
                });
            });
            $newMenu.find(".dropdown-menu").append($actions);
            $menu.replaceWith($newMenu);
            return $newMenu;
        },

        /** return a list of plain objects used to render multiselect actions menu. Each object should have:
         *      html: an html string used as the anchor contents
         *      func: a function called when the anchor is clicked (passed the click event)
         */
        multiselectActions: function () {
            return [];
        },

        // ------------------------------------------------------------------------ sub-$element shortcuts
        /** the scroll container for this panel - can be $el, $el.parent(), or grandparent depending on context */
        $scrollContainer: function ($where) {
            // override or set via attributes.$scrollContainer
            return ($where || this.$el).parent().parent();
        },
        /** convenience selector for the section that displays the list controls */
        $controls: function ($where) {
            return ($where || this.$el).find("> .controls");
        },
        /** list-items: where the subviews are contained in the view's dom */
        $list: function ($where) {
            return ($where || this.$el).find("> .list-items");
        },
        /** container where list messages are attached */
        $messages: function ($where) {
            //TODO: controls isn't really correct here (only for ModelListPanel)
            return ($where || this.$el).find("> .controls .messages");
        },
        /** the message displayed when no views can be shown (no views, none matching search) */
        $emptyMessage: function ($where) {
            return ($where || this.$el).find("> .empty-message");
        },

        // ------------------------------------------------------------------------ hda sub-views
        /** render the subviews for the list's collection */
        renderItems: function ($whereTo) {
            $whereTo = $whereTo || this.$el;
            var panel = this;
            panel.log(`${this}.renderItems`, $whereTo);

            var $list = panel.$list($whereTo);
            panel.freeViews();
            // console.log( 'views freed' );
            //TODO:? cache and re-use views?
            var shownModels = panel._filterCollection();
            // console.log( 'models filtered:', shownModels );

            panel.views = shownModels.map((itemModel) => {
                return panel._createItemView(itemModel);
            });

            $list.empty();
            // console.log( 'list emptied' );
            if (panel.views.length) {
                panel._attachItems($whereTo);
                // console.log( 'items attached' );
            }
            panel._renderEmptyMessage($whereTo).toggle(!panel.views.length);
            panel.trigger("views:ready", panel.views);

            // console.log( '------------------------------------------- rendering items' );
            return panel.views;
        },

        /** Filter the collection to only those models that should be currently viewed */
        _filterCollection: function () {
            // override this
            var panel = this;
            return panel.collection.filter(_.bind(panel._filterItem, panel));
        },

        /** Should the model be viewable in the current state?
         *     Checks against this.filters and this.searchFor
         */
        _filterItem: function (model) {
            // override this
            var panel = this;
            return (
                _.every(panel.filters.map((fn) => fn.call(model))) &&
                (!panel.searchFor || model.matchesAll(panel.searchFor))
            );
        },

        /** Create a view for a model and set up it's listeners */
        _createItemView: function (model) {
            var ViewClass = this._getItemViewClass(model);
            var options = _.extend(this._getItemViewOptions(model), {
                model: model,
            });
            var view = new ViewClass(options);
            this._setUpItemViewListeners(view);
            return view;
        },

        /** Free a view for a model. Note: does not remove it from the DOM */
        _destroyItemView: function (view) {
            this.stopListening(view);
            this.views = _.without(this.views, view);
        },

        _destroyItemViews: function (view) {
            var self = this;
            self.views.forEach((v) => {
                self.stopListening(v);
            });
            self.views = [];
            return self;
        },

        /** free any sub-views the list has */
        freeViews: function () {
            return this._destroyItemViews();
        },

        /** Get the bbone view class based on the model */
        _getItemViewClass: function (model) {
            // override this
            return this.viewClass;
        },

        /** Get the options passed to the new view based on the model */
        _getItemViewOptions: function (model) {
            // override this
            return {
                //logger      : this.logger,
                fxSpeed: this.fxSpeed,
                expanded: false,
                selectable: this.selecting,
                selected: _.contains(this.selected, model.id),
                draggable: this.dragItems,
            };
        },

        /** Set up listeners for new models */
        _setUpItemViewListeners: function (view) {
            var panel = this;
            // send all events to the panel, re-namspaceing them with the view prefix
            this.listenTo(view, "all", function () {
                var args = Array.prototype.slice.call(arguments, 0);
                args[0] = `view:${args[0]}`;
                panel.trigger.apply(panel, args);
            });

            // drag multiple - hijack ev.setData to add all selected items
            this.listenTo(
                view,
                "draggable:dragstart",
                function (ev, v) {
                    //TODO: set multiple drag data here
                    var json = {};

                    var selected = this.getSelectedModels();
                    if (selected.length) {
                        json = selected.toJSON();
                    } else {
                        json = [v.model.toJSON()];
                    }
                    ev.dataTransfer.setData("text", JSON.stringify(json));
                    //ev.dataTransfer.setDragImage( v.el, 60, 60 );
                },
                this
            );

            return panel;
        },

        /** Attach views in this.views to the model based on $whereTo */
        _attachItems: function ($whereTo) {
            var self = this;
            // console.log( '_attachItems:', $whereTo, this.$list( $whereTo ) );
            //ASSUMES: $list has been emptied
            this.$list($whereTo).append(this.views.map((view) => self._renderItemView$el(view)));
            return this;
        },

        /** get a given subview's $el (or whatever may wrap it) and return it */
        _renderItemView$el: function (view) {
            // useful to wrap and override
            return view.render(0).$el;
        },

        /** render the empty/none-found message */
        _renderEmptyMessage: function ($whereTo) {
            this.debug("_renderEmptyMessage", $whereTo, this.searchFor);
            var text = this.searchFor ? this.noneFoundMsg : this.emptyMsg;
            return this.$emptyMessage($whereTo).text(text);
        },

        /** expand all item views */
        expandAll: function () {
            _.each(this.views, (view) => {
                view.expand();
            });
        },

        /** collapse all item views */
        collapseAll: function () {
            _.each(this.views, (view) => {
                view.collapse();
            });
        },

        // ------------------------------------------------------------------------ collection/views syncing
        /** Add a view (if the model should be viewable) to the panel */
        addItemView: function (model, collection, options) {
            // console.log( this + '.addItemView:', model );
            var panel = this;
            // get the index of the model in the list of filtered models shown by this list
            // in order to insert the view in the proper place
            //TODO:? potentially expensive
            var modelIndex = panel._filterCollection().indexOf(model);
            if (modelIndex === -1) {
                return undefined;
            }
            var view = panel._createItemView(model);
            // console.log( 'adding and rendering:', modelIndex, view.toString() );

            $(view).queue("fx", [
                (next) => {
                    // hide the empty message first if only view
                    if (panel.$emptyMessage().is(":visible")) {
                        panel.$emptyMessage().fadeOut(panel.fxSpeed, next);
                    } else {
                        next();
                    }
                },
                (next) => {
                    panel._attachView(view, modelIndex);
                    next();
                },
            ]);
            return view;
        },

        /** internal fn to add view (to both panel.views and panel.$list) */
        _attachView: function (view, modelIndex, useFx) {
            // console.log( this + '._attachView:', view, modelIndex, useFx );
            useFx = _.isUndefined(useFx) ? true : useFx;
            modelIndex = modelIndex || 0;
            var panel = this;

            // use the modelIndex to splice into views and insert at the proper index in the DOM
            panel.views.splice(modelIndex, 0, view);
            panel._insertIntoListAt(modelIndex, panel._renderItemView$el(view).hide());

            panel.trigger("view:attached", view);
            if (useFx) {
                view.$el.slideDown(panel.fxSpeed, () => {
                    panel.trigger("view:attached:rendered");
                });
            } else {
                view.$el.show();
                panel.trigger("view:attached:rendered");
            }
            return view;
        },

        /** insert a jq object as a child of list-items at the specified *DOM index* */
        _insertIntoListAt: function (index, $what) {
            // console.log( this + '._insertIntoListAt:', index, $what );
            var $list = this.$list();
            if (index === 0) {
                $list.prepend($what);
            } else {
                $list
                    .children()
                    .eq(index - 1)
                    .after($what);
            }
            return $what;
        },

        /** Remove a view from the panel (if found) */
        removeItemView: function (model, collection, options) {
            var panel = this;
            var view = _.find(panel.views, (v) => v.model === model);
            if (!view) {
                return undefined;
            }
            panel.views = _.without(panel.views, view);
            panel.trigger("view:removed", view);

            // potentially show the empty message if no views left
            // use anonymous queue here - since remove can happen multiple times
            $({}).queue("fx", [
                (next) => {
                    view.$el.fadeOut(panel.fxSpeed, next);
                },
                (next) => {
                    view.remove();
                    panel.trigger("view:removed:rendered");
                    if (!panel.views.length) {
                        panel._renderEmptyMessage().fadeIn(panel.fxSpeed, next);
                    } else {
                        next();
                    }
                },
            ]);
            return view;
        },

        /** get views based on model.id */
        viewFromModelId: function (id) {
            return _.find(this.views, (v) => v.model.id === id);
        },

        /** get views based on model */
        viewFromModel: function (model) {
            return model ? this.viewFromModelId(model.id) : undefined;
        },

        /** get views based on model properties */
        viewsWhereModel: function (properties) {
            return this.views.filter((view) => _.isMatch(view.model.attributes, properties));
        },

        /** A range of views between (and including) viewA and viewB */
        viewRange: function (viewA, viewB) {
            if (viewA === viewB) {
                return viewA ? [viewA] : [];
            }

            var indexA = this.views.indexOf(viewA);
            var indexB = this.views.indexOf(viewB);

            // handle not found
            if (indexA === -1 || indexB === -1) {
                if (indexA === indexB) {
                    return [];
                }
                return indexA === -1 ? [viewB] : [viewA];
            }
            // reverse if indeces are
            //note: end inclusive
            return indexA < indexB ? this.views.slice(indexA, indexB + 1) : this.views.slice(indexB, indexA + 1);
        },

        // ------------------------------------------------------------------------ searching
        /** render a search input for filtering datasets shown
         *      (see SearchableMixin in base-mvc for implementation of the actual searching)
         *      return will start the search
         *      esc will clear the search
         *      clicking the clear button will clear the search
         *      uses searchInput in ui.js
         */
        _renderSearch: function ($where) {
            $where.find(".controls .search-input").searchInput({
                placeholder: this.searchPlaceholder,
                initialVal: this.searchFor,
                onfirstsearch: _.bind(this._firstSearch, this),
                onsearch: _.bind(this.searchItems, this),
                onclear: _.bind(this.clearSearch, this),
                advsearchlink: true,
            });
            return $where;
        },

        /** What to do on the first search entered */
        _firstSearch: function (searchFor) {
            // override to load model details if necc.
            this.log("onFirstSearch", searchFor);
            return this.searchItems(searchFor);
        },

        /** filter view list to those that contain the searchFor terms */
        searchItems: function (searchFor, force) {
            this.log("searchItems", searchFor, this.searchFor, force);
            if (!force && this.searchFor === searchFor) {
                return this;
            }
            this.searchFor = searchFor;
            this.renderItems();
            this.trigger("search:searching", searchFor, this);
            var $search = this.$("> .controls .search-query");
            if ($search.val() !== searchFor) {
                $search.val(searchFor);
            }
            return this;
        },

        /** clear the search filters and show all views that are normally shown */
        clearSearch: function (searchFor) {
            //this.log( 'onSearchClear', this );
            this.searchFor = "";
            this.trigger("search:clear", this);
            this.$("> .controls .search-query").val("");
            this.renderItems();
            return this;
        },

        // ------------------------------------------------------------------------ selection
        /** @type Integer when the number of list item views is >= to this, don't animate selectors */
        THROTTLE_SELECTOR_FX_AT: 20,

        /** show selectors on all visible itemViews and associated controls */
        showSelectors: function (speed) {
            speed = speed !== undefined ? speed : this.fxSpeed;
            this.selecting = true;
            this.$(".list-actions").slideDown(speed);
            speed = this.views.length >= this.THROTTLE_SELECTOR_FX_AT ? 0 : speed;
            _.each(this.views, (view) => {
                view.showSelector(speed);
            });
            //this.selected = [];
            //this.lastSelected = null;
        },

        /** hide selectors on all visible itemViews and associated controls */
        hideSelectors: function (speed) {
            speed = speed !== undefined ? speed : this.fxSpeed;
            this.selecting = false;
            this.$(".list-actions").slideUp(speed);
            speed = this.views.length >= this.THROTTLE_SELECTOR_FX_AT ? 0 : speed;
            _.each(this.views, (view) => {
                view.hideSelector(speed);
            });
            this.selected = [];
            this.lastSelected = null;
        },

        /** show or hide selectors on all visible itemViews and associated controls */
        toggleSelectors: function () {
            if (!this.selecting) {
                this.showSelectors();
            } else {
                this.hideSelectors();
            }
        },

        /** select all visible items */
        selectAll: function (event) {
            _.each(this.views, (view) => {
                view.select(event);
            });
        },

        /** deselect all visible items */
        deselectAll: function (event) {
            this.lastSelected = null;
            _.each(this.views, (view) => {
                view.deselect(event);
            });
        },

        /** select a range of datasets between A and B */
        selectRange: function (viewA, viewB) {
            var range = this.viewRange(viewA, viewB);
            _.each(range, (view) => {
                view.select();
            });
            return range;
        },

        /** return an array of all currently selected itemViews */
        getSelectedViews: function () {
            return _.filter(this.views, (v) => v.selected);
        },

        /** return a collection of the models of all currenly selected items */
        getSelectedModels: function () {
            // console.log( '(getSelectedModels)' );
            return new this.collection.constructor(_.map(this.getSelectedViews(), (view) => view.model));
        },

        // ------------------------------------------------------------------------ loading indicator
        /** hide the $el and display a loading indicator (in the $el's parent) when loading new data */
        _showLoadingIndicator: function (msg, speed, callback) {
            this.debug("_showLoadingIndicator", this.indicator, msg, speed, callback);
            speed = speed !== undefined ? speed : this.fxSpeed;
            if (!this.indicator) {
                this.indicator = new LoadingIndicator.LoadingIndicator(this.$el);
                this.debug("\t created", this.indicator);
            }
            if (!this.$el.is(":visible")) {
                this.indicator.show(0, callback);
            } else {
                this.$el.fadeOut(speed);
                this.indicator.show(msg, speed, callback);
            }
        },

        /** hide the loading indicator */
        _hideLoadingIndicator: function (speed, callback) {
            this.debug("_hideLoadingIndicator", this.indicator, speed, callback);
            speed = speed !== undefined ? speed : this.fxSpeed;
            if (this.indicator) {
                this.indicator.hide(speed, callback);
            }
        },

        // ------------------------------------------------------------------------ scrolling
        /** get the current scroll position of the panel in its parent */
        scrollPosition: function () {
            return this.$scrollContainer().scrollTop();
        },

        /** set the current scroll position of the panel in its parent */
        scrollTo: function (pos, speed) {
            speed = speed || 0;
            this.$scrollContainer().animate({ scrollTop: pos }, speed);
            return this;
        },

        /** Scrolls the panel to the top. */
        scrollToTop: function (speed) {
            return this.scrollTo(0, speed);
        },

        /** scroll to the given view in list-items */
        scrollToItem: function (view, speed) {
            if (!view) {
                return this;
            }
            return this;
        },

        /** Scrolls the panel to show the content with the given id. */
        scrollToId: function (id, speed) {
            return this.scrollToItem(this.viewFromModelId(id), speed);
        },

        // ------------------------------------------------------------------------ panel events
        /** event map */
        events: {
            "click .select-all": "selectAll",
            "click .deselect-all": "deselectAll",
        },

        // ------------------------------------------------------------------------ misc
        /** Return a string rep of the panel */
        toString: function () {
            return `ListPanel(${this.collection})`;
        },
    }
);

// ............................................................................ TEMPLATES
/** underscore templates */
ListPanel.prototype.templates = (() => {
    var elTemplate = BASE_MVC.wrapTemplate([
        // temp container
        "<div>",
        '<div class="controls"></div>',
        '<div class="list-items"></div>',
        '<div class="empty-message alert alert-info"></div>',
        "</div>",
    ]);

    var controlsTemplate = BASE_MVC.wrapTemplate([
        '<div class="controls">',
        '<div class="title">',
        '<div class="name"><%- view.title %></div>',
        "</div>",
        '<div class="subtitle"><%- view.subtitle %></div>',
        // buttons, controls go here
        '<div class="actions"></div>',
        // deleted msg, etc.
        '<div class="messages"></div>',

        '<div class="search">',
        '<div class="search-input"></div>',
        "</div>",

        // show when selectors are shown
        '<div class="list-actions">',
        '<div class="btn-group">',
        '<button class="select-all btn btn-secondary"',
        'data-mode="select">',
        _l("All"),
        "</button>",
        '<button class="deselect-all btn btn-secondary"',
        'data-mode="select">',
        _l("None"),
        "</button>",
        "</div>",
        '<div class="list-action-menu btn-group">',
        "</div>",
        "</div>",
        "</div>",
    ]);

    return {
        el: elTemplate,
        controls: controlsTemplate,
    };
})();

//=============================================================================
/** View for a model that has a sub-collection (e.g. History, DatasetCollection)
 *  Allows:
 *      the model to be reset
 *      auto assign panel.collection to panel.model[ panel.modelCollectionKey ]
 *
 */
var ModelListPanel = ListPanel.extend({
    /** key of attribute in model to assign to this.collection */
    modelCollectionKey: "contents",

    initialize: function (attributes) {
        ListPanel.prototype.initialize.call(this, attributes);
        this.selecting = attributes.selecting !== undefined ? attributes.selecting : false;

        this.setModel(this.model, attributes);
    },

    /** release/free/shutdown old models and set up panel for new models
     *  @fires new-model with the panel as parameter
     */
    setModel: function (model, attributes) {
        attributes = attributes || {};
        this.debug(`${this}.setModel:`, model, attributes);

        this.freeModel();
        this.freeViews();

        if (model) {
            var oldModelId = this.model ? this.model.get("id") : null;

            // set up the new model with user, logger, storage, events
            this.model = model;
            if (this.logger) {
                this.model.logger = this.logger;
            }
            this._setUpModelListeners();

            //TODO: relation btwn model, collection becoming tangled here
            // free the collection, and assign the new collection to either
            //  the model[ modelCollectionKey ], attributes.collection, or an empty vanilla collection
            this.stopListening(this.collection);
            this.collection =
                this.model[this.modelCollectionKey] || attributes.collection || this._createDefaultCollection();
            this._setUpCollectionListeners();

            if (oldModelId && model.get("id") !== oldModelId) {
                this.trigger("new-model", this);
            }
        }
        return this;
    },

    /** free the current model and all listeners for it, free any views for the model */
    freeModel: function () {
        // stop/release the previous model, and clear cache to sub-views
        if (this.model) {
            this.stopListening(this.model);
            //TODO: see base-mvc
            //this.model.free();
            //this.model = null;
        }
        return this;
    },

    // ------------------------------------------------------------------------ listening
    /** listening for model events */
    _setUpModelListeners: function () {
        // override
        this.log(`${this}._setUpModelListeners`, this.model);
        // bounce model errors up to the panel
        this.listenTo(
            this.model,
            "error",
            function () {
                var args = Array.prototype.slice.call(arguments, 0);
                //args.unshift( 'model:error' );
                args.unshift("error");
                this.trigger.apply(this, args);
            },
            this
        );

        // debugging
        if (this.logger) {
            this.listenTo(this.model, "all", function (event) {
                this.info(`${this}(model)`, event, arguments);
            });
        }
        return this;
    },

    /** Build a temp div containing the new children for the view's $el.
     */
    _renderControls: function ($newRender) {
        this.debug(`${this}(ModelListPanel)._renderControls`);
        var json = this.model ? this.model.toJSON() : {};
        var $controls = $(this.templates.controls(json, this));
        $newRender.find(".controls").replaceWith($controls);
        return $controls;
    },

    // ------------------------------------------------------------------------ misc
    /** Return a string rep of the panel */
    toString: function () {
        return `ModelListPanel(${this.model})`;
    },
});

// ............................................................................ TEMPLATES
/** underscore templates */
ModelListPanel.prototype.templates = (() => {
    var controlsTemplate = BASE_MVC.wrapTemplate([
        '<div class="controls">',
        '<div class="title">',
        //TODO: this is really the only difference - consider factoring titlebar out
        '<div class="name"><%- model.name %></div>',
        "</div>",
        '<div class="subtitle"><%- view.subtitle %></div>',
        '<div class="actions"></div>',
        '<div class="messages"></div>',

        '<div class="search">',
        '<div class="search-input"></div>',
        "</div>",

        '<div class="list-actions">',
        '<div class="btn-group">',
        '<button class="select-all btn btn-secondary"',
        'data-mode="select">',
        _l("All"),
        "</button>",
        '<button class="deselect-all btn btn-secondary"',
        'data-mode="select">',
        _l("None"),
        "</button>",
        "</div>",
        '<div class="list-action-menu btn-group">',
        "</div>",
        "</div>",
        "</div>",
    ]);

    return _.extend(_.clone(ListPanel.prototype.templates), {
        controls: controlsTemplate,
    });
})();

//=============================================================================
export default {
    ListPanel: ListPanel,
    ModelListPanel: ModelListPanel,
};
