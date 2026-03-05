/** Adds window manager masthead icon and functionality **/
import "winbox/src/css/winbox.css";

import { faTh } from "@fortawesome/free-solid-svg-icons";
import WinBox from "winbox/src/js/winbox.js";

import _l from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";

const STORAGE_KEY = "galaxy-scratchbook-windows";

export class WindowManager {
    constructor(options) {
        options = options || {};
        this.counter = 0;
        this.active = false;
        this.zIndexInitialized = false;
        this.windows = new Map();
        this._saveTimeout = null;
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
        const id = crypto.randomUUID();
        const originalUrl = options.url;
        const url = this._build_url(withPrefix(originalUrl), { hide_panels: true, hide_masthead: true });
        const x = options.x ?? this.counter * margin;
        const y = options.y ?? (this.counter % layout) * margin;
        this.counter++;
        const params = {
            title: options.title || "Window",
            url: url,
            x: x,
            y: y,
            width: options.width,
            height: options.height,
            onclose: () => {
                this.counter--;
                this.windows.delete(id);
                this._saveWindows();
            },
            onmove: (newX, newY) => {
                const entry = this.windows.get(id);
                if (entry) {
                    entry.x = newX;
                    entry.y = newY;
                    this._saveWindows();
                }
            },
            onresize: (newW, newH) => {
                const entry = this.windows.get(id);
                if (entry) {
                    entry.width = newW;
                    entry.height = newH;
                    this._saveWindows();
                }
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

        this.windows.set(id, {
            id,
            title: params.title,
            url: originalUrl,
            x: x,
            y: y,
            width: win.width,
            height: win.height,
        });
        this._saveWindows();
    }

    /** Restore windows saved from a previous session. */
    restore() {
        const saved = this._loadWindows();
        if (saved.length > 0) {
            this.active = true;
            for (const entry of saved) {
                this.add({
                    title: entry.title,
                    url: entry.url,
                    x: entry.x,
                    y: entry.y,
                    width: entry.width,
                    height: entry.height,
                });
            }
        }
    }

    /** Called before closing all windows. */
    beforeUnload() {
        return this.counter > 0;
    }

    _saveWindows() {
        clearTimeout(this._saveTimeout);
        this._saveTimeout = setTimeout(() => {
            try {
                const data = JSON.stringify([...this.windows.values()]);
                localStorage.setItem(STORAGE_KEY, data);
            } catch (e) {
                // localStorage full or unavailable — silently ignore
            }
        }, 200);
    }

    _loadWindows() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
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
