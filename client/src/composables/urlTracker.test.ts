import { describe, expect, it } from "vitest";

import { useUrlTracker } from "./urlTracker";

describe("useUrlTracker", () => {
    it("starts at the configured root with an empty history", () => {
        const tracker = useUrlTracker({ root: "/api/data" });

        expect(tracker.current.value).toBe("/api/data");
        expect(tracker.isAtRoot.value).toBe(true);
        expect(tracker.navigationHistory.value).toEqual([]);
    });

    it("returns to the parent URL and then the root when navigating backward", () => {
        const tracker = useUrlTracker({ root: "/api/root" });

        tracker.forward("/api/folder1");
        expect(tracker.current.value).toBe("/api/folder1");
        expect(tracker.isAtRoot.value).toBe(false);

        tracker.forward("/api/folder1/subfolder");
        expect(tracker.current.value).toBe("/api/folder1/subfolder");
        expect(tracker.navigationHistory.value).toEqual(["/api/folder1", "/api/folder1/subfolder"]);

        const parentUrl = tracker.backward();
        expect(parentUrl).toBe("/api/folder1");
        expect(tracker.current.value).toBe("/api/folder1");
        expect(tracker.isAtRoot.value).toBe(false);

        const rootUrl = tracker.backward();
        expect(rootUrl).toBe("/api/root");
        expect(tracker.current.value).toBe("/api/root");
        expect(tracker.isAtRoot.value).toBe(true);
    });

    it("keeps metadata on navigation items when returning to the previous folder", () => {
        interface NavItem {
            id: string;
            url: string;
            parentPage?: number;
        }

        const rootFolder = { id: "root", url: "/" };
        const tracker = useUrlTracker<NavItem>({ root: rootFolder });

        expect(tracker.current.value).toEqual(rootFolder);

        const firstFolder = { id: "folder1", url: "/folder1", parentPage: 1 };
        tracker.forward(firstFolder);

        const secondFolder = { id: "folder2", url: "/folder2", parentPage: 3 };
        tracker.forward(secondFolder);

        expect(tracker.navigationHistory.value).toHaveLength(2);
        expect(tracker.navigationHistory.value[0]).toEqual(firstFolder);
        expect(tracker.navigationHistory.value[1]).toEqual(secondFolder);
        expect(tracker.current.value).toEqual(secondFolder);

        tracker.backward();
        expect(tracker.current.value).toEqual(firstFolder);
    });

    it("returns the previous folder and the popped folder metadata with backwardWithContext", () => {
        interface NavItem {
            id: string;
            parentPage: number;
        }

        const rootFolder = { id: "root", parentPage: 1 };
        const tracker = useUrlTracker<NavItem>({ root: rootFolder });

        const firstFolder = { id: "folder1", parentPage: 2 };
        const secondFolder = { id: "folder2", parentPage: 3 };

        tracker.forward(firstFolder);
        tracker.forward(secondFolder);

        const result = tracker.backwardWithContext();

        expect(result.current).toEqual(firstFolder);
        expect(result.popped).toEqual(secondFolder);
        expect(result.popped?.parentPage).toBe(3);
        expect(tracker.current.value).toEqual(firstFolder);
    });

    it("returns the root and the popped URL when leaving the last folder with backwardWithContext", () => {
        const tracker = useUrlTracker({ root: "/root" });

        tracker.forward("/folder1");

        const result = tracker.backwardWithContext();

        expect(result.current).toBe("/root");
        expect(result.popped).toBe("/folder1");
        expect(tracker.isAtRoot.value).toBe(true);
    });

    it("returns the root without a popped item when backwardWithContext starts at root", () => {
        const tracker = useUrlTracker({ root: "/root" });

        const result = tracker.backwardWithContext();

        expect(result.current).toBe("/root");
        expect(result.popped).toBeUndefined();
        expect(tracker.isAtRoot.value).toBe(true);
    });

    it("stays at root when backward is called repeatedly with an empty history", () => {
        const tracker = useUrlTracker({ root: "/api/root" });

        expect(tracker.isAtRoot.value).toBe(true);

        const firstResult = tracker.backward();
        expect(firstResult).toBe("/api/root");
        expect(tracker.isAtRoot.value).toBe(true);

        const repeatedResult = tracker.backward();
        expect(repeatedResult).toBe("/api/root");
        expect(tracker.isAtRoot.value).toBe(true);
        expect(tracker.navigationHistory.value).toEqual([]);
    });

    it("clears navigation history and returns to the existing root on reset", () => {
        const tracker = useUrlTracker({ root: "/api/root" });

        tracker.forward("/api/folder1");
        tracker.forward("/api/folder2");

        expect(tracker.navigationHistory.value).toHaveLength(2);
        expect(tracker.isAtRoot.value).toBe(false);

        tracker.reset();

        expect(tracker.navigationHistory.value).toEqual([]);
        expect(tracker.isAtRoot.value).toBe(true);
        expect(tracker.current.value).toBe("/api/root");
    });

    it("clears navigation history and replaces the root on reset with a new root", () => {
        const tracker = useUrlTracker({ root: "/api/history1" });

        tracker.forward("/api/history1/folder");
        expect(tracker.isAtRoot.value).toBe(false);

        tracker.reset("/api/history2");

        expect(tracker.navigationHistory.value).toEqual([]);
        expect(tracker.isAtRoot.value).toBe(true);
        expect(tracker.current.value).toBe("/api/history2");
    });

    it("returns undefined after navigating back when no root is configured", () => {
        const tracker = useUrlTracker<string>();

        expect(tracker.current.value).toBeUndefined();
        expect(tracker.isAtRoot.value).toBe(true);

        tracker.forward("/folder");
        expect(tracker.current.value).toBe("/folder");
        expect(tracker.isAtRoot.value).toBe(false);

        const rootUrl = tracker.backward();
        expect(rootUrl).toBeUndefined();
        expect(tracker.current.value).toBeUndefined();
        expect(tracker.isAtRoot.value).toBe(true);
    });

    it("updates the current URL and root state at every step of a two-level round trip", () => {
        const tracker = useUrlTracker({ root: "url_initial" });

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

    it("navigates forward and backward with the push and pop aliases", () => {
        const tracker = useUrlTracker({ root: "/root" });

        tracker.push("/folder");
        expect(tracker.current.value).toBe("/folder");

        const result = tracker.pop();
        expect(result).toBe("/root");
    });

    it("starts a fresh history when navigating forward after returning to root", () => {
        const tracker = useUrlTracker({ root: "/root" });

        tracker.forward("/level1");
        tracker.backward();
        tracker.forward("/new-path");

        expect(tracker.current.value).toBe("/new-path");
        expect(tracker.navigationHistory.value).toEqual(["/new-path"]);
    });
});
