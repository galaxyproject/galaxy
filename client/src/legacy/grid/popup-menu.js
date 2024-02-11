// =============================================================================
/**
 * view for a popup menu
 */
import Backbone from "backbone";
import $ from "jquery";
import _ from "underscore";

const PopupMenu = Backbone.View.extend({
    //TODO: maybe better as singleton off the Galaxy obj
    /** Cache the desired button element and options, set up the button click handler
     *  NOTE: attaches this view as HTML/jQ data on the button for later use.
     */
    initialize: function ($button, options) {
        // default settings
        this.$button = $button;
        if (!this.$button.length) {
            this.$button = $("<div/>");
        }
        this.options = options || [];
        this.$button.data("popupmenu", this);

        // set up button click -> open menu behavior
        this.$button.click((event) => {
            // if there's already a menu open, remove it
            $(".popmenu-wrapper").remove();
            this._renderAndShow(event);
            return false;
        });
    },

    // render the menu, append to the page body at the click position, and set up the 'click-away' handlers, show
    _renderAndShow: function (clickEvent) {
        this.render();
        this.$el.appendTo("body").css(this._getShownPosition(clickEvent)).show();
        this._setUpCloseBehavior();
    },

    // render the menu
    // this menu doesn't attach itself to the DOM ( see _renderAndShow )
    render: function () {
        // render the menu body absolute and hidden, fill with template
        this.$el
            .addClass("popmenu-wrapper")
            .hide()
            .css({ position: "absolute" })
            .html(this.template(this.$button.attr("id"), this.options));

        // set up behavior on each link/anchor elem
        if (this.options.length) {
            this.$(".popupmenu-option").each((i, el) => {
                const option = this.options[i];
                // if the option has 'func', call that function when the anchor is clicked
                if (option.func) {
                    $(el).click((event) => {
                        option.func.call(this, event, option);
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

    template: function (id, options) {
        return `<div id="${id}-menu" class="dropdown-menu ${id}-menu">
                    ${this._templateOptions(options)}
                </div>`;
    },

    _templateOptions: function (options) {
        if (!options.length) {
            return '<div class="dropdown-header">(no options)</div>';
        }
        return _.map(options, (option) => {
            if (option.divider) {
                return '<div class="popupmenu-option dropdown-divider"/>';
            } else if (option.header) {
                return `<div class="popupmenu-option dropdown-header">${option.html}</div>`;
            }
            const href = option.href || "javascript:void(0);";
            const target = option.target ? `target="${option.target}"` : "";
            const check = option.checked ? '<span class="fa fa-check mr-1"/>' : "";
            const title = option.title ? `title="${option.title}"` : "";
            return `<a class="popupmenu-option dropdown-item" href="${href}" ${title} ${target}>${check}${option.html}</a>`;
        }).join("");
    },

    // get the absolute position/offset for the menu
    _getShownPosition: function (clickEvent) {
        // display menu horiz. centered on click...
        const menuWidth = this.$el.width();
        let x = clickEvent.pageX - menuWidth / 2;

        // adjust to handle horiz. scroll and window dimensions ( draw entirely on visible screen area )
        x = Math.min(x, $(document).scrollLeft() + $(window).width() - menuWidth - 5);
        x = Math.max(x, $(document).scrollLeft() + 5);
        return {
            top: clickEvent.pageY,
            left: x,
        };
    },

    // bind an event handler to all available frames so that when anything is clicked
    // the menu is removed from the DOM and the event handler unbinds itself
    _setUpCloseBehavior: function () {
        //TODO: alternately: focus hack, blocking overlay, jquery.blockui

        // function to close popup and unbind itself
        const closePopup = (event) => {
            //do nothing if header item is clicked
            if (event.target.classList.contains("dropdown-header")) {
                return;
            }
            $(document).off("click.close_popup");
            try {
                if (window && window.parent !== window) {
                    $(window.parent.document).off("click.close_popup");
                } else {
                    $("iframe#galaxy_main").contents().off("click.close_popup");
                }
            } catch (err) {
                if (err instanceof DOMException) {
                    console.debug(
                        "Error clearing parent popups, likely cross-origin frame access from the toolshed and not problematic."
                    );
                } else {
                    console.debug(err);
                }
            }
            this.remove();
        };

        $("html").on("click.close_popup", closePopup);
        try {
            if (window && window.parent !== window) {
                $(window.parent.document).find("html").on("click.close_popup", closePopup);
            } else {
                $("iframe#galaxy_main").contents().on("click.close_popup", closePopup);
            }
        } catch (err) {
            if (err instanceof DOMException) {
                console.debug(
                    "Error clearing parent popups, likely cross-origin frame access from the toolshed and not problematic."
                );
            } else {
                console.debug(err);
            }
        }
    },

    // add a menu option/item at the given index
    addItem: function (item, index) {
        // append to end if no index
        index = index >= 0 ? index : this.options.length;
        this.options.splice(index, 0, item);
        return this;
    },

    // remove a menu option/item at the given index
    removeItem: function (index) {
        if (index >= 0) {
            this.options.splice(index, 1);
        }
        return this;
    },

    // search for a menu option by its html
    findIndexByHtml: function (html) {
        for (let i = 0; i < this.options.length; i++) {
            if (_.has(this.options[i], "html") && this.options[i].html === html) {
                return i;
            }
        }
        return null;
    },

    // search for a menu option by its html
    findItemByHtml: function (html) {
        return this.options[this.findIndexByHtml(html)];
    },

    // string representation
    toString: function () {
        return "PopupMenu";
    },
});
/** shortcut to new for when you don't need to preserve the ref */
PopupMenu.create = function _create($button, options) {
    return new PopupMenu($button, options);
};

// =============================================================================
export default PopupMenu;
