import { getFakeObjectStoreInstance } from "@tests/test-data/objectStores";
import { beforeEach, describe, expect, it } from "vitest";

import { useObjectStoreInstancesStore } from "@/stores/objectStoreInstancesStore";

import { setupTestPinia } from "./testUtils";

const UUID = "112f889f-72d7-4619-a8e8-510a8c685aa7";

describe("Object Store Instances Store", () => {
    beforeEach(setupTestPinia);

    it("starts without fetched instances", () => {
        const store = useObjectStoreInstancesStore();
        expect(store.fetched).toBeFalsy();
    });

    it("starts without an error", () => {
        const store = useObjectStoreInstancesStore();
        expect(store.error).toBeFalsy();
    });

    it("marks instances as fetched after initialization", async () => {
        const store = useObjectStoreInstancesStore();
        const instance = getFakeObjectStoreInstance({ uuid: UUID, name: "moo" });

        await store.handleInit([instance]);

        expect(store.instances).toHaveLength(1);
        expect(store.fetched).toBeTruthy();
    });

    it("finds an initialized instance by its UUID", async () => {
        const store = useObjectStoreInstancesStore();
        const instance = getFakeObjectStoreInstance({ uuid: UUID, name: "moo" });

        await store.handleInit([instance]);

        expect(store.getInstance(UUID)?.name).toBe("moo");
    });

    it("records the message from an error", async () => {
        const store = useObjectStoreInstancesStore();

        await store.handleError(Error("an error"));

        expect(store.error).toBe("an error");
    });
});
