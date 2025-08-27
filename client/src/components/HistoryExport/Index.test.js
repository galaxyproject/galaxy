import { createTestingPinia } from "@pinia/testing";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useFileSources } from "@/composables/fileSources";

import Index from "./Index.vue";

jest.mock("@/composables/fileSources");

const globalConfig = getLocalVue();

useFileSources.mockReturnValue({ isLoading: false, hasWritable: true });

describe("Index.vue", () => {
    it("should render tabs", async () => {
        // just make sure the component renders to catch obvious big errors
        const pinia = createTestingPinia();
        setActivePinia(pinia);
        const wrapper = shallowMount(Index, {
            props: {
                historyId: "test_id",
            },
            global: {
                ...globalConfig.global,
                plugins: [...globalConfig.global.plugins, pinia],
            },
        });
        await flushPromises();
        const tabs = wrapper.find(".history-export-tabs");
        expect(tabs.exists()).toBeTruthy();
    });
});
