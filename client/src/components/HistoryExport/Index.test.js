import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { vi } from "vitest";

import { useFileSources } from "@/composables/fileSources";

import Index from "./Index.vue";

vi.mock("@/composables/fileSources");

const localVue = getLocalVue();

useFileSources.mockReturnValue({ isLoading: false, hasWritable: true });

describe("Index.vue", () => {
    it("should render tabs", async () => {
        // just make sure the component renders to catch obvious big errors
        const pinia = createTestingPinia();
        const wrapper = shallowMount(Index, {
            propsData: {
                historyId: "test_id",
            },
            localVue,
            pinia,
        });
        await flushPromises();
        const tabs = wrapper.findComponent(".history-export-tabs");
        expect(tabs.exists()).toBeTruthy();
    });
});
