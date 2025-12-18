import { describe, expect, it } from "vitest";

import { useUrlTracker } from "./urlTracker";

describe("useUrlTracker", () => {
    it("should initialize with root URL", () => {
        const tracker = useUrlTracker<string>({ root: "/api/data" });

        expect(tracker.getUrl()).toBe("/api/data");
        expect(tracker.atRoot.value).toBe(true);
        expect(tracker.navigationHistory.value).toEqual([]);
    });

    it("should track string URLs through navigation stack", () => {
        const tracker = useUrlTracker<string>({ root: "/api/root" });

        // Navigate forward
        const url1 = tracker.getUrl("/api/folder1");
        expect(url1).toBe("/api/folder1");
        expect(tracker.atRoot.value).toBe(false);

        // Navigate deeper
        const url2 = tracker.getUrl("/api/folder1/subfolder");
        expect(url2).toBe("/api/folder1/subfolder");
        expect(tracker.navigationHistory.value).toEqual(["/api/folder1", "/api/folder1/subfolder"]);

        // Navigate back
        const url3 = tracker.getUrl();
        expect(url3).toBe("/api/folder1");
        expect(tracker.atRoot.value).toBe(false);

        // Navigate back to root
        const url4 = tracker.getUrl();
        expect(url4).toBe("/api/root");
        expect(tracker.atRoot.value).toBe(true);
    });

    it("should track objects with metadata through navigation stack", () => {
        interface NavItem {
            id: string;
            url: string;
            parentPage?: number;
        }

        const tracker = useUrlTracker<NavItem>({ root: { id: "root", url: "/" } });

        // Navigate with pagination metadata
        const item1 = { id: "folder1", url: "/folder1", parentPage: 1 };
        tracker.getUrl(item1);

        const item2 = { id: "folder2", url: "/folder2", parentPage: 3 };
        tracker.getUrl(item2);

        expect(tracker.navigationHistory.value).toHaveLength(2);
        expect(tracker.navigationHistory.value[0]).toEqual(item1);
        expect(tracker.navigationHistory.value[1]).toEqual(item2);

        // Navigate back
        const current = tracker.getUrl();
        expect(current).toEqual(item1);
    });

    it("should return popped value when navigating back with returnWithPrevious", () => {
        interface NavItem {
            id: string;
            parentPage: number;
        }

        const tracker = useUrlTracker<NavItem>({
            root: { id: "root", parentPage: 1 },
        });

        const item1 = { id: "folder1", parentPage: 2 };
        const item2 = { id: "folder2", parentPage: 3 };

        tracker.getUrl(item1);
        tracker.getUrl(item2);

        // Navigate back with popped value
        const result = tracker.getUrl(undefined, true);

        expect(result.url).toEqual(item1);
        expect(result.popped).toEqual(item2);
        expect(result.popped?.parentPage).toBe(3);
    });

    it("should handle returnWithPrevious at root level", () => {
        const tracker = useUrlTracker<string>({ root: "/root" });

        tracker.getUrl("/folder1");

        const result = tracker.getUrl(undefined, true);

        expect(result.url).toBe("/root");
        expect(result.popped).toBe("/folder1");
        expect(tracker.atRoot.value).toBe(true);
    });

    it("should handle returnWithPrevious when already at root", () => {
        const tracker = useUrlTracker<string>({ root: "/root" });

        const result = tracker.getUrl(undefined, true);

        expect(result.url).toBe("/root");
        expect(result.popped).toBeUndefined();
        expect(tracker.atRoot.value).toBe(true);
    });

    it("should reset navigation history", () => {
        const tracker = useUrlTracker<string>({ root: "/api/root" });

        tracker.getUrl("/api/folder1");
        tracker.getUrl("/api/folder2");

        expect(tracker.navigationHistory.value).toHaveLength(2);
        expect(tracker.atRoot.value).toBe(false);

        tracker.reset();

        expect(tracker.navigationHistory.value).toEqual([]);
        expect(tracker.atRoot.value).toBe(true);
        expect(tracker.getUrl()).toBe("/api/root");
    });

    it("should update root when resetting with new root", () => {
        const tracker = useUrlTracker<string>({ root: "/api/history1" });

        tracker.getUrl("/api/history1/folder");
        expect(tracker.atRoot.value).toBe(false);

        tracker.reset("/api/history2");

        expect(tracker.navigationHistory.value).toEqual([]);
        expect(tracker.atRoot.value).toBe(true);
        expect(tracker.getUrl()).toBe("/api/history2");
    });

    it("should expose readonly navigationHistory", () => {
        const tracker = useUrlTracker<string>({ root: "/root" });

        tracker.getUrl("/folder1");
        tracker.getUrl("/folder2");

        const history = tracker.navigationHistory.value;
        expect(history).toEqual(["/folder1", "/folder2"]);

        // Verify it's readonly (TypeScript would catch this at compile time)
        expect(tracker.navigationHistory.value).toHaveLength(2);
    });

    it("should reactively update atRoot computed property", () => {
        const tracker = useUrlTracker<string>({ root: "/root" });

        expect(tracker.atRoot.value).toBe(true);

        tracker.getUrl("/folder");
        expect(tracker.atRoot.value).toBe(false);

        tracker.getUrl();
        expect(tracker.atRoot.value).toBe(true);
    });

    it("should work without specifying root option", () => {
        const tracker = useUrlTracker<string>();

        expect(tracker.getUrl()).toBeUndefined();
        expect(tracker.atRoot.value).toBe(true);

        tracker.getUrl("/folder");
        expect(tracker.atRoot.value).toBe(false);

        const back = tracker.getUrl();
        expect(back).toBeUndefined();
        expect(tracker.atRoot.value).toBe(true);
    });

    it("should handle multiple forward navigations followed by multiple back navigations", () => {
        const tracker = useUrlTracker<string>({ root: "url_initial" });

        // Test case from original utilities.test.js
        let url = tracker.getUrl();
        expect(url).toBe("url_initial");
        expect(tracker.atRoot.value).toBe(true);

        url = tracker.getUrl("url_1");
        expect(url).toBe("url_1");
        expect(tracker.atRoot.value).toBe(false);

        url = tracker.getUrl("url_2");
        expect(url).toBe("url_2");
        expect(tracker.atRoot.value).toBe(false);

        url = tracker.getUrl();
        expect(url).toBe("url_1");
        expect(tracker.atRoot.value).toBe(false);

        url = tracker.getUrl();
        expect(url).toBe("url_initial");
        expect(tracker.atRoot.value).toBe(true);
    });
});
