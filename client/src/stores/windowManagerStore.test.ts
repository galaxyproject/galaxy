import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useWindowManagerStore } from "./windowManagerStore";

describe("windowManagerStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        localStorage.clear();
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("toggles active state", () => {
        const store = useWindowManagerStore();
        expect(store.active).toBe(false);
        store.toggle();
        expect(store.active).toBe(true);
        store.toggle();
        expect(store.active).toBe(false);
    });

    it("adds a window and focuses it", () => {
        const store = useWindowManagerStore();
        store.add({ title: "One", url: "/foo" });
        expect(store.windows).toHaveLength(1);
        const win = store.windows[0]!;
        expect(win.title).toBe("One");
        expect(win.url).toBe("/foo");
        expect(win.width).toBe(600);
        expect(win.height).toBe(400);
        expect(win.minimized).toBe(false);
        expect(win.maximized).toBe(false);
        expect(store.focusedId).toBe(win.id);
    });

    it("removes a window and refocuses the last remaining one", () => {
        const store = useWindowManagerStore();
        store.add({ title: "A", url: "/a" });
        store.add({ title: "B", url: "/b" });
        const a = store.windows[0]!;
        const b = store.windows[1]!;
        store.remove(b.id);
        expect(store.windows).toHaveLength(1);
        expect(store.focusedId).toBe(a.id);
        store.remove(a.id);
        expect(store.windows).toHaveLength(0);
        expect(store.focusedId).toBeNull();
    });

    it("raises zIndex when focusing a different window", () => {
        const store = useWindowManagerStore();
        store.add({ url: "/a" });
        store.add({ url: "/b" });
        const a = store.windows[0]!;
        const b = store.windows[1]!;
        expect(b.zIndex).toBeGreaterThan(a.zIndex);
        store.focus(a.id);
        expect(store.focusedId).toBe(a.id);
        expect(a.zIndex).toBeGreaterThan(b.zIndex);
    });

    it("updates position and size", () => {
        const store = useWindowManagerStore();
        store.add({ url: "/a" });
        const win = store.windows[0]!;
        store.updatePosition(win.id, 123, 456);
        expect(win.x).toBe(123);
        expect(win.y).toBe(456);
        store.updateSize(win.id, 800, 500);
        expect(win.width).toBe(800);
        expect(win.height).toBe(500);
    });

    it("toggles minimize and moves focus to another open window", () => {
        const store = useWindowManagerStore();
        store.add({ url: "/a" });
        store.add({ url: "/b" });
        const a = store.windows[0]!;
        const b = store.windows[1]!;
        store.focus(b.id);
        store.toggleMinimize(b.id);
        expect(b.minimized).toBe(true);
        expect(store.focusedId).toBe(a.id);
        store.toggleMinimize(b.id);
        expect(b.minimized).toBe(false);
        expect(store.focusedId).toBe(b.id);
    });

    it("un-minimizes when toggling maximize on a minimized window", () => {
        const store = useWindowManagerStore();
        store.add({ url: "/a" });
        const win = store.windows[0]!;
        store.toggleMinimize(win.id);
        expect(win.minimized).toBe(true);
        store.toggleMaximize(win.id);
        expect(win.maximized).toBe(true);
        expect(win.minimized).toBe(false);
    });

    it("beforeUnload reflects whether any windows are open", () => {
        const store = useWindowManagerStore();
        expect(store.beforeUnload()).toBe(false);
        store.add({ url: "/a" });
        expect(store.beforeUnload()).toBe(true);
    });

    it("persists to localStorage and restores on demand", () => {
        const store = useWindowManagerStore();
        store.add({ title: "Saved", url: "/saved", x: 50, y: 60, width: 700, height: 450 });
        vi.runAllTimers();
        const raw = localStorage.getItem("galaxy-window-manager-windows");
        expect(raw).not.toBeNull();

        // Fresh store should start empty, then restore from the same localStorage.
        setActivePinia(createPinia());
        const fresh = useWindowManagerStore();
        expect(fresh.windows).toHaveLength(0);
        fresh.restore();
        expect(fresh.active).toBe(true);
        expect(fresh.windows).toHaveLength(1);
        expect(fresh.windows[0]).toMatchObject({
            title: "Saved",
            url: "/saved",
            x: 50,
            y: 60,
            width: 700,
            height: 450,
        });
    });

    it("buildUrl appends hide_panels and hide_masthead query params", () => {
        const store = useWindowManagerStore();
        const url = store.buildUrl("/tool/runner?tool_id=foo");
        expect(url).toContain("tool_id=foo");
        expect(url).toContain("hide_panels=true");
        expect(url).toContain("hide_masthead=true");
    });

    it("getTab exposes a masthead entry that toggles the window manager", () => {
        const store = useWindowManagerStore();
        const tab = store.getTab();
        expect(tab.id).toBe("enable-window-manager");
        expect(tab.visible).toBe(true);
        tab.onclick();
        expect(store.active).toBe(true);
    });
});
