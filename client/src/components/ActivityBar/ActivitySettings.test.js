import { createTestingPinia } from "@pinia/testing";
import { PiniaVuePlugin } from "pinia";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { useActivityStore } from "@/stores/activityStore";
import mountTarget from "./ActivitySettings.vue";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

function testActivity(newOptions = {}) {
    const defaultOptions = {
        id: "activity-test-id",
        description: "activity-test-description",
        icon: "activity-test-icon",
        mutable: true,
        optional: false,
        title: "activity-test-title",
        to: null,
        tooltip: "activity-test-tooltip",
        visible: true,
    };
    return { ...defaultOptions, ...newOptions };
}

describe("ActivitySettings", () => {
    let wrapper;

    beforeEach(async () => {
        const pinia = createTestingPinia({ stubActions: false });
        wrapper = mount(mountTarget, {
            localVue,
            pinia,
            stubs: {
                icon: { template: "<div></div>" },
            },
        });
    });

    it("availability of checkboxes and checkbox states", async () => {
        // check number of available default activities
        const items = wrapper.findAll("input[type='checkbox']");
        expect(items.length).toBe(8);

        // replace stored activity with a visible but non-optional test activity
        const activityStore = useActivityStore();
        activityStore.saveAll([testActivity()]);
        await wrapper.vm.$nextTick();
        const visibleItems = wrapper.findAll(".activity-settings-item");
        expect(visibleItems.length).toBe(1);
        const visibleCheckbox = visibleItems.at(0).find("input");
        expect(visibleCheckbox.attributes("disabled")).toBe("disabled");
        expect(visibleCheckbox.element.checked).toBeTruthy();
        const visibleIcon = wrapper.find("[icon='activity-test-icon'");
        expect(visibleIcon.exists()).toBe(true);

        // replace stored activity with a non-visible but optional test activity
        activityStore.saveAll([
            testActivity({
                optional: true,
                visible: false,
            }),
        ]);
        await wrapper.vm.$nextTick();
        const hiddenItems = wrapper.findAll(".activity-settings-item");
        expect(hiddenItems.length).toBe(1);
        const hiddenCheckbox = visibleItems.at(0).find("input");
        expect(hiddenCheckbox.attributes("disabled")).toBeUndefined;
        expect(hiddenCheckbox.element.checked).toBeFalsy();
    });
});
