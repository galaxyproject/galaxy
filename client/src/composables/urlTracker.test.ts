import { describe, expect, it } from "vitest";

import { useUrlTracker } from "./urlTracker";

describe("useUrlTracker", () => {
    it("should initialize with root value as current", () => {
        const tracker = useUrlTracker<string>({ root: "/api/data" });

        expect(tracker.current.value).toBe("/api/data");
        expect(tracker.isAtRoot.value).toBe(true);
        expect(tracker.navigationHistory.value).toEqual([]);
    });

    it("should track string URLs through navigation stack", () => {
        const tracker = useUrlTracker<string>({ root: "/api/root" });

        // Navigate forward
        tracker.forward("/api/folder1");
        expect(tracker.current.value).toBe("/api/folder1");
        expect(tracker.isAtRoot.value).toBe(false);

        // Navigate deeper
        tracker.forward("/api/folder1/subfolder");
        expect(tracker.current.value).toBe("/api/folder1/subfolder");
        expect(tracker.navigationHistory.value).toEqual(["/api/folder1", "/api/folder1/subfolder"]);

        // Navigate back
        const url1 = tracker.backward();
        expect(url1).toBe("/api/folder1");
        expect(tracker.current.value).toBe("/api/folder1");
        expect(tracker.isAtRoot.value).toBe(false);

        // Navigate back to root
        const url2 = tracker.backward();
        expect(url2).toBe("/api/root");
        expect(tracker.current.value).toBe("/api/root");
        expect(tracker.isAtRoot.value).toBe(true);
    });

    it("should track objects with metadata through navigation stack", () => {
        interface NavItem {
            id: string;
            url: string;
            parentPage?: number;
        }

        const rootItem = { id: "root", url: "/" };
        const tracker = useUrlTracker<NavItem>({ root: rootItem });

        expect(tracker.current.value).toEqual(rootItem);

        // Navigate with pagination metadata
        const item1 = { id: "folder1", url: "/folder1", parentPage: 1 };
        tracker.forward(item1);

        const item2 = { id: "folder2", url: "/folder2", parentPage: 3 };
        tracker.forward(item2);

        expect(tracker.navigationHistory.value).toHaveLength(2);
        expect(tracker.navigationHistory.value[0]).toEqual(item1);
        expect(tracker.navigationHistory.value[1]).toEqual(item2);
        expect(tracker.current.value).toEqual(item2);

        // Navigate back
        tracker.backward();
        expect(tracker.current.value).toEqual(item1);
    });

    it("should return popped value when using backwardWithContext", () => {
        interface NavItem {
            id: string;
            parentPage: number;
        }

        const rootItem = { id: "root", parentPage: 1 };
        const tracker = useUrlTracker<NavItem>({ root: rootItem });

        const item1 = { id: "folder1", parentPage: 2 };
        const item2 = { id: "folder2", parentPage: 3 };

        tracker.forward(item1);
        tracker.forward(item2);

        // Navigate back with context
        const result = tracker.backwardWithContext();

        expect(result.current).toEqual(item1);
        expect(result.popped).toEqual(item2);
        expect(result.popped?.parentPage).toBe(3);
        expect(tracker.current.value).toEqual(item1);
    });

    it("should handle backwardWithContext at root level", () => {
        const tracker = useUrlTracker<string>({ root: "/root" });

        tracker.forward("/folder1");

        const result = tracker.backwardWithContext();

        expect(result.current).toBe("/root");
        expect(result.popped).toBe("/folder1");
        expect(tracker.isAtRoot.value).toBe(true);
    });

    it("should handle backwardWithContext when already at root", () => {
        const tracker = useUrlTracker<string>({ root: "/root" });

        const result = tracker.backwardWithContext();

        expect(result.current).toBe("/root");
        expect(result.popped).toBeUndefined();
        expect(tracker.isAtRoot.value).toBe(true);
    });

    it("should be idempotent when calling backward at root", () => {
        const tracker = useUrlTracker<string>({ root: "/api/root" });

        expect(tracker.isAtRoot.value).toBe(true);

        // Call backward multiple times at root
        const url1 = tracker.backward();
        expect(url1).toBe("/api/root");
        expect(tracker.isAtRoot.value).toBe(true);

        const url2 = tracker.backward();
        expect(url2).toBe("/api/root");
        expect(tracker.isAtRoot.value).toBe(true);
        expect(tracker.navigationHistory.value).toEqual([]);
    });

    it("should reset navigation history", () => {
        const tracker = useUrlTracker<string>({ root: "/api/root" });

        tracker.forward("/api/folder1");
        tracker.forward("/api/folder2");

        expect(tracker.navigationHistory.value).toHaveLength(2);
        expect(tracker.isAtRoot.value).toBe(false);

        tracker.reset();

        expect(tracker.navigationHistory.value).toEqual([]);
        expect(tracker.isAtRoot.value).toBe(true);
        expect(tracker.current.value).toBe("/api/root");
    });

    it("should update root when resetting with new root", () => {
        const tracker = useUrlTracker<string>({ root: "/api/history1" });

        tracker.forward("/api/history1/folder");
        expect(tracker.isAtRoot.value).toBe(false);

        tracker.reset("/api/history2");

        expect(tracker.navigationHistory.value).toEqual([]);
        expect(tracker.isAtRoot.value).toBe(true);
        expect(tracker.current.value).toBe("/api/history2");
    });

    it("should work without specifying root option", () => {
        const tracker = useUrlTracker<string>();

        expect(tracker.current.value).toBeUndefined();
        expect(tracker.isAtRoot.value).toBe(true);

        tracker.forward("/folder");
        expect(tracker.current.value).toBe("/folder");
        expect(tracker.isAtRoot.value).toBe(false);

        const back = tracker.backward();
        expect(back).toBeUndefined();
        expect(tracker.current.value).toBeUndefined();
        expect(tracker.isAtRoot.value).toBe(true);
    });

    it("should handle multiple forward navigations followed by multiple backward navigations", () => {
        const tracker = useUrlTracker<string>({ root: "url_initial" });

        // Test case from original utilities.test.js
        expect(tracker.current.value).toBe("url_initial");
        expect(tracker.isAtRoot.value).toBe(true);

        tracker.forward("url_1");
        expect(tracker.current.value).toBe("url_1");
        expect(tracker.isAtRoot.value).toBe(false);

        tracker.forward("url_2");
        expect(tracker.current.value).toBe("url_2");
        expect(tracker.isAtRoot.value).toBe(false);

        tracker.backward();
        expect(tracker.current.value).toBe("url_1");
        expect(tracker.isAtRoot.value).toBe(false);

        tracker.backward();
        expect(tracker.current.value).toBe("url_initial");
        expect(tracker.isAtRoot.value).toBe(true);
    });

    it("should support push/pop as aliases for forward/backward", () => {
        const tracker = useUrlTracker<string>({ root: "/root" });

        tracker.push("/folder");
        expect(tracker.current.value).toBe("/folder");

        const result = tracker.pop();
        expect(result).toBe("/root");
    });

    it("should allow forward navigation after returning to root", () => {
        const tracker = useUrlTracker<string>({ root: "/root" });

        tracker.forward("/level1");
        tracker.backward();
        tracker.forward("/new-path");

        expect(tracker.current.value).toBe("/new-path");
        expect(tracker.navigationHistory.value).toEqual(["/new-path"]);
    });
});
