import $ from "jquery";
import Backbone from "backbone";
import _ from "underscore";
import BASE_MVC from "mvc/base-mvc";

var logNamespace = "list";
//==============================================================================
/** A view which, when first rendered, shows only summary data/attributes, but
 *      can be expanded to show further details (and optionally fetch those
 *      details from the server).
 */
var ExpandableView = Backbone.View.extend(BASE_MVC.LoggableMixin).extend({
    _logNamespace: logNamespace,

    //TODO: Although the reasoning behind them is different, this shares a lot with HiddenUntilActivated above: combine them
    //PRECONDITION: model must have method hasDetails
    //PRECONDITION: subclasses must have templates.el and templates.details

    initialize: function (attributes) {
        /** are the details of this view expanded/shown or not? */
        this.expanded = attributes.expanded || false;
        this.log("\t expanded:", this.expanded);
        this.fxSpeed = attributes.fxSpeed !== undefined ? attributes.fxSpeed : this.fxSpeed;
    },

    // ........................................................................ render main
    /** jq fx speed */
    fxSpeed: "fast",

    /** Render this content, set up ui.
     *  @param {Number or String} speed   the speed of the render
     */
    render: function (speed) {
        var $newRender = this._buildNewRender();
        this._setUpBehaviors($newRender);
        this._queueNewRender($newRender, speed);
        return this;
    },

    /** Build a temp div containing the new children for the view's $el.
     *      If the view is already expanded, build the details as well.
     */
    _buildNewRender: function () {
        // create a new render using a skeleton template, render title buttons, render body, and set up events, etc.
        var $newRender = $(this.templates.el(this.model.toJSON(), this));
        if (this.expanded) {
            this.$details($newRender).replaceWith(this._renderDetails().show());
        }
        return $newRender;
    },

    /** Fade out the old el, swap in the new contents, then fade in.
     *  @param {Number or String} speed   jq speed to use for rendering effects
     *  @fires rendered when rendered
     */
    _queueNewRender: function ($newRender, speed) {
        speed = speed === undefined ? this.fxSpeed : speed;
        var view = this;

        if (speed === 0) {
            view._swapNewRender($newRender);
            view.trigger("rendered", view);
        } else {
            $(view).queue("fx", [
                (next) => {
                    view.$el.fadeOut(speed, next);
                },
                (next) => {
                    view._swapNewRender($newRender);
                    next();
                },
                (next) => {
                    view.$el.fadeIn(speed, next);
                },
                (next) => {
                    view.trigger("rendered", view);
                    next();
                },
            ]);
        }
    },

    /** empty out the current el, move the $newRender's children in */
    _swapNewRender: function ($newRender) {
        return this.$el
            .empty()
            .attr("class", _.isFunction(this.className) ? this.className() : this.className)
            .append($newRender.children());
    },

    /** set up js behaviors, event handlers for elements within the given container
     *  @param {jQuery} $container jq object that contains the elements to process (defaults to this.$el)
     */
    _setUpBehaviors: function ($where) {
        $where = $where || this.$el;
        // set up canned behavior on children (bootstrap, popupmenus, editable_text, etc.)
        //make_popup_menus( $where );
        $where.find("[title]").tooltip({ placement: "bottom" });
    },

    // ......................................................................... details
    /** shortcut to details DOM (as jQ) */
    $details: function ($where) {
        $where = $where || this.$el;
        return $where.find("> .details");
    },

    /** build the DOM for the details and set up behaviors on it */
    _renderDetails: function () {
        var $newDetails = $(this.templates.details(this.model.toJSON(), this));
        this._setUpBehaviors($newDetails);
        return $newDetails;
    },

    // ......................................................................... expansion/details
    /** Show or hide the details
     *  @param {Boolean} expand if true, expand; if false, collapse
     */
    toggleExpanded: function (expand) {
        expand = expand === undefined ? !this.expanded : expand;
        if (expand) {
            this.expand();
        } else {
            this.collapse();
        }
        return this;
    },

    /** Render and show the full, detailed body of this view including extra data and controls.
     *      note: if the model does not have detailed data, fetch that data before showing the body
     *  @fires expanded when a body has been expanded
     */
    expand: function () {
        var view = this;
        return view._fetchModelDetails().always(() => {
            view._expand();
        });
    },

    /** Check for model details and, if none, fetch them.
     *  @returns {jQuery.promise} the model.fetch.xhr if details are being fetched, an empty promise if not
     */
    _fetchModelDetails: function () {
        if (!this.model.hasDetails()) {
            return this.model.fetch();
        }
        return $.when();
    },

    /** Inner fn called when expand (public) has fetched the details */
    _expand: function () {
        var view = this;
        var $newDetails = view._renderDetails();
        view.$details().replaceWith($newDetails);
        // needs to be set after the above or the slide will not show
        view.expanded = true;
        view.$details().slideDown(view.fxSpeed, () => {
            view.trigger("expanded", view);
        });
    },

    /** Hide the body/details of an HDA.
     *  @fires collapsed when a body has been collapsed
     */
    collapse: function () {
        this.debug(`${this}(ExpandableView).collapse`);
        var view = this;
        view.expanded = false;
        this.$details().slideUp(view.fxSpeed, () => {
            view.trigger("collapsed", view);
        });
    },
});

//==============================================================================
/** A view that is displayed in some larger list/grid/collection.
 *      Inherits from Expandable, Selectable, Draggable.
 *  The DOM contains warnings, a title bar, and a series of primary action controls.
 *      Primary actions are meant to be easily accessible item functions (such as delete)
 *      that are rendered in the title bar.
 *
 *  Details are rendered when the user clicks the title bar or presses enter/space when
 *      the title bar is in focus.
 *
 *  Designed as a base class for history panel contents - but usable elsewhere (I hope).
 */
export var ListItemView = ExpandableView.extend(
    BASE_MVC.mixin(BASE_MVC.SelectableViewMixin, BASE_MVC.DraggableViewMixin, {
        tagName: "div",
        className: "list-item",

        /** Set up the base class and all mixins */
        initialize: function (attributes) {
            ExpandableView.prototype.initialize.call(this, attributes);
            BASE_MVC.SelectableViewMixin.initialize.call(this, attributes);
            BASE_MVC.DraggableViewMixin.initialize.call(this, attributes);
            this._setUpListeners();
        },

        /** event listeners */
        _setUpListeners: function () {
            // hide the primary actions in the title bar when selectable and narrow
            this.on(
                "selectable",
                function (isSelectable) {
                    if (isSelectable) {
                        this.$(".primary-actions").hide();
                    } else {
                        this.$(".primary-actions").show();
                    }
                },
                this
            );
            return this;
        },

        // ........................................................................ rendering
        /** In this override, call methods to build warnings, titlebar and primary actions */
        _buildNewRender: function () {
            var $newRender = ExpandableView.prototype._buildNewRender.call(this);
            $newRender.children(".warnings").replaceWith(this._renderWarnings());
            $newRender.children(".title-bar").replaceWith(this._renderTitleBar());
            $newRender.children(".primary-actions").append(this._renderPrimaryActions());
            $newRender.find("> .title-bar .subtitle").replaceWith(this._renderSubtitle());
            return $newRender;
        },

        /** In this override, render the selector controls and set up dragging before the swap */
        _swapNewRender: function ($newRender) {
            ExpandableView.prototype._swapNewRender.call(this, $newRender);
            if (this.selectable) {
                this.showSelector(0);
            }
            if (this.draggable) {
                this.draggableOn();
            }
            return this.$el;
        },

        /** Render any warnings the item may need to show (e.g. "I'm deleted") */
        _renderWarnings: function () {
            var view = this;
            var $warnings = $('<div class="warnings"></div>');
            var json = view.model.toJSON();
            //TODO:! unordered (map)
            _.each(view.templates.warnings, (templateFn) => {
                $warnings.append($(templateFn(json, view)));
            });
            return $warnings;
        },

        /** Render the title bar (the main/exposed SUMMARY dom element) */
        _renderTitleBar: function () {
            return $(this.templates.titleBar(this.model.toJSON(), this));
        },

        /** Return an array of jQ objects containing common/easily-accessible item controls */
        _renderPrimaryActions: function () {
            // override this
            return [];
        },

        /** Render the title bar (the main/exposed SUMMARY dom element) */
        _renderSubtitle: function () {
            return $(this.templates.subtitle(this.model.toJSON(), this));
        },

        // ......................................................................... events
        /** event map */
        events: {
            // expand the body when the title is clicked or when in focus and space or enter is pressed
            "click .title-bar": "_clickTitleBar",
            "keydown .title-bar": "_keyDownTitleBar",
            "click .selector": "toggleSelect",
        },

        /** expand when the title bar is clicked */
        _clickTitleBar: function (event) {
            event.stopPropagation();
            if (event.altKey) {
                this.toggleSelect(event);
                if (!this.selectable) {
                    this.showSelector();
                }
            } else {
                this.toggleExpanded();
            }
        },

        /** expand when the title bar is in focus and enter or space is pressed */
        _keyDownTitleBar: function (event) {
            // bail (with propagation) if keydown and not space or enter
            var KEYCODE_SPACE = 32;

            var KEYCODE_RETURN = 13;
            if (
                event &&
                event.type === "keydown" &&
                (event.keyCode === KEYCODE_SPACE || event.keyCode === KEYCODE_RETURN)
            ) {
                this.toggleExpanded();
                event.stopPropagation();
                return false;
            }
            return true;
        },

        // ......................................................................... misc
        /** String representation */
        toString: function () {
            var modelString = this.model ? `${this.model}` : "(no model)";
            return `ListItemView(${modelString})`;
        },
    })
);

// ............................................................................ TEMPLATES
/** underscore templates */
ListItemView.prototype.templates = (() => {
    var elTemplato = BASE_MVC.wrapTemplate([
        '<div class="list-element">',
        // errors, messages, etc.
        '<div class="warnings"></div>',

        // multi-select checkbox
        '<div class="selector">',
        '<span class="fa fa-2x fa-square-o"></span>',
        "</div>",
        // space for title bar buttons - gen. floated to the right
        '<div class="primary-actions"></div>',
        '<div class="title-bar"></div>',

        // expandable area for more details
        '<div class="details"></div>',
        "</div>",
    ]);

    var warnings = {};

    var titleBarTemplate = BASE_MVC.wrapTemplate(
        [
            // adding a tabindex here allows focusing the title bar and the use of keydown to expand the dataset display
            '<div class="title-bar clear" tabindex="0">',
            //TODO: prob. belongs in dataset-list-item
            '<span class="state-icon"></span>',
            '<div class="title">',
            '<span class="name"><%- element.name %></span>',
            "</div>",
            '<div class="subtitle"></div>',
            "</div>",
        ],
        "element"
    );

    var subtitleTemplate = BASE_MVC.wrapTemplate([
        // override this
        '<div class="subtitle"></div>',
    ]);

    var detailsTemplate = BASE_MVC.wrapTemplate([
        // override this
        '<div class="details"></div>',
    ]);

    return {
        el: elTemplato,
        warnings: warnings,
        titleBar: titleBarTemplate,
        subtitle: subtitleTemplate,
        details: detailsTemplate,
    };
})();

//==============================================================================
/** A view that is displayed in some larger list/grid/collection.
 *  *AND* can display some sub-list of it's own when expanded (e.g. dataset collections).
 *  This list will 'foldout' when the item is expanded depending on this.foldoutStyle:
 *      If 'foldout': will expand vertically to show the nested list
 *      If 'drilldown': will overlay the parent list
 *
 *  Inherits from ListItemView.
 *
 *  _renderDetails does the work of creating this.details: a sub-view that shows the nested list
 */
export var FoldoutListItemView = ListItemView.extend({
    /** If 'foldout': show the sub-panel inside the expanded item
     *  If 'drilldown': only fire events and handle by pub-sub
     *      (allow the panel containing this item to attach it, hide itself, etc.)
     */
    foldoutStyle: "foldout",
    /** Panel view class to instantiate for the sub-panel */
    foldoutPanelClass: null,

    /** override to:
     *      add attributes foldoutStyle and foldoutPanelClass for config poly
     *      disrespect attributes.expanded if drilldown
     */
    initialize: function (attributes) {
        if (this.foldoutStyle === "drilldown") {
            this.expanded = false;
        }
        this.foldoutStyle = attributes.foldoutStyle || this.foldoutStyle;
        this.foldoutPanelClass = attributes.foldoutPanelClass || this.foldoutPanelClass;

        ListItemView.prototype.initialize.call(this, attributes);
        this.foldout = this._createFoldoutPanel();
    },

    /** in this override, attach the foldout panel when rendering details */
    _renderDetails: function () {
        if (this.foldoutStyle === "drilldown") {
            return $();
        }
        var $newDetails = ListItemView.prototype._renderDetails.call(this);
        return this._attachFoldout(this.foldout, $newDetails);
    },

    /** In this override, handle collection expansion. */
    _createFoldoutPanel: function () {
        var model = this.model;
        var FoldoutClass = this._getFoldoutPanelClass(model);
        var options = this._getFoldoutPanelOptions(model);

        return new FoldoutClass(
            _.extend(options, {
                model: model,
            })
        );
    },

    /** Stub to return proper foldout panel class */
    _getFoldoutPanelClass: function () {
        // override
        return this.foldoutPanelClass;
    },

    /** Stub to return proper foldout panel options */
    _getFoldoutPanelOptions: function () {
        return {
            // propagate foldout style down
            foldoutStyle: this.foldoutStyle,
            fxSpeed: this.fxSpeed,
        };
    },

    /** Render the foldout panel inside the view, hiding controls */
    _attachFoldout: function (foldout, $whereTo) {
        $whereTo = $whereTo || this.$("> .details");
        this.foldout = foldout.render(0);
        foldout.$("> .controls").hide();
        return $whereTo.append(foldout.$el);
    },

    /** In this override, branch on foldoutStyle to show expanded */
    expand: function () {
        var view = this;
        return view._fetchModelDetails().always(() => {
            if (view.foldoutStyle === "foldout") {
                view._expand();
            } else if (view.foldoutStyle === "drilldown") {
                view._expandByDrilldown();
            }
        });
    },

    /** For drilldown, set up close handler and fire expanded:drilldown
     *      containing views can listen to this and handle other things
     *      (like hiding themselves) by listening for expanded/collapsed:drilldown
     */
    _expandByDrilldown: function () {
        var view = this;
        // attachment and rendering done by listener
        view.listenTo(view.foldout, "close", () => {
            view.trigger("collapsed:drilldown", view, view.foldout);
        });
        view.trigger("expanded:drilldown", view, view.foldout);
    },
});

// ............................................................................ TEMPLATES
/** underscore templates */
FoldoutListItemView.prototype.templates = (() => {
    var detailsTemplate = BASE_MVC.wrapTemplate(
        [
            '<div class="details">',
            // override with more info (that goes above the panel)
            "</div>",
        ],
        "collection"
    );

    return _.extend({}, ListItemView.prototype.templates, {
        details: detailsTemplate,
    });
})();

//==============================================================================
export default {
    ExpandableView: ExpandableView,
    ListItemView: ListItemView,
    FoldoutListItemView: FoldoutListItemView,
};
