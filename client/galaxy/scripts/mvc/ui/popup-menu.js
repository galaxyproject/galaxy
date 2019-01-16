// =============================================================================
/**
 * view for a popup menu
 */
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
var PopupMenu = Backbone.View.extend({
    //TODO: maybe better as singleton off the Galaxy obj
    /** Cache the desired button element and options, set up the button click handler
     *  NOTE: attaches this view as HTML/jQ data on the button for later use.
     */
    initialize: function($button, options) {
        // default settings
        this.$button = $button;
        if (!this.$button.length) {
            this.$button = $("<div/>");
        }
        this.options = options || [];
        this.$button.data("popupmenu", this);

        // set up button click -> open menu behavior
        var menu = this;
        this.$button.click(event => {
            // if there's already a menu open, remove it
            $(".popmenu-wrapper").remove();
            menu._renderAndShow(event);
            return false;
        });
    },

    // render the menu, append to the page body at the click position, and set up the 'click-away' handlers, show
    _renderAndShow: function(clickEvent) {
        this.render();
        this.$el
            .appendTo("body")
            .css(this._getShownPosition(clickEvent))
            .show();
        this._setUpCloseBehavior();
    },

    // render the menu
    // this menu doesn't attach itself to the DOM ( see _renderAndShow )
    render: function() {
        // render the menu body absolute and hidden, fill with template
        this.$el
            .addClass("popmenu-wrapper")
            .hide()
            .css({ position: "absolute" })
            .html(this.template(this.$button.attr("id"), this.options));

        // set up behavior on each link/anchor elem
        if (this.options.length) {
            var menu = this;
            //precondition: there should be one option per li
            this.$el.find("li").each(function(i, li) {
                var option = menu.options[i];

                // if the option has 'func', call that function when the anchor is clicked
                if (option.func) {
                    $(this)
                        .children("a.popupmenu-option")
                        .click(event => {
                            option.func.call(menu, event, option);
                            // We must preventDefault otherwise clicking "cancel"
                            // on a purge or something still navigates and causes
                            // the action.
                            event.preventDefault();
                            // bubble up so that an option click will call the close behavior
                        });
                }
            });
        }
        return this;
    },

    template: function(id, options) {
        return ['<ul id="', id, '-menu" class="dropdown-menu">', this._templateOptions(options), "</ul>"].join("");
    },

    _templateOptions: function(options) {
        if (!options.length) {
            return "<li>(no options)</li>";
        }
        return _.map(options, option => {
            if (option.divider) {
                return '<li class="divider"></li>';
            } else if (option.header) {
                return ['<li class="head"><a href="javascript:void(0);">', option.html, "</a></li>"].join("");
            }
            var href = option.href || "javascript:void(0);";
            var target = option.target ? ` target="${option.target}"` : "";

            var check = option.checked ? '<span class="fa fa-check"></span>' : "";

            return [
                '<li><a class="popupmenu-option" href="',
                href,
                '"',
                target,
                ">",
                check,
                option.html,
                "</a></li>"
            ].join("");
        }).join("");
    },

    // get the absolute position/offset for the menu
    _getShownPosition: function(clickEvent) {
        // display menu horiz. centered on click...
        var menuWidth = this.$el.width();
        var x = clickEvent.pageX - menuWidth / 2;

        // adjust to handle horiz. scroll and window dimensions ( draw entirely on visible screen area )
        x = Math.min(x, $(document).scrollLeft() + $(window).width() - menuWidth - 5);
        x = Math.max(x, $(document).scrollLeft() + 5);
        return {
            top: clickEvent.pageY,
            left: x
        };
    },

    // bind an event handler to all available frames so that when anything is clicked
    // the menu is removed from the DOM and the event handler unbinds itself
    _setUpCloseBehavior: function() {
        var menu = this;
        //TODO: alternately: focus hack, blocking overlay, jquery.blockui

        // function to close popup and unbind itself
        function closePopup(event) {
            $(document).off("click.close_popup");
            if (window && window.parent !== window) {
                try {
                    $(window.parent.document).off("click.close_popup");
                } catch (err) {
                    console.debug(err);
                }
            } else {
                try {
                    $("iframe#galaxy_main")
                        .contents()
                        .off("click.close_popup");
                } catch (err) {
                    console.debug(err);
                }
            }
            menu.remove();
        }

        $("html").one("click.close_popup", closePopup);
        if (window && window.parent !== window) {
            try {
                $(window.parent.document)
                    .find("html")
                    .one("click.close_popup", closePopup);
            } catch (err) {
                console.debug(err);
            }
        } else {
            try {
                $("iframe#galaxy_main")
                    .contents()
                    .one("click.close_popup", closePopup);
            } catch (err) {
                console.debug(err);
            }
        }
    },

    // add a menu option/item at the given index
    addItem: function(item, index) {
        // append to end if no index
        index = index >= 0 ? index : this.options.length;
        this.options.splice(index, 0, item);
        return this;
    },

    // remove a menu option/item at the given index
    removeItem: function(index) {
        if (index >= 0) {
            this.options.splice(index, 1);
        }
        return this;
    },

    // search for a menu option by its html
    findIndexByHtml: function(html) {
        for (var i = 0; i < this.options.length; i++) {
            if (_.has(this.options[i], "html") && this.options[i].html === html) {
                return i;
            }
        }
        return null;
    },

    // search for a menu option by its html
    findItemByHtml: function(html) {
        return this.options[this.findIndexByHtml(html)];
    },

    // string representation
    toString: function() {
        return "PopupMenu";
    }
});
/** shortcut to new for when you don't need to preserve the ref */
PopupMenu.create = function _create($button, options) {
    return new PopupMenu($button, options);
};

// -----------------------------------------------------------------------------
// the following class functions are bridges from the original make_popupmenu and make_popup_menus
// to the newer backbone.js PopupMenu

/** Create a PopupMenu from simple map initial_options activated by clicking button_element.
 *      Converts initial_options to object array used by PopupMenu.
 *  @param {jQuery|DOMElement} button_element element which, when clicked, activates menu
 *  @param {Object} initial_options map of key -> values, where
 *      key is option text, value is fn to call when option is clicked
 *  @returns {PopupMenu} the PopupMenu created
 */
PopupMenu.make_popupmenu = (button_element, initial_options) => {
    var convertedOptions = [];
    _.each(initial_options, (optionVal, optionKey) => {
        var newOption = { html: optionKey };

        // keys with null values indicate: header
        if (optionVal === null) {
            // !optionVal? (null only?)
            newOption.header = true;

            // keys with function values indicate: a menu option
        } else if ($.type(optionVal) === "function") {
            newOption.func = optionVal;
        }
        //TODO:?? any other special optionVals?
        // there was no divider option originally
        convertedOptions.push(newOption);
    });
    return new PopupMenu($(button_element), convertedOptions);
};

/** Find all anchors in $parent (using selector) and covert anchors into a PopupMenu options map.
 *  @param {jQuery} $parent the element that contains the links to convert to options
 *  @param {String} selector jq selector string to find links
 *  @returns {Object[]} the options array to initialize a PopupMenu
 */
//TODO: lose parent and selector, pass in array of links, use map to return options
PopupMenu.convertLinksToOptions = ($parent, selector) => {
    $parent = $($parent);
    selector = selector || "a";
    var options = [];
    $parent.find(selector).each((elem, i) => {
        var option = {};
        var $link = $(elem);

        // convert link text to the option text (html) and the href into the option func
        option.html = $link.text();
        if ($link.attr("href")) {
            var linkHref = $link.attr("href");
            var linkTarget = $link.attr("target");
            var confirmText = $link.attr("confirm");

            option.func = () => {
                // if there's a "confirm" attribute, throw up a confirmation dialog, and
                //  if the user cancels - do nothing
                if (confirmText && !confirm(confirmText)) {
                    return;
                }

                // if there's no confirm attribute, or the user accepted the confirm dialog:
                switch (linkTarget) {
                    // relocate the center panel
                    case "_parent":
                        window.parent.location = linkHref;
                        break;

                    // relocate the entire window
                    case "_top":
                        window.top.location = linkHref;
                        break;

                    // relocate this panel
                    default:
                        window.location = linkHref;
                }
            };
        }
        options.push(option);
    });
    return options;
};

/** Create a single popupmenu from existing DOM button and anchor elements
 *  @param {jQuery} $buttonElement the element that when clicked will open the menu
 *  @param {jQuery} $menuElement the element that contains the anchors to convert into a menu
 *  @param {String} menuElementLinkSelector jq selector string used to find anchors to be made into menu options
 *  @returns {PopupMenu} the PopupMenu (Backbone View) that can render, control the menu
 */
PopupMenu.fromExistingDom = ($buttonElement, $menuElement, menuElementLinkSelector) => {
    $buttonElement = $($buttonElement);
    $menuElement = $($menuElement);
    var options = PopupMenu.convertLinksToOptions($menuElement, menuElementLinkSelector);
    // we're done with the menu (having converted it to an options map)
    $menuElement.remove();
    return new PopupMenu($buttonElement, options);
};

/** Create all popupmenus within a document or a more specific element
 *  @param {DOMElement} parent the DOM element in which to search for popupmenus to build (defaults to document)
 *  @param {String} menuSelector jq selector string to find popupmenu menu elements (defaults to "div[popupmenu]")
 *  @param {Function} buttonSelectorBuildFn the function to build the jq button selector.
 *      Will be passed $menuElement, parent.
 *      (Defaults to return '#' + $menuElement.attr( 'popupmenu' ); )
 *  @returns {PopupMenu[]} array of popupmenus created
 */
PopupMenu.make_popup_menus = (parent, menuSelector, buttonSelectorBuildFn) => {
    parent = parent || document;
    // orig. Glx popupmenu menus have a (non-std) attribute 'popupmenu'
    //  which contains the id of the button that activates the menu
    menuSelector = menuSelector || "div[popupmenu]";
    // default to (orig. Glx) matching button to menu by using the popupmenu attr of the menu as the id of the button
    buttonSelectorBuildFn = buttonSelectorBuildFn || (($menuElement, parent) => `#${$menuElement.attr("popupmenu")}`);

    // aggregate and return all PopupMenus
    var popupMenusCreated = [];
    $(parent)
        .find(menuSelector)
        .each(function() {
            var $menuElement = $(this);

            var $buttonElement = $(parent).find(buttonSelectorBuildFn($menuElement, parent));

            popupMenusCreated.push(PopupMenu.fromDom($buttonElement, $menuElement));
            $buttonElement.addClass("popup");
        });
    return popupMenusCreated;
};

// =============================================================================
export default PopupMenu;
