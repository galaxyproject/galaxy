/** Adds window manager masthead icon and functionality **/
import _l from "utils/localization";
import WinBox from "winbox/src/js/winbox.js";
import "winbox/dist/css/winbox.min.css";
import { withPrefix } from "utils/redirect";

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
        const url = withPrefix(options.url);
        this.counter++;
        const boxUrl = this._build_url(url, { hide_panels: true, hide_masthead: true });
        WinBox.new({
            title: options.title || "Window",
            url: boxUrl,
            index: 850,
            onclose: () => {
                this.counter--;
            },
        });
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
