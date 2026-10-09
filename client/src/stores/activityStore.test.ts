import { faWrench } from "@fortawesome/free-solid-svg-icons";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ensureDefined } from "@/utils/assertions";

import { defaultActivities } from "./activitySetup";
import { useActivityStore } from "./activityStore";
import type { Activity } from "./activityStoreTypes";
import { setupTestPinia } from "./testUtils";

vi.mock("./activitySetup", async () => {
    const { faFlask } = await import("@fortawesome/free-solid-svg-icons");
    return {
        defaultActivities: [
            {
                anonymous: false,
                description: "a-description",
                icon: faFlask,
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
    };
});

function getUpdatedActivities(): Activity[] {
    const defaultActivity = ensureDefined(defaultActivities[0]);
    return [
        {
            ...defaultActivity,
            description: "a-description-new",
            icon: faWrench,
            to: "a-to-new",
            tooltip: "a-tooltip-new",
            visible: false,
        },
        {
            ...defaultActivity,
            description: "b-description-new",
            icon: faWrench,
            id: "b-id",
            mutable: true,
            title: "b-title-new",
            to: "b-to-new",
            tooltip: "b-tooltip-new",
        },
    ];
}

async function createSyncedStore(activities?: Activity[]) {
    const store = useActivityStore("default");
    await store.sync();
    if (activities) {
        store.setAll(activities);
    }
    return store;
}

describe("Activity Store", () => {
    beforeEach(() => {
        setupTestPinia();
        // ensure clean localStorage between tests (useUserLocalStorage persistence)
        localStorage.clear();
    });

    it("initializes with default activities after sync", async () => {
        const activityStore = useActivityStore("default");
        expect(activityStore.getAll()).toEqual([]);
        await activityStore.sync();
        expect(activityStore.getAll()).toEqual(defaultActivities);
    });

    it("merges built-in and custom activities on sync", async () => {
        const activityStore = await createSyncedStore();
        const initialActivities = activityStore.getAll();
        expect(initialActivities[0]?.visible).toBe(true);
        const updatedActivities = getUpdatedActivities();
        activityStore.setAll(updatedActivities);
        expect(activityStore.activities).toHaveLength(2);
        const currentActivities = activityStore.getAll();
        expect(currentActivities[0]).toEqual(updatedActivities[0]);
        expect(currentActivities[1]).toEqual(updatedActivities[1]);
        await activityStore.sync();
        const syncActivities = activityStore.getAll();
        expect(syncActivities).toHaveLength(2);
        expect(syncActivities[0]?.description).toEqual("a-description");
        expect(syncActivities[0]?.visible).toBe(false);
        expect(syncActivities[1]).toEqual(updatedActivities[1]);
    });

    it("restores a removed built-in activity on sync", async () => {
        const activityStore = await createSyncedStore();
        expect(activityStore.getAll()).toEqual(defaultActivities);

        activityStore.remove("a-id");
        expect(activityStore.getAll()).toEqual([]);
        await activityStore.sync();

        expect(activityStore.getAll()).toEqual(defaultActivities);
    });

    it("keeps a removed custom activity absent after sync", async () => {
        const activityStore = await createSyncedStore(getUpdatedActivities());
        expect(activityStore.getAll()).toHaveLength(2);

        activityStore.remove("b-id");
        await activityStore.sync();

        expect(activityStore.getAll().map(({ id }) => id)).toEqual(["a-id"]);
    });

    describe("setPosition", () => {
        it("reorders an activity to the specified position", async () => {
            const activityStore = await createSyncedStore(getUpdatedActivities());

            const initialActivities = activityStore.getAll();
            expect(initialActivities.map(({ id }) => id)).toEqual(["a-id", "b-id"]);

            activityStore.setPosition("b-id", 0);

            const reorderedActivities = activityStore.getAll();
            expect(reorderedActivities.map(({ id }) => id)).toEqual(["b-id", "a-id"]);
        });

        it("bounds the position within valid range", async () => {
            const activityStore = await createSyncedStore(getUpdatedActivities());

            activityStore.setPosition("a-id", 100);

            const activities = activityStore.getAll();
            expect(activities[activities.length - 1]?.id).toBe("a-id");
        });

        it("does nothing when activity does not exist", async () => {
            const activityStore = await createSyncedStore(getUpdatedActivities());

            const before = activityStore.getAll().map((a) => a.id);
            activityStore.setPosition("non-existent", 0);
            const after = activityStore.getAll().map((a) => a.id);

            expect(after).toEqual(before);
        });
    });

    describe("ensureSideBarOpen", () => {
        it("opens the sidebar for a panel activity", async () => {
            const activityStore = await createSyncedStore(getUpdatedActivities());

            expect(activityStore.toggledSideBar).toBe("a-id");

            activityStore.ensureSideBarOpen("b-id");
            expect(activityStore.toggledSideBar).toBe("b-id");
        });

        it("does nothing for unknown activity", async () => {
            const activityStore = await createSyncedStore();

            const previous = activityStore.toggledSideBar;
            activityStore.ensureSideBarOpen("non-existent");
            expect(activityStore.toggledSideBar).toBe(previous);
        });
    });

    describe("setSpecialPanelActivityIds", () => {
        it("prevents sync from resetting toggledSideBar when set to a registered special panel activity", async () => {
            const activityStore = await createSyncedStore();

            activityStore.setSpecialPanelActivityIds(["special-panel-id"]);
            activityStore.toggledSideBar = "special-panel-id";

            await activityStore.sync();

            expect(activityStore.toggledSideBar).toBe("special-panel-id");
        });

        it("still resets toggledSideBar when it is not in defaults or registered special activities", async () => {
            const activityStore = await createSyncedStore();

            activityStore.setSpecialPanelActivityIds([]);
            activityStore.toggledSideBar = "unknown-panel-id";

            await activityStore.sync();

            expect(activityStore.toggledSideBar).toBe("a-id");
        });

        it("resets toggledSideBar after special activity is unregistered", async () => {
            const activityStore = await createSyncedStore();

            activityStore.setSpecialPanelActivityIds(["special-panel-id"]);
            activityStore.toggledSideBar = "special-panel-id";
            await activityStore.sync();
            expect(activityStore.toggledSideBar).toBe("special-panel-id");

            activityStore.setSpecialPanelActivityIds([]);
            await activityStore.sync();
            expect(activityStore.toggledSideBar).toBe("a-id");
        });
    });

    describe("ensureVisible", () => {
        it("marks an existing activity as visible", async () => {
            const activityStore = await createSyncedStore(getUpdatedActivities());

            const activity = activityStore.findById("a-id");
            expect(activity?.visible).toBe(false);

            activityStore.ensureVisible("a-id");

            expect(activityStore.findById("a-id")?.visible).toBe(true);
        });

        it("does nothing for unknown activity", async () => {
            const activityStore = await createSyncedStore();

            const before = activityStore.getAll().map((activity) => ({ ...activity }));

            expect(() => activityStore.ensureVisible("non-existent")).not.toThrow();

            expect(activityStore.getAll()).toEqual(before);
        });
    });
});
