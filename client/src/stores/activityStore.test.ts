import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useActivityStore } from "@/stores/activityStore";

// mock Galaxy object
vi.mock("./activitySetup", () => ({
    defaultActivities: [
        {
            anonymous: false,
            description: "a-description",
            icon: "a-icon" as unknown as IconDefinition,
            id: "a-id",
            mutable: false,
            optional: false,
            panel: true,
            title: "a-title",
            to: null,
            tooltip: "a-tooltip",
            visible: true,
        },
    ],
}));

const newActivities = [
    {
        anonymous: false,
        description: "a-description-new",
        icon: "a-icon-new" as unknown as IconDefinition,
        id: "a-id",
        mutable: false,
        optional: false,
        panel: true,
        title: "a-title",
        to: "a-to-new",
        tooltip: "a-tooltip-new",
        visible: false,
    },
    {
        anonymous: false,
        description: "b-description-new",
        icon: "b-icon-new" as unknown as IconDefinition,
        id: "b-id",
        mutable: true,
        optional: false,
        panel: true,
        title: "b-title-new",
        to: "b-to-new",
        tooltip: "b-tooltip-new",
        visible: true,
    },
];

describe("Activity Store", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        // ensure clean localStorage between tests (useUserLocalStorage persistence)
        localStorage.clear();
    });

    it("initializes with default activities after sync", async () => {
        const activityStore = useActivityStore("default");
        expect(activityStore.getAll().length).toBe(0);
        await activityStore.sync();
        expect(activityStore.getAll().length).toBe(1);
    });

    it("merges built-in and custom activities on sync", async () => {
        const activityStore = useActivityStore("default");
        await activityStore.sync();
        const initialActivities = activityStore.getAll();
        expect(initialActivities[0]?.visible).toBeTruthy();
        activityStore.setAll(newActivities);
        expect(activityStore.activities.length).toBe(2);
        const currentActivities = activityStore.getAll();
        expect(currentActivities[0]).toEqual(newActivities[0]);
        expect(currentActivities[1]).toEqual(newActivities[1]);
        await activityStore.sync();
        const syncActivities = activityStore.getAll();
        expect(syncActivities.length).toEqual(2);
        expect(syncActivities[0]?.description).toEqual("a-description");
        expect(syncActivities[0]?.visible).toBeFalsy();
        expect(syncActivities[1]).toEqual(newActivities[1]);
    });

    it("removes activities and restores built-ins on sync", async () => {
        const activityStore = useActivityStore("default");
        await activityStore.sync();
        const initialActivities = activityStore.getAll();
        expect(initialActivities.length).toEqual(1);
        activityStore.remove("a-id");
        expect(activityStore.getAll().length).toEqual(0);
        await activityStore.sync();
        expect(activityStore.getAll().length).toEqual(1);
        activityStore.setAll(newActivities);
        expect(activityStore.getAll().length).toEqual(2);
        activityStore.remove("b-id");
        await activityStore.sync();
        expect(activityStore.getAll().length).toEqual(1);
    });

    describe("setPosition", () => {
        it("reorders an activity to the specified position", async () => {
            const activityStore = useActivityStore("default");
            await activityStore.sync();
            activityStore.setAll(newActivities);

            const initialActivities = activityStore.getAll();
            expect(initialActivities[0]?.id).toBe("a-id");
            expect(initialActivities[1]?.id).toBe("b-id");

            // initial order: [a-id, b-id]
            activityStore.setPosition("b-id", 0);

            const reorderedActivities = activityStore.getAll();
            expect(reorderedActivities[0]?.id).toBe("b-id");
            expect(reorderedActivities[1]?.id).toBe("a-id");
        });

        it("bounds the position within valid range", async () => {
            const activityStore = useActivityStore("default");
            await activityStore.sync();
            activityStore.setAll(newActivities);

            // move to an out-of-range index
            activityStore.setPosition("a-id", 100);

            const activities = activityStore.getAll();
            expect(activities[activities.length - 1]?.id).toBe("a-id");
        });

        it("does nothing when activity does not exist", async () => {
            const activityStore = useActivityStore("default");
            await activityStore.sync();
            activityStore.setAll(newActivities);

            const before = activityStore.getAll().map((a) => a.id);
            activityStore.setPosition("non-existent", 0);
            const after = activityStore.getAll().map((a) => a.id);

            expect(after).toEqual(before);
        });
    });

    describe("ensureSideBarOpen", () => {
        it("opens the sidebar for a panel activity", async () => {
            const activityStore = useActivityStore("default");
            await activityStore.sync();
            activityStore.setAll(newActivities);

            // Initially a-id is in the sidebar
            expect(activityStore.toggledSideBar).toBe("a-id");

            // Ensure b-id is open, which should set toggledSideBar to b-id
            activityStore.ensureSideBarOpen("b-id");
            expect(activityStore.toggledSideBar).toBe("b-id");
        });

        it("does nothing for unknown activity", async () => {
            const activityStore = useActivityStore("default");
            await activityStore.sync();

            const previous = activityStore.toggledSideBar;
            activityStore.ensureSideBarOpen("non-existent");
            expect(activityStore.toggledSideBar).toBe(previous);
        });
    });

    describe("ensureVisible", () => {
        it("marks an existing activity as visible", async () => {
            const activityStore = useActivityStore("default");
            await activityStore.sync();
            activityStore.setAll(newActivities);

            const activity = activityStore.findById("a-id");
            expect(activity?.visible).toBe(false);

            activityStore.ensureVisible("a-id");

            expect(activityStore.findById("a-id")?.visible).toBe(true);
        });

        it("does nothing for unknown activity", async () => {
            const activityStore = useActivityStore("default");
            await activityStore.sync();

            expect(() => activityStore.ensureVisible("non-existent")).not.toThrow();
        });
    });
});
