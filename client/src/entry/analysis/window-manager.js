/** Adds window manager masthead icon and functionality **/
import "winbox/src/css/winbox.css";

import { faTh } from "@fortawesome/free-solid-svg-icons";
import WinBox from "winbox/src/js/winbox.js";

import _l from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";

export class WindowManager {
    constructor(options) {
        options = options || {};
        this.counter = 0;
        this.active = false;
        this.zIndexInitialized = false;
    }

    /** Return window masthead tab props */
    getTab() {
        return {
            id: "enable-window-manager",
            icon: faTh,
            tooltip: _l("Enable/Disable Window Manager"),
            visible: true,
            onclick: () => {
                this.active = !this.active;
            },
        };
    }

    /** Add and display a new window based on options. */
    add(options, layout = 10, margin = 20) {
        const url = this._build_url(withPrefix(options.url), { hide_panels: true, hide_masthead: true });
        const x = this.counter * margin;
        const y = (this.counter % layout) * margin;
        this.counter++;
        const params = {
            title: options.title || "Window",
            url: url,
            x: x,
            y: y,
            onclose: () => {
                this.counter--;
            },
        };
        // Set z-index floor on the first window only to position above
        // Galaxy UI (masthead is z-index 900). Subsequent windows omit
        // index so WinBox auto-increments correctly.
        if (!this.zIndexInitialized) {
            params.index = 850;
            this.zIndexInitialized = true;
        }
        const win = WinBox.new(params);
        // Overlay to capture clicks on unfocused windows, since mousedown
        // doesn't propagate out of iframes. WinBox toggles the "focus"
        // class, and CSS sets pointer-events:none on the overlay for the
        // focused window so the iframe works normally.
        const overlay = document.createElement("div");
        overlay.className = "iframe-focus-overlay";
        overlay.addEventListener("mousedown", () => win.focus());
        win.body.appendChild(overlay);
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
