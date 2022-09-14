/** Adds window manager masthead icon and functionality **/
import _l from "utils/localization";
import WinBox from "winbox/src/js/winbox.js";
import "winbox/dist/css/winbox.min.css";
import { safePath } from "utils/redirect";

export class WindowManager {
    constructor(options) {
        options = options || {};
        this.counter = 0;
        this.active = false;
    }

    /** Return window masthead tab props */
    getTab() {
        return {
            id: "enable-window-manager",
            icon: "fa-th",
            tooltip: _l("Enable/Disable Window Manager"),
            visible: true,
            onclick: () => {
                this.active = !this.active;
            },
        };
    }

    /** Add and display a new window based on options. */
    add(options) {
        const url = safePath(options.url);
        if (options.target == "_blank") {
            window.open(url);
        } else if (options.target == "_top" || options.target == "_parent" || options.target == "_self") {
            window.location = url;
        } else if (!this.active) {
            const $galaxy_main = window.parent.document.getElementById("galaxy_main");
            if (options.target == "galaxy_main" || options.target == "center") {
                if ($galaxy_main.length === 0) {
                    window.location = this._build_url(url, { use_panels: true });
                } else {
                    $galaxy_main.attr("src", url);
                }
            } else {
                window.location = url;
            }
        } else {
            this.counter++;
            const boxUrl = this._build_url(url, { hide_panels: true, hide_masthead: true });
            WinBox.new({
                title: options.title || "Window",
                url: boxUrl,
                onclose: () => {
                    this.counter--;
                },
            });
        }
    }

    /** Called before closing all windows. */
    beforeUnload() {
        return this.counter > 0;
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
