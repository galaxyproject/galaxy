import { createTestingPinia } from "@pinia/testing";
import { PiniaVuePlugin } from "pinia";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { useActivityStore } from "@/stores/activityStore";
import mountTarget from "./ActivityBar.vue";

jest.mock("vue-router/composables", () => ({
    useRoute: jest.fn(() => ({})),
}));

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

function testActivity(id, newOptions = {}) {
    const defaultOptions = {
        id: `test-${id}`,
        description: "test-description",
        icon: "test-icon",
        mutable: true,
        optional: false,
        title: "test-title",
        to: "test-to",
        tooltip: "test-tooltip",
        visible: true,
    };
    return { ...defaultOptions, ...newOptions };
}

describe("ActivityBar", () => {
    let activityStore;
    let wrapper;

    beforeEach(async () => {
        const pinia = createTestingPinia({ stubActions: false });
        activityStore = useActivityStore();
        wrapper = shallowMount(mountTarget, {
            localVue,
            pinia,
        });
    });

    it("rendering", async () => {
        activityStore.setAll([testActivity("1"), testActivity("2"), testActivity("3")]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll("[title='test-title']");
        expect(items.length).toBe(3);
    });
});
