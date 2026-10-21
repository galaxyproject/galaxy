import { createTestingPinia } from "@pinia/testing";
import { getFakeObjectStoreInstance } from "@tests/test-data/objectStores";
import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import TargetObjectStoreSelector from "./TargetObjectStoreSelector.vue";

enableAutoUnmount(afterEach);

const { server, http } = useServerMock();

async function mountSelector({ private: isPrivate }: { private: boolean }) {
    const privateStore = getFakeObjectStoreInstance({
        object_store_id: "object_store_private",
        name: "Private Store",
        description: "Private storage",
        private: true,
        template_id: "",
        type: "disk",
        uuid: "private-uuid",
        variables: null,
    });
    const sharableStore = getFakeObjectStoreInstance({
        ...privateStore,
        object_store_id: "object_store_public",
        name: "Sharable Store",
        private: false,
    });
    const stores = [privateStore, sharableStore];
    const localVue = getLocalVue(true);
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const objectStoreStore = useObjectStoreStore();
    objectStoreStore.selectableObjectStores = stores;

    server.use(
        http.get("/api/object_stores", ({ response }) => {
            return response(200).json(stores);
        }),
        http.untyped.get("/history/permissions", () => {
            return HttpResponse.json({
                inputs: [
                    { name: "DATASET_MANAGE_PERMISSIONS", value: [1] },
                    { name: "DATASET_ACCESS", value: [] },
                ],
            });
        }),
    );

    const wrapper = mount(TargetObjectStoreSelector as object, {
        propsData: {
            targetHistoryId: "history-1",
            targetObjectStoreId: isPrivate ? privateStore.object_store_id : sharableStore.object_store_id,
        },
        localVue,
        pinia,
    });

    await flushPromises();
    return wrapper;
}

describe("TargetObjectStoreSelector", () => {
    it("shows a warning when a private store is selected for a public history", async () => {
        const wrapper = await mountSelector({ private: true });

        expect(wrapper.text()).toContain(
            "Selected storage location is private while this history still allows sharable datasets.",
        );
    });

    it("does not show the privacy warning for a sharable store", async () => {
        const wrapper = await mountSelector({ private: false });

        expect(wrapper.text()).toContain("Sharable Store");
        expect(wrapper.text()).not.toContain("still allows sharable datasets");
    });
});
