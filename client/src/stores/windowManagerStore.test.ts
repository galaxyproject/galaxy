import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setupTestPinia } from "./testUtils";
import { useWindowManagerStore } from "./windowManagerStore";

describe("windowManagerStore", () => {
    beforeEach(() => {
        setupTestPinia();
        localStorage.clear();
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
        localStorage.clear();
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
        expect(win).toMatchObject({
            title: "One",
            url: "/foo",
            width: 600,
            height: 400,
            minimized: false,
            maximized: false,
        });
        expect(store.focusedId).toBe(win.id);
    });

    it("removes a window and refocuses the last remaining one", () => {
        const store = useWindowManagerStore();
        store.add({ title: "A", url: "/a" });
        store.add({ title: "B", url: "/b" });
        const firstWindow = store.windows[0]!;
        const secondWindow = store.windows[1]!;
        store.remove(secondWindow.id);
        expect(store.windows).toHaveLength(1);
        expect(store.focusedId).toBe(firstWindow.id);
        store.remove(firstWindow.id);
        expect(store.windows).toHaveLength(0);
        expect(store.focusedId).toBeNull();
    });

    it("raises zIndex when focusing a different window", () => {
        const store = useWindowManagerStore();
        store.add({ url: "/a" });
        store.add({ url: "/b" });
        const firstWindow = store.windows[0]!;
        const secondWindow = store.windows[1]!;
        expect(secondWindow.zIndex).toBeGreaterThan(firstWindow.zIndex);
        store.focus(firstWindow.id);
        expect(store.focusedId).toBe(firstWindow.id);
        expect(firstWindow.zIndex).toBeGreaterThan(secondWindow.zIndex);
    });

    it("updates position and size", () => {
        const store = useWindowManagerStore();
        store.add({ url: "/a" });
        const win = store.windows[0]!;
        store.updatePosition(win.id, 123, 456);
        expect(win).toMatchObject({ x: 123, y: 456 });
        store.updateSize(win.id, 800, 500);
        expect(win).toMatchObject({ width: 800, height: 500 });
    });

    it("toggles minimize and moves focus to another open window", () => {
        const store = useWindowManagerStore();
        store.add({ url: "/a" });
        store.add({ url: "/b" });
        const firstWindow = store.windows[0]!;
        const secondWindow = store.windows[1]!;
        store.focus(secondWindow.id);
        store.toggleMinimize(secondWindow.id);
        expect(secondWindow.minimized).toBe(true);
        expect(store.focusedId).toBe(firstWindow.id);
        store.toggleMinimize(secondWindow.id);
        expect(secondWindow.minimized).toBe(false);
        expect(store.focusedId).toBe(secondWindow.id);
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
        const savedWindow = { title: "Saved", url: "/saved", x: 50, y: 60, width: 700, height: 450 };
        store.add(savedWindow);
        vi.runAllTimers();
        const raw = localStorage.getItem("galaxy-window-manager-windows");
        expect(raw).not.toBeNull();

        // Fresh store should start empty, then restore from the same localStorage.
        setupTestPinia();
        const fresh = useWindowManagerStore();
        expect(fresh.windows).toHaveLength(0);
        fresh.restore();
        expect(fresh.active).toBe(true);
        expect(fresh.windows).toHaveLength(1);
        expect(fresh.windows[0]).toMatchObject(savedWindow);
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
