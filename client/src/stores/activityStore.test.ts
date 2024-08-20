import { createPinia, setActivePinia } from "pinia";

import { useActivityStore } from "@/stores/activityStore";

// mock Galaxy object
jest.mock("./activitySetup", () => ({
    Activities: [
        {
            anonymous: false,
            description: "a-description",
            icon: "a-icon",
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
        icon: "a-icon-new",
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
        icon: "b-icon-new",
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
    });

    it("initialize store", () => {
        const activityStore = useActivityStore("default");
        expect(activityStore.getAll().length).toBe(0);
        activityStore.sync();
        expect(activityStore.getAll().length).toBe(1);
    });

    it("add activity", () => {
        const activityStore = useActivityStore("default");
        activityStore.sync();
        const initialActivities = activityStore.getAll();
        expect(initialActivities[0]?.visible).toBeTruthy();
        activityStore.setAll(newActivities);
        expect(activityStore.activities.length).toBe(2);
        const currentActivities = activityStore.getAll();
        expect(currentActivities[0]).toEqual(newActivities[0]);
        expect(currentActivities[1]).toEqual(newActivities[1]);
        activityStore.sync();
        const syncActivities = activityStore.getAll();
        expect(syncActivities.length).toEqual(2);
        expect(syncActivities[0]?.description).toEqual("a-description");
        expect(syncActivities[0]?.visible).toBeFalsy();
        expect(syncActivities[1]).toEqual(newActivities[1]);
    });

    it("remove activity", () => {
        const activityStore = useActivityStore("default");
        activityStore.sync();
        const initialActivities = activityStore.getAll();
        expect(initialActivities.length).toEqual(1);
        activityStore.remove("a-id");
        expect(activityStore.getAll().length).toEqual(0);
        activityStore.sync();
        expect(activityStore.getAll().length).toEqual(1);
        activityStore.setAll(newActivities);
        expect(activityStore.getAll().length).toEqual(2);
        activityStore.remove("b-id");
        activityStore.sync();
        expect(activityStore.getAll().length).toEqual(1);
    });
});
