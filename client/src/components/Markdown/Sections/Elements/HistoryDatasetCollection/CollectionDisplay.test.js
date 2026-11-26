import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { embedKey } from "@/composables/embed";

import CollectionDisplay from "./CollectionDisplay.vue";

vi.mock("@/stores/userStore", () => ({ useUserStore: () => ({ currentUser: { id: "user_id" } }) }));
vi.mock("@/stores/historyStore", () => ({ useHistoryStore: () => ({ currentHistoryId: "history_id" }) }));

const localVue = getLocalVue();
const { server, http } = useServerMock();

async function mountDisplay(provide = {}) {
    server.use(
        http.get("/api/dataset_collections/{hdca_id}", ({ response }) =>
            response(200).json({ name: "collection_name", elements: [] }),
        ),
    );
    const wrapper = mount(CollectionDisplay, {
        global: { ...localVue, provide, stubs: { ...localVue.stubs, CollectionTree: true } },
        propsData: { collectionId: "collection_id" },
    });
    await flushPromises();
    return wrapper;
}

describe("CollectionDisplay", () => {
    it("offers the import to a signed-in user", async () => {
        const wrapper = await mountDisplay();
        expect(wrapper.find(".fa-file-import").exists()).toBe(true);
    });

    it("offers no import when embedded", async () => {
        const wrapper = await mountDisplay({ [embedKey]: ref(true) });
        expect(wrapper.find(".fa-file-import").exists()).toBe(false);
    });
});
