import jQuery from "jquery";
import _ from "underscore";

var $ = jQuery;
//==============================================================================
/**
 *  Template function that produces a bootstrap dropdown to replace the
 *  vanilla HTML select input. Pass in an array of options and an initial selection:
 *  $( '.my-div' ).append( dropDownSelect( [ 'option1', 'option2' ], 'option2' );
 *
 *  When the user changes the selected option a 'change.dropdown-select' event will
 *  fire with both the jq event and the new selection text as arguments.
 *
 *  Get the currently selected choice using:
 *  var userChoice = $( '.my-div .dropdown-select .dropdown-select-selected' ).text();
 *
 */
function dropDownSelect(options, selected) {
    // replacement for vanilla select element using bootstrap dropdowns instead
    selected = selected || (!_.isEmpty(options) ? options[0] : "");
    var $select = $(
        [
            '<div class="dropdown-select btn-group">',
            '<button type="button" class="btn btn-secondary">',
            `<span class="dropdown-select-selected">${selected}</span>`,
            "</button>",
            "</div>"
        ].join("\n")
    );

    // if there's only one option, do not style/create as buttons, dropdown - use simple span
    // otherwise, a dropdown displaying the current selection
    if (options && options.length > 1) {
        $select
            .find("button")
            .addClass("dropdown-toggle")
            .attr("data-toggle", "dropdown")
            .append(' <span class="caret"></span>');
        $select.append(
            [
                '<ul class="dropdown-menu" role="menu">',
                _.map(options, option => ['<li><a href="javascript:void(0)">', option, "</a></li>"].join("")).join(
                    "\n"
                ),
                "</ul>"
            ].join("\n")
        );
    }

    // trigger 'change.dropdown-select' when a new selection is made using the dropdown
    function selectThis(event) {
        var $this = $(this);
        var $select = $this.parents(".dropdown-select");
        var newSelection = $this.text();
        $select.find(".dropdown-select-selected").text(newSelection);
        $select.trigger("change.dropdown-select", newSelection);
    }

    $select.find("a").click(selectThis);
    return $select;
}

//==============================================================================
/**
 *  Creates a three part bootstrap button group (key, op, value) meant to
 *  allow the user control of filters (e.g. { key: 'name', op: 'contains', value: 'my_history' })
 *
 *  Each field uses a dropDownSelect (from ui.js) to allow selection
 *  (with the 'value' field appearing as an input when set to do so).
 *
 *  Any change or update in any of the fields will trigger a 'change.filter-control'
 *  event which will be passed an object containing those fields (as the example above).
 *
 *  Pass in an array of possible filter objects to control what the user can select.
 *  Each filter object should have:
 *      key : generally the attribute name on which to filter something
 *      ops : an array of 1 or more filter operations (e.g. [ 'is', '<', 'contains', '!=' ])
 *      values (optional) : an array of possible values for the filter (e.g. [ 'true', 'false' ])
 *  @example:
 *  $( '.my-div' ).filterControl({
 *      filters : [
 *          { key: 'name',    ops: [ 'is exactly', 'contains' ] }
 *          { key: 'deleted', ops: [ 'is' ], values: [ 'true', 'false' ] }
 *      ]
 *  });
 *  // after initialization, you can prog. get the current value using:
 *  $( '.my-div' ).filterControl( 'val' )
 *
 */
function FilterControl(element, options) {
    return this.init(element, options);
}
/** the data key that this object will be stored under in the DOM element */
FilterControl.prototype.DATA_KEY = "filter-control";

/** parses options, sets up instance vars, and does initial render */
FilterControl.prototype.init = function _init(element, options) {
    options = options || { filters: [] };
    this.$element = $(element).addClass("filter-control btn-group");
    this.options = jQuery.extend(true, {}, this.defaults, options);

    this.currFilter = this.options.filters[0];
    return this.render();
};

/** render (or re-render) the controls on the element */
FilterControl.prototype.render = function _render() {
    this.$element.empty().append([this._renderKeySelect(), this._renderOpSelect(), this._renderValueInput()]);
    return this;
};

/** render the key dropDownSelect, bind a change event to it, and return it */
FilterControl.prototype._renderKeySelect = function __renderKeySelect() {
    var filterControl = this;
    var keys = this.options.filters.map(filter => filter.key);
    this.$keySelect = dropDownSelect(keys, this.currFilter.key)
        .addClass("filter-control-key")
        .on("change.dropdown-select", (event, selection) => {
            filterControl.currFilter = _.findWhere(filterControl.options.filters, { key: selection });
            // when the filter/key changes, re-render the control entirely
            filterControl.render()._triggerChange();
        });
    return this.$keySelect;
};

/** render the op dropDownSelect, bind a change event to it, and return it */
FilterControl.prototype._renderOpSelect = function __renderOpSelect() {
    var filterControl = this;
    var ops = this.currFilter.ops;
    //TODO: search for currOp in avail. ops: use that for selected if there; otherwise: first op
    this.$opSelect = dropDownSelect(ops, ops[0])
        .addClass("filter-control-op")
        .on("change.dropdown-select", (event, selection) => {
            filterControl._triggerChange();
        });
    return this.$opSelect;
};

/** render the value control, bind a change event to it, and return it */
FilterControl.prototype._renderValueInput = function __renderValueInput() {
    var filterControl = this;
    // if a values attribute is prov. on the filter - make this a dropdown; otherwise, use an input
    if (this.currFilter.values) {
        this.$valueSelect = dropDownSelect(this.currFilter.values, this.currFilter.values[0]).on(
            "change.dropdown-select",
            (event, selection) => {
                filterControl._triggerChange();
            }
        );
    } else {
        //TODO: allow setting a value type (mainly for which html5 input to use: range, number, etc.)
        this.$valueSelect = $("<input/>")
            .addClass("form-control")
            .on("change", (event, value) => {
                filterControl._triggerChange();
            });
    }
    this.$valueSelect.addClass("filter-control-value");
    return this.$valueSelect;
};

/** return the current state/setting for the filter as a three key object: key, op, value */
FilterControl.prototype.val = function _val() {
    var key = this.$element.find(".filter-control-key .dropdown-select-selected").text();

    var op = this.$element.find(".filter-control-op .dropdown-select-selected").text();

    var // handle either a dropdown or plain input
        $value = this.$element.find(".filter-control-value");

    var value = $value.hasClass("dropdown-select") ? $value.find(".dropdown-select-selected").text() : $value.val();

    return { key: key, op: op, value: value };
};

// single point of change for change event
FilterControl.prototype._triggerChange = function __triggerChange() {
    this.$element.trigger("change.filter-control", this.val());
};

// as jq plugin
jQuery.fn.extend({
    filterControl: function $filterControl(options) {
        var nonOptionsArgs = jQuery.makeArray(arguments).slice(1);
        return this.map(function() {
            var $this = $(this);
            var data = $this.data(FilterControl.prototype.DATA_KEY);

            if (jQuery.type(options) === "object") {
                data = new FilterControl($this, options);
                $this.data(FilterControl.prototype.DATA_KEY, data);
            }
            if (data && jQuery.type(options) === "string") {
                var fn = data[options];
                if (jQuery.type(fn) === "function") {
                    return fn.apply(data, nonOptionsArgs);
                }
            }
            return this;
        });
    }
});
