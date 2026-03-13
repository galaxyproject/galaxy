import { faTh } from "@fortawesome/free-solid-svg-icons";
import { defineStore } from "pinia";
import { ref } from "vue";

import _l from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";

const STORAGE_KEY = "galaxy-scratchbook-windows";

export interface WindowState {
    id: string;
    title: string;
    url: string;
    x: number;
    y: number;
    width: number;
    height: number;
    zIndex: number;
    minimized: boolean;
    maximized: boolean;
}

export const useWindowManagerStore = defineStore("windowManager", () => {
    const active = ref(false);
    const windows = ref<WindowState[]>([]);
    const focusedId = ref<string | null>(null);
    let nextZIndex = 850;
    let saveTimeout: ReturnType<typeof setTimeout> | null = null;

    function toggle() {
        active.value = !active.value;
    }

    function getTab() {
        return {
            id: "enable-window-manager",
            icon: faTh,
            tooltip: _l("Enable/Disable Window Manager"),
            visible: true,
            onclick: () => toggle(),
        };
    }

    function buildUrl(url: string): string {
        let fullUrl = withPrefix(url);
        fullUrl += fullUrl.includes("?") ? "&" : "?";
        fullUrl += "hide_panels=true&hide_masthead=true";
        return fullUrl;
    }

    function add(options: { title?: string; url: string; x?: number; y?: number; width?: number; height?: number }) {
        const id = crypto.randomUUID();
        const count = windows.value.length;
        const margin = 20;
        const layout = 10;
        const x = options.x ?? count * margin;
        const y = options.y ?? (count % layout) * margin;

        windows.value.push({
            id,
            title: options.title || "Window",
            url: options.url,
            x,
            y,
            width: options.width ?? 600,
            height: options.height ?? 400,
            zIndex: nextZIndex++,
            minimized: false,
            maximized: false,
        });
        focusedId.value = id;
        _saveWindows();
    }

    function remove(id: string) {
        windows.value = windows.value.filter((w) => w.id !== id);
        if (focusedId.value === id) {
            const last = windows.value[windows.value.length - 1];
            focusedId.value = last?.id ?? null;
        }
        _saveWindows();
    }

    function focus(id: string) {
        focusedId.value = id;
        const win = windows.value.find((w) => w.id === id);
        if (win) {
            win.zIndex = nextZIndex++;
        }
    }

    function updatePosition(id: string, x: number, y: number) {
        const win = windows.value.find((w) => w.id === id);
        if (win) {
            win.x = x;
            win.y = y;
            _saveWindows();
        }
    }

    function updateSize(id: string, width: number, height: number) {
        const win = windows.value.find((w) => w.id === id);
        if (win) {
            win.width = width;
            win.height = height;
            _saveWindows();
        }
    }

    function toggleMinimize(id: string) {
        const win = windows.value.find((w) => w.id === id);
        if (win) {
            win.minimized = !win.minimized;
            if (win.minimized && focusedId.value === id) {
                const next = windows.value.find((w) => w.id !== id && !w.minimized);
                focusedId.value = next?.id ?? null;
            }
            if (!win.minimized) {
                focus(id);
            }
        }
    }

    function toggleMaximize(id: string) {
        const win = windows.value.find((w) => w.id === id);
        if (win) {
            win.maximized = !win.maximized;
            if (win.maximized) {
                win.minimized = false;
            }
        }
    }

    function beforeUnload(): boolean {
        return windows.value.length > 0;
    }

    function _saveWindows() {
        if (saveTimeout) {
            clearTimeout(saveTimeout);
        }
        saveTimeout = setTimeout(() => {
            try {
                const data = windows.value.map((w) => ({
                    id: w.id,
                    title: w.title,
                    url: w.url,
                    x: w.x,
                    y: w.y,
                    width: w.width,
                    height: w.height,
                }));
                localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
            } catch {
                // localStorage full or unavailable
            }
        }, 200);
    }

    function restore() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return;
            }
            const saved = JSON.parse(raw);
            if (!Array.isArray(saved) || saved.length === 0) {
                return;
            }
            active.value = true;
            for (const entry of saved) {
                add({
                    title: entry.title,
                    url: entry.url,
                    x: entry.x,
                    y: entry.y,
                    width: entry.width,
                    height: entry.height,
                });
            }
        } catch {
            // corrupt localStorage
        }
    }

    return {
        active,
        windows,
        focusedId,
        toggle,
        getTab,
        buildUrl,
        add,
        remove,
        focus,
        updatePosition,
        updateSize,
        toggleMinimize,
        toggleMaximize,
        beforeUnload,
        restore,
    };
});
