import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import type { UserConcreteObjectStoreModel } from "@/api";
import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import TargetObjectStoreSelector from "./TargetObjectStoreSelector.vue";

const localVue = getLocalVue(true);
const { server, http } = useServerMock();

const PRIVATE_STORE: UserConcreteObjectStoreModel = {
    object_store_id: "object_store_private",
    name: "Private Store",
    description: "Private storage",
    badges: [],
    private: true,
    quota: { enabled: false },
    active: true,
    hidden: false,
    purged: false,
    secrets: [],
    template_id: "",
    template_version: 0,
    type: "disk",
    uuid: "private-uuid",
    variables: null,
};

const SHARABLE_STORE: UserConcreteObjectStoreModel = {
    ...PRIVATE_STORE,
    object_store_id: "object_store_public",
    name: "Sharable Store",
    private: false,
};

async function mountSelector(targetObjectStoreId = PRIVATE_STORE.object_store_id) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const objectStoreStore = useObjectStoreStore();
    objectStoreStore.selectableObjectStores = [PRIVATE_STORE, SHARABLE_STORE];

    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response(200).json({});
        }),
        http.get("/api/object_stores", ({ response }) => {
            return response(200).json([PRIVATE_STORE, SHARABLE_STORE]);
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
            targetObjectStoreId,
        },
        localVue,
        pinia,
    });

    await flushPromises();
    return wrapper;
}

describe("TargetObjectStoreSelector", () => {
    it("shows a warning when a private store is selected for a public history", async () => {
        const wrapper = await mountSelector();

        expect(wrapper.text()).toContain(
            "Selected storage location is private while this history still allows sharable datasets.",
        );
    });

    it("does not show the privacy warning for a sharable store", async () => {
        const wrapper = await mountSelector(SHARABLE_STORE.object_store_id);

        expect(wrapper.text()).not.toContain("still allows sharable datasets");
    });
});
