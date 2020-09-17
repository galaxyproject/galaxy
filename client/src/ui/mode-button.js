import jQuery from "jquery";
("use_strict");

var $ = jQuery;

/** Multi 'mode' button (or any element really) that changes the html
 *      contents of itself when clicked. Pass in an ordered list of
 *      objects with 'html' and (optional) onclick functions.
 *
 *      When clicked in a particular node, the onclick function will
 *      be called (with the element as this) and the element will
 *      switch to the next mode, replacing its html content with
 *      that mode's html.
 *
 *      If there is no next mode, the element will switch back to
 *      the first mode.
 * @example:
 *     $( '.myElement' ).modeButton({
 *         modes : [
 *             {
 *                 mode: 'bler',
 *                 html: '<h5>Bler</h5>',
 *                 onclick : function(){
 *                     $( 'body' ).css( 'background-color', 'red' );
 *                 }
 *             },
 *             {
 *                 mode: 'bloo',
 *                 html: '<h4>Bloo</h4>',
 *                 onclick : function(){
 *                     $( 'body' ).css( 'background-color', 'blue' );
 *                 }
 *             },
 *             {
 *                 mode: 'blah',
 *                 html: '<h3>Blah</h3>',
 *                 onclick : function(){
 *                     $( 'body' ).css( 'background-color', 'grey' );
 *                 }
 *             },
 *         ]
 *     });
 *     $( '.myElement' ).modeButton( 'callModeFn', 'bler' );
 */
/** constructor */
function ModeButton(element, options) {
    this.currModeIndex = 0;
    return this._init(element, options);
}

/** html5 data key to store this object inside an element */
ModeButton.prototype.DATA_KEY = "mode-button";
/** default options */
ModeButton.prototype.defaults = {
    switchModesOnClick: true,
};

// ---- private interface
/** set up options, intial mode, and the click handler */
ModeButton.prototype._init = function _init(element, options) {
    //console.debug( 'ModeButton._init:', element, options );
    options = options || {};
    this.$element = $(element);
    this.options = $.extend(true, {}, this.defaults, options);
    if (!options.modes) {
        throw new Error('ModeButton requires a "modes" array');
    }

    var modeButton = this;
    this.$element.click(function _ModeButtonClick(event) {
        // call the curr mode fn
        modeButton.callModeFn();
        // inc the curr mode index
        if (modeButton.options.switchModesOnClick) {
            modeButton._incModeIndex();
        }
        // set the element html
        $(this).html(modeButton.options.modes[modeButton.currModeIndex].html);
    });
    return this.reset();
};
/** increment the mode index to the next in the array, looping back to zero if at the last */
ModeButton.prototype._incModeIndex = function _incModeIndex() {
    this.currModeIndex += 1;
    if (this.currModeIndex >= this.options.modes.length) {
        this.currModeIndex = 0;
    }
    return this;
};
/** get the mode index in the modes array for the given key (mode name) */
ModeButton.prototype._getModeIndex = function _getModeIndex(modeKey) {
    for (var i = 0; i < this.options.modes.length; i += 1) {
        if (this.options.modes[i].mode === modeKey) {
            return i;
        }
    }
    throw new Error(`mode not found: ${modeKey}`);
};
/** set the current mode to the one with the given index and set button html */
ModeButton.prototype._setModeByIndex = function _setModeByIndex(index) {
    var newMode = this.options.modes[index];
    if (!newMode) {
        throw new Error(`mode index not found: ${index}`);
    }
    this.currModeIndex = index;
    if (newMode.html) {
        this.$element.html(newMode.html);
    }
    return this;
};

// ---- public interface
/** get the current mode object (not just the mode name) */
ModeButton.prototype.currentMode = function currentMode() {
    return this.options.modes[this.currModeIndex];
};
/** return the mode key of the current mode */
ModeButton.prototype.current = function current() {
    // sugar for returning mode name
    return this.currentMode().mode;
};
/** get the mode with the given modeKey or the current mode if modeKey is undefined */
ModeButton.prototype.getMode = function getMode(modeKey) {
    if (!modeKey) {
        return this.currentMode();
    }
    return this.options.modes[this._getModeIndex(modeKey)];
};
/** T/F if the button has the given mode */
ModeButton.prototype.hasMode = function hasMode(modeKey) {
    try {
        return !!this.getMode(modeKey);
    } catch (err) {
        console.debug(err);
    }
    return false;
};
/** set the current mode to the mode with the given name */
ModeButton.prototype.setMode = function setMode(modeKey) {
    return this._setModeByIndex(this._getModeIndex(modeKey));
};
/** reset to the initial mode */
ModeButton.prototype.reset = function reset() {
    this.currModeIndex = 0;
    if (this.options.initialMode) {
        this.currModeIndex = this._getModeIndex(this.options.initialMode);
    }
    return this._setModeByIndex(this.currModeIndex);
};
/** manually call the click handler of the given mode */
ModeButton.prototype.callModeFn = function callModeFn(modeKey) {
    var modeFn = this.getMode(modeKey).onclick;
    if (modeFn && $.type(modeFn === "function")) {
        // call with the element as context (std jquery pattern)
        return modeFn.call(this.$element.get(0));
    }
    return undefined;
};

// as jq plugin
$.fn.modeButton = function $modeButton(options) {
    if (!this.length) {
        return this;
    }

    //TODO: does map still work with jq multi selection (i.e. $( '.class-for-many-btns' ).modeButton)?
    if ($.type(options) === "object") {
        return this.map(function () {
            var $this = $(this);
            $this.data("mode-button", new ModeButton($this, options));
            return this;
        });
    }

    var $first = $(this[0]);
    var button = $first.data("mode-button");

    if (!button) {
        throw new Error("modeButton needs an options object or string name of a function");
    }

    if (button && $.type(options) === "string") {
        var fnName = options;
        if (button && $.type(button[fnName]) === "function") {
            return button[fnName].apply(button, $.makeArray(arguments).slice(1));
        }
    }
    return button;
};
