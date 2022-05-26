/** Adds window manager masthead icon and functionality **/
import _l from "utils/localization";
import WinBox from "winbox/src/js/winbox.js";
import "winbox/dist/css/winbox.min.css";

export class WindowManager {
    constructor(options) {
        options = options || {};
        this.counter = 0;
        this.active = false;
        this.buttonActive = {
            id: "enable-window-manager",
            icon: "fa-th",
            tooltip: _l("Enable/Disable Window Manager"),
            toggle: false,
            onclick: () => {
                this.active = !this.active;
                this.buttonActive.toggle = this.active;
                this.buttonActive.show_note = this.active;
                this.buttonActive.note_cls = this.active && "fa fa-check";
            },
        };
    }

    /** Add and display a new window based on options. */
    add(options) {
        if (options.target == "_blank") {
            window.open(options.url);
        } else if (options.target == "_top" || options.target == "_parent" || options.target == "_self") {
            window.location = options.url;
        } else if (!this.active) {
            const $galaxy_main = window.parent.document.getElementById("galaxy_main");
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
            this.counter++;
            const url = this._build_url(options.url, { hide_panels: true, hide_masthead: true });
            WinBox.new({
                title: options.title || "Window",
                url: url,
                onclose: () => {
                    this.counter--;
                },
            });
        }
    }

    /** Called before closing all windows. */
    beforeUnload() {
        let confirmText = "";
        if (this.counter > 0) {
            confirmText = `You opened ${this.counter} window(s) which will be lost.`;
        }
        return confirmText;
    }

    /** Url helper */
    _build_url(url, options) {
        if (url) {
            url += url.indexOf("?") == -1 ? "?" : "&";
            Object.entries(options).forEach(([key, value]) => {
                url += `${key}=${value}&`;
            });
            return url;
        }
    }
}
