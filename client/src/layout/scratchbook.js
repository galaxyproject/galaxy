/** Frame manager uses the window manager to create the scratch book masthead icon and functionality **/
import _ from "underscore";
import _l from "utils/localization";
import Backbone from "backbone";
import WinBox from "winbox/src/js/winbox.js";
import "winbox/dist/css/winbox.min.css";

export default Backbone.View.extend({
    initialize: function (options) {
        options = options || {};
        this.setElement("<div />");
        this.counter = 0;
        this.active = false;
        this.buttonActive = {
            id: "enable-scratchbook",
            icon: "fa-th",
            tooltip: _l("Enable/Disable Scratchbook"),
            toggle: false,
            onclick: () => {
                this.active = !this.active;
                this.buttonActive.toggle = this.active;
                this.buttonActive.show_note = this.active;
                this.buttonActive.note_cls = this.active && "fa fa-check";
                if (!this.active) {
                    this.$el.hide();
                }
            },
        };
        this.buttonLoad = {
            id: "show-scratchbook",
            icon: "fa-eye",
            tooltip: _l("Show/Hide Scratchbook"),
            show_note: true,
            visible: false,
            note: "",
            onclick: (e) => {
                if (this.visible) {
                    this.$el.hide();
                } else {
                    this.$el.show();
                }
            },
        };
        this.history_cache = {};
    },

    getFrames() {
        // needed for Vue.js integration
        return this;
    },

    beforeUnload() {
        let confirmText = "";
        if (this.counter > 0) {
            confirmText = `You opened ${this.counter} frame(s) which will be lost.`;
        }
        return confirmText;
    },

    /** Add and display a new frame/window based on options. */
    add: function (options) {
        if (options.target == "_blank") {
            window.open(options.url);
        } else if (options.target == "_top" || options.target == "_parent" || options.target == "_self") {
            window.location = options.url;
        } else if (!this.active || options.noscratchbook) {
            const $galaxy_main = $(window.parent.document).find("#galaxy_main");
            if (options.target == "galaxy_main" || options.target == "center") {
                if ($galaxy_main.length === 0) {
                    window.location = this._build_url(options.url, { use_panels: true });
                } else {
                    $galaxy_main.attr("src", options.url);
                }
            } else {
                window.location = options.url;
            }
        } else {
            options.url = this._build_url(options.url, { hide_panels: true, hide_masthead: true });
            options.class = "modern";
            WinBox.new(options);
        }
    },

    /** Url helper */
    _build_url: function (url, options) {
        if (url) {
            url += url.indexOf("?") == -1 ? "?" : "&";
            Object.entries(options).forEach(([key, value]) => {
                url += `${key}=${value}&`;
            });
            return url;
        }
    },
});
