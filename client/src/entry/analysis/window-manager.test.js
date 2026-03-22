import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

// Capture callbacks passed to WinBox so tests can invoke them
let lastWinBoxParams = null;
const mockWinBoxInstance = {
    body: document.createElement("div"),
    width: 400,
    height: 300,
    focus: vi.fn(),
};

vi.mock("winbox/src/js/winbox.js", () => ({
    default: {
        new: vi.fn((params) => {
            lastWinBoxParams = params;
            return { ...mockWinBoxInstance };
        }),
    },
}));

vi.mock("winbox/src/css/winbox.css", () => ({}));

vi.mock("@/utils/redirect", () => ({
    withPrefix: (url) => url,
}));

vi.mock("@/utils/localization", () => ({
    default: (s) => s,
}));

const STORAGE_KEY = "galaxy-scratchbook-windows";

// Dynamic import so mocks are in place before the module loads
let WindowManager;

describe("WindowManager persistence", () => {
    beforeAll(async () => {
        ({ WindowManager } = await import("./window-manager"));
    });

    beforeEach(() => {
        localStorage.clear();
        lastWinBoxParams = null;
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    function flushSave() {
        vi.advanceTimersByTime(200);
    }

    it("saves window metadata to localStorage on add", () => {
        const wm = new WindowManager();
        wm.add({ title: "Chat", url: "/chat" });
        flushSave();

        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
        expect(stored).toHaveLength(1);
        expect(stored[0].title).toBe("Chat");
        expect(stored[0].url).toBe("/chat");
    });

    it("stores original url without hide_panels params", () => {
        const wm = new WindowManager();
        wm.add({ title: "Test", url: "/some/page" });
        flushSave();

        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
        expect(stored[0].url).toBe("/some/page");
        expect(stored[0].url).not.toContain("hide_panels");
    });

    it("removes window from storage on close", () => {
        const wm = new WindowManager();
        wm.add({ title: "Win1", url: "/a" });
        flushSave();

        // Trigger the onclose callback WinBox would call
        lastWinBoxParams.onclose();
        flushSave();

        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
        expect(stored).toHaveLength(0);
    });

    it("updates position on move", () => {
        const wm = new WindowManager();
        wm.add({ title: "Win", url: "/a" });
        flushSave();

        lastWinBoxParams.onmove(150, 250);
        flushSave();

        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
        expect(stored[0].x).toBe(150);
        expect(stored[0].y).toBe(250);
    });

    it("updates size on resize", () => {
        const wm = new WindowManager();
        wm.add({ title: "Win", url: "/a" });
        flushSave();

        lastWinBoxParams.onresize(600, 500);
        flushSave();

        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
        expect(stored[0].width).toBe(600);
        expect(stored[0].height).toBe(500);
    });

    it("restores windows from localStorage", () => {
        const saved = [
            { id: "abc", title: "Chat", url: "/chat", x: 100, y: 50, width: 500, height: 400 },
            { id: "def", title: "Help", url: "/help", x: 200, y: 80, width: 300, height: 250 },
        ];
        localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));

        const wm = new WindowManager();
        wm.restore();

        expect(wm.active).toBe(true);
        expect(wm.counter).toBe(2);
        expect(wm.windows.size).toBe(2);
    });

    it("passes saved position/size through to add on restore", () => {
        const saved = [{ id: "abc", title: "Chat", url: "/chat", x: 100, y: 50, width: 500, height: 400 }];
        localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));

        const wm = new WindowManager();
        wm.restore();

        expect(lastWinBoxParams.x).toBe(100);
        expect(lastWinBoxParams.y).toBe(50);
        expect(lastWinBoxParams.width).toBe(500);
        expect(lastWinBoxParams.height).toBe(400);
    });

    it("does not set active when nothing to restore", () => {
        const wm = new WindowManager();
        wm.restore();

        expect(wm.active).toBe(false);
        expect(wm.counter).toBe(0);
    });

    it("handles corrupt localStorage gracefully", () => {
        localStorage.setItem(STORAGE_KEY, "not-valid-json{{{");

        const wm = new WindowManager();
        wm.restore();

        expect(wm.active).toBe(false);
        expect(wm.counter).toBe(0);
    });

    it("tracks multiple windows independently", () => {
        const wm = new WindowManager();
        wm.add({ title: "Win1", url: "/a" });
        const firstClose = lastWinBoxParams.onclose;

        wm.add({ title: "Win2", url: "/b" });
        flushSave();

        let stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
        expect(stored).toHaveLength(2);

        // Close first window
        firstClose();
        flushSave();

        stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
        expect(stored).toHaveLength(1);
        expect(stored[0].title).toBe("Win2");
    });

    it("debounces rapid saves", () => {
        const wm = new WindowManager();
        wm.add({ title: "Win", url: "/a" });

        // Multiple moves without flushing
        lastWinBoxParams.onmove(10, 10);
        lastWinBoxParams.onmove(20, 20);
        lastWinBoxParams.onmove(30, 30);

        // Nothing written yet
        expect(localStorage.getItem(STORAGE_KEY)).toBeNull();

        flushSave();

        // Only final state persisted
        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
        expect(stored[0].x).toBe(30);
        expect(stored[0].y).toBe(30);
    });
});
