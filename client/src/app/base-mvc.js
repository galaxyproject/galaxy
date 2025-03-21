import Backbone from "backbone";
import $ from "jquery";
import _ from "underscore";
import _l from "utils/localization";

//==============================================================================
/** Backbone model that syncs to the browser's sessionStorage API.
 *      This all largely happens behind the scenes and no special calls are required.
 */
var SessionStorageModel = Backbone.Model.extend({
    initialize: function (initialAttrs) {
        // check for sessionStorage and error if no id is provided
        this._checkEnabledSessionStorage();
        if (!initialAttrs.id) {
            throw new Error("SessionStorageModel 在初始属性中需要一个 id");
        }
        this.id = initialAttrs.id;

        // load existing from storage (if any), clear any attrs set by bbone before init is called,
        //  layer initial over existing and defaults, and save
        var existing = !this.isNew() ? this._read(this) : {};
        this.clear({ silent: true });
        this.save(_.extend({}, this.defaults, existing, initialAttrs), {
            silent: true,
        });

        // save on any change to it immediately
        this.on("change", function () {
            this.save();
        });
    },

    _checkEnabledSessionStorage: function () {
        try {
            return window.sessionStorage.length >= 0;
        } catch (err) {
            alert("请在浏览器中启用 cookies，以便使用网站");
            return false;
        }
    },

    /** override of bbone sync to save to sessionStorage rather than REST
     *      bbone options (success, errror, etc.) should still apply
     */
    sync: function (method, model, options) {
        if (!options.silent) {
            model.trigger("request", model, {}, options);
        }
        var returned = {};
        switch (method) {
            case "create":
                returned = this._create(model);
                break;
            case "read":
                returned = this._read(model);
                break;
            case "update":
                returned = this._update(model);
                break;
            case "delete":
                returned = this._delete(model);
                break;
        }
        if (returned !== undefined || returned !== null) {
            if (options.success) {
                options.success();
            }
        } else {
            if (options.error) {
                options.error();
            }
        }
        return returned;
    },

    /** set storage to the stringified item */
    _create: function (model) {
        try {
            var json = model.toJSON();
            var set = sessionStorage.setItem(model.id, JSON.stringify(json));
            return set === null ? set : json;
            // DOMException is thrown in Safari if in private browsing mode and sessionStorage is attempted:
            // http://stackoverflow.com/questions/14555347
            // TODO: this could probably use a more general soln - like detecting priv. mode + safari => non-ajaxing Model
        } catch (err) {
            if (!(err instanceof DOMException && navigator.userAgent.indexOf("Safari") > -1)) {
                throw err;
            }
        }
        return null;
    },

    /** read and parse json from storage */
    _read: function (model) {
        return JSON.parse(sessionStorage.getItem(model.id));
    },

    /** set storage to the item (alias to create) */
    _update: function (model) {
        return model._create(model);
    },

    /** remove the item from storage */
    _delete: function (model) {
        return sessionStorage.removeItem(model.id);
    },

    /** T/F whether sessionStorage contains the model's id (data is present) */
    isNew: function () {
        return !Object.prototype.hasOwnProperty.call(sessionStorage, this.id);
    },

    _log: function () {
        return JSON.stringify(this.toJSON(), null, "  ");
    },
    toString: function () {
        return `SessionStorageModel(${this.id})`;
    },
});
(() => {
    SessionStorageModel.prototype = _.omit(SessionStorageModel.prototype, "url", "urlRoot");
})();

//==============================================================================
/** Function that allows mixing of hashs into bbone MVC while showing the mixins first
 *      (before the more local class overrides/hash).
 *      Basically, a simple reversal of param order on _.defaults() - to show mixins in top of definition.
 *  @example:
 *      var NewModel = Something.extend( mixin( MyMixinA, MyMixinB, { ... myVars : ... }) );
 *
 *  NOTE: this does not combine any hashes (like events, etc.) and you're expected to handle that
 */
function mixin(mixinHash1, /* mixinHash2, etc: ... variadic */ propsHash) {
    var args = Array.prototype.slice.call(arguments, 0);
    var lastArg = args.pop();
    args.unshift(lastArg);
    return _.defaults.apply(_, args);
}

//==============================================================================
/** A mixin for models that allow T/F/Matching to their attributes - useful when
 *      searching or filtering collections of models.
 * @example:
 *      see hda-model for searchAttribute and searchAliases definition examples.
 *      see history-contents.matches for how collections are filtered
 *      and see readonly-history-view.searchHdas for how user input is connected to the filtering
 */
var SearchableModelMixin = {
    /** what attributes of an HDA will be used in a text search */
    searchAttributes: [
        // override
    ],

    /** our attr keys don't often match the labels we display to the user - so, when using
     *      attribute specifiers ('name="bler"') in a term, allow passing in aliases for the
     *      following attr keys.
     */
    searchAliases: {
        // override
    },

    /** search the attribute with key attrKey for the string searchFor; T/F if found */
    searchAttribute: function (attrKey, searchFor) {
        var attrVal = this.get(attrKey);
        //console.debug( 'searchAttribute', attrKey, attrVal, searchFor );
        // bail if empty searchFor or unsearchable values
        if (!searchFor || attrVal === undefined || attrVal === null) {
            return false;
        }
        // pass to sep. fn for deep search of array attributes
        if (_.isArray(attrVal)) {
            return this._searchArrayAttribute(attrVal, searchFor);
        }
        return attrVal.toString().toLowerCase().indexOf(searchFor.toLowerCase()) !== -1;
    },

    /** deep(er) search for array attributes; T/F if found */
    _searchArrayAttribute: function (array, searchFor) {
        //console.debug( '_searchArrayAttribute', array, searchFor );
        searchFor = searchFor.toLowerCase();
        //precondition: searchFor has already been validated as non-empty string
        //precondition: assumes only 1 level array
        //TODO: could possibly break up searchFor more (CSV...)
        return _.any(array, (elem) => elem.toString().toLowerCase().indexOf(searchFor.toLowerCase()) !== -1);
    },

    /** search all searchAttributes for the string searchFor,
     *      returning a list of keys of attributes that contain searchFor
     */
    search: function (searchFor) {
        var model = this;
        return _.filter(this.searchAttributes, (key) => model.searchAttribute(key, searchFor));
    },

    /** alias of search, but returns a boolean; accepts attribute specifiers where
     *      the attributes searched can be narrowed to a single attribute using
     *      the form: matches( 'genome_build=hg19' )
     *      (the attribute keys allowed can also be aliases to the true attribute key;
     *          see searchAliases above)
     *  @param {String} term   plain text or ATTR_SPECIFIER sep. key=val pair
     *  @returns {Boolean} was term found in (any) attribute(s)
     */
    matches: function (term) {
        var ATTR_SPECIFIER = "=";
        var split = term.split(ATTR_SPECIFIER);
        // attribute is specified - search only that
        if (split.length >= 2) {
            var attrKey = split[0];
            attrKey = this.searchAliases[attrKey] || attrKey;
            return this.searchAttribute(attrKey, split[1]);
        }
        // no attribute is specified - search all attributes in searchAttributes
        return !!this.search(term).length;
    },

    /** an implicit AND search for all terms; IOW, a model must match all terms given
     *      where terms is a whitespace separated value string.
     *      e.g. given terms of: 'blah bler database=hg19'
     *          an HDA would have to have attributes containing blah AND bler AND a genome_build == hg19
     *      To include whitespace in terms: wrap the term in double quotations (name="blah bler").
     */
    matchesAll: function (terms) {
        var model = this;
        // break the terms up by whitespace and filter out the empty strings
        terms = terms.match(/(".*"|\w*=".*"|\S*)/g).filter((s) => !!s);
        return _.all(terms, (term) => {
            term = term.replace(/"/g, "");
            return model.matches(term);
        });
    },
};

//==============================================================================
/** A view that renders hidden and shows when some activator is clicked.
 *      options:
 *          showFn: the effect used to show/hide the View (defaults to jq.toggle)
 *          $elementShown: some jqObject (defaults to this.$el) to be shown/hidden
 *          onShowFirstTime: fn called the first time the view is shown
 *          onshow: fn called every time the view is shown
 *          onhide: fn called every time the view is hidden
 *      events:
 *          hiddenUntilActivated:shown (the view is passed as an arg)
 *          hiddenUntilActivated:hidden (the view is passed as an arg)
 *      instance vars:
 *          view.hidden {boolean} is the view in the hidden state
 */
var HiddenUntilActivatedViewMixin = /** @lends hiddenUntilActivatedMixin# */ {
    //TODO: since this is a mixin, consider moving toggle, hidden into HUAVOptions

    /** call this in your initialize to set up the mixin
     *  @param {jQuery} $activator the 'button' that's clicked to show/hide the view
     *  @param {Object} hash with mixin options
     */
    hiddenUntilActivated: function ($activator, options) {
        // call this in your view's initialize fn
        options = options || {};
        //TODO: flesh out options - show them all here
        this.HUAVOptions = {
            $elementShown: this.$el,
            showFn: $.prototype.toggle,
            showSpeed: "fast",
        };
        _.extend(this.HUAVOptions, options || {});
        /** has this been shown already (and onshowFirstTime called)? */
        this.HUAVOptions.hasBeenShown = this.HUAVOptions.$elementShown.is(":visible");
        this.hidden = this.isHidden();

        if ($activator) {
            var mixin = this;
            $activator.on("click", (ev) => {
                mixin.toggle(mixin.HUAVOptions.showSpeed);
            });
        }
    },

    //TODO:?? remove? use .hidden?
    /** returns T/F if the view is hidden */
    isHidden: function () {
        return this.HUAVOptions.$elementShown.is(":hidden");
    },

    /** toggle the hidden state, show/hide $elementShown, call onshow/hide, trigger events */
    toggle: function () {
        //TODO: more specific name - toggle is too general
        // can be called manually as well with normal toggle arguments
        //TODO: better as a callback (when the show/hide is actually done)
        // show
        if (this.hidden) {
            // fire the optional fns on the first/each showing - good for render()
            if (!this.HUAVOptions.hasBeenShown) {
                if (_.isFunction(this.HUAVOptions.onshowFirstTime)) {
                    this.HUAVOptions.hasBeenShown = true;
                    this.HUAVOptions.onshowFirstTime.call(this);
                }
            }
            if (_.isFunction(this.HUAVOptions.onshow)) {
                this.HUAVOptions.onshow.call(this);
                this.trigger("hiddenUntilActivated:shown", this);
            }
            this.hidden = false;

            // hide
        } else {
            if (_.isFunction(this.HUAVOptions.onhide)) {
                this.HUAVOptions.onhide.call(this);
                this.trigger("hiddenUntilActivated:hidden", this);
            }
            this.hidden = true;
        }
        return this.HUAVOptions.showFn.apply(this.HUAVOptions.$elementShown, arguments);
    },
};

//==============================================================================
/** Mixin for views that can be dragged and dropped
 *      Allows for the drag behavior to be turned on/off, setting/removing jQuery event
 *          handlers each time.
 *      dataTransfer data is set to the JSON string of the view's model.toJSON
 *      Override '$dragHandle' to define the draggable DOM sub-element.
 */
var DraggableViewMixin = {
    /** set up instance vars to track whether this view is currently draggable */
    initialize: function (attributes) {
        /** is the body of this hda view expanded/not? */
        this.draggable = attributes.draggable || false;
    },

    /** what part of the view's DOM triggers the dragging */
    $dragHandle: function () {
        //TODO: make abstract/general - move this to listItem
        // override to the element you want to be your view's handle
        return this.$(".title-bar");
    },

    /** toggle whether this view is draggable */
    toggleDraggable: function () {
        if (this.draggable) {
            this.draggableOff();
        } else {
            this.draggableOn();
        }
    },

    /** allow the view to be dragged, set up event handlers */
    draggableOn: function () {
        this.draggable = true;
        this.dragStartHandler = _.bind(this._dragStartHandler, this);
        this.dragEndHandler = _.bind(this._dragEndHandler, this);

        var handle = this.$dragHandle().attr("draggable", true).get(0);
        handle.addEventListener("dragstart", this.dragStartHandler, false);
        handle.addEventListener("dragend", this.dragEndHandler, false);
    },

    /** turn of view dragging and remove event listeners */
    draggableOff: function () {
        this.draggable = false;
        var handle = this.$dragHandle().attr("draggable", false).get(0);
        handle.removeEventListener("dragstart", this.dragStartHandler, false);
        handle.removeEventListener("dragend", this.dragEndHandler, false);
    },

    /** sets the dataTransfer data to the model's toJSON
     *  @fires draggable:dragstart (bbone event) which is passed the event and this view
     */
    _dragStartHandler: function (event) {
        event.dataTransfer.effectAllowed = "move";
        //ASSUMES: this.model
        //TODO: all except IE: should be 'application/json', IE: must be 'text'
        event.dataTransfer.setData("text", JSON.stringify(this.model.toJSON()));
        this.trigger("draggable:dragstart", event, this);
        return false;
    },

    /** handle the dragend
     *  @fires draggable:dragend (bbone event) which is passed the event and this view
     */
    _dragEndHandler: function (event) {
        this.trigger("draggable:dragend", event, this);
        return false;
    },
};

//==============================================================================
/** Mixin that allows a view to be selected (gen. from a list).
 *      Selection controls ($selector) may be hidden/shown/toggled.
 *          The bbone event 'selectable' is fired when the controls are shown/hidden (passed T/F).
 *      Default rendering is a font-awesome checkbox.
 *      Default selector is '.selector' within the view's $el.
 *      The bbone events 'selected' and 'de-selected' are fired when the $selector is clicked.
 *          Both events are passed the view and the (jQuery) event.
 */
var SelectableViewMixin = {
    /** Set up instance state vars for whether the selector is shown and whether the view has been selected */
    initialize: function (attributes) {
        /** is the view currently in selection mode? */
        this.selectable = attributes.selectable || false;
        /** is the view currently selected? */
        this.selected = attributes.selected || false;
    },

    /** $el sub-element where the selector is rendered and what can be clicked to select. */
    $selector: function () {
        return this.$(".selector");
    },

    /** How the selector is rendered - defaults to font-awesome checkbox */
    _renderSelected: function () {
        // override
        this.$selector()
            .find("span")
            .toggleClass("fa-check-square-o", this.selected)
            .toggleClass("fa-square-o", !this.selected);
    },

    /** Toggle whether the selector is shown */
    toggleSelector: function () {
        //TODO: use this.selectable
        if (!this.$selector().is(":visible")) {
            this.showSelector();
        } else {
            this.hideSelector();
        }
    },

    /** Display the selector control.
     *  @param {Number} a jQuery fx speed
     *  @fires: selectable which is passed true (IOW, the selector is shown) and the view
     */
    showSelector: function (speed) {
        speed = speed !== undefined ? speed : this.fxSpeed;
        // make sure selected state is represented properly
        this.selectable = true;
        this.trigger("selectable", true, this);
        this._renderSelected();
        if (speed) {
            this.$selector().show(speed);
        } else {
            this.$selector().show();
        }
    },

    /** remove the selector control
     *  @param {Number} a jQuery fx speed
     *  @fires: selectable which is passed false (IOW, the selector is not shown) and the view
     */
    hideSelector: function (speed) {
        speed = speed !== undefined ? speed : this.fxSpeed;
        // reverse the process from showSelect
        this.selectable = false;
        this.trigger("selectable", false, this);
        if (speed) {
            this.$selector().hide(speed);
        } else {
            this.$selector().hide();
        }
    },

    /** Toggle whether the view is selected */
    toggleSelect: function (event) {
        if (this.selected) {
            this.deselect(event);
        } else {
            this.select(event);
        }
    },

    /** Select this view and re-render the selector control to show it
     *  @param {Event} a jQuery event that caused the selection
     *  @fires: selected which is passed the view and the DOM event that triggered it (optionally)
     */
    select: function (event) {
        // switch icon, set selected, and trigger event
        if (!this.selected) {
            this.trigger("selected", this, event);
            this.selected = true;
            this._renderSelected();
        }
        return false;
    },

    /** De-select this view and re-render the selector control to show it
     *  @param {Event} a jQuery event that caused the selection
     *  @fires: de-selected which is passed the view and the DOM event that triggered it (optionally)
     */
    deselect: function (event) {
        // switch icon, set selected, and trigger event
        if (this.selected) {
            this.trigger("de-selected", this, event);
            this.selected = false;
            this._renderSelected();
        }
        return false;
    },
};

//==============================================================================
/** Return an underscore template fn from an array of strings.
 *  @param {String[]} template      the template strings to compile into the underscore template fn
 *  @param {String} jsonNamespace   an optional namespace for the json data passed in (defaults to 'model')
 *  @returns {Function} the (wrapped) underscore template fn
 *      The function accepts:
 *
 *  The template strings can access:
 *      the json/model hash using model ("<%- model.myAttr %>) using the jsonNamespace above
 *      _l: the localizer function
 *      view (if passed): ostensibly, the view using the template (handy for view instance vars)
 *      Because they're namespaced, undefined attributes will not throw an error.
 *
 *  @example:
 *      templateBler : BASE_MVC.wrapTemplate([
 *          '<div class="myclass <%- mynamespace.modelClass %>">',
 *              '<span><% print( _l( mynamespace.message ) ); %>:<%= view.status %></span>'
 *          '</div>'
 *      ], 'mynamespace' )
 *
 *  Meant to be called in a View's definition in order to compile only once.
 *
 */
function wrapTemplate(template, jsonNamespace) {
    jsonNamespace = jsonNamespace || "model";
    var templateFn = _.template(template.join(""));
    return (json, view) => {
        var templateVars = { view: view || {}, _l: _l };
        templateVars[jsonNamespace] = json || {};
        return templateFn(templateVars);
    };
}

//==============================================================================
/** Return a comparator function for sorted Collections */
function buildComparator(attribute_name, options) {
    options = options || {};
    var ascending = options.ascending ? 1 : -1;
    return function __comparator(a, b) {
        a = a.get(attribute_name);
        b = b.get(attribute_name);
        return (a < b ? -1 : a > b ? 1 : 0) * ascending;
    };
}

//==============================================================================
export default {
    SessionStorageModel: SessionStorageModel,
    mixin: mixin,
    SearchableModelMixin: SearchableModelMixin,
    HiddenUntilActivatedViewMixin: HiddenUntilActivatedViewMixin,
    DraggableViewMixin: DraggableViewMixin,
    SelectableViewMixin: SelectableViewMixin,
    wrapTemplate: wrapTemplate,
    buildComparator: buildComparator,
};
