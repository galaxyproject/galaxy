import { createTestingPinia } from "@pinia/testing";
import { PiniaVuePlugin } from "pinia";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { useActivityStore } from "@/stores/activityStore";
import mountTarget from "./ActivitySettings.vue";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

function testActivity(id, newOptions = {}) {
    const defaultOptions = {
        id: `activity-test-${id}`,
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

async function testSearch(wrapper, query, result) {
    const searchField = wrapper.find("input");
    searchField.element.value = query;
    searchField.trigger("change");
    await wrapper.vm.$nextTick();
    const filtered = wrapper.findAll(".activity-settings-item");
    expect(filtered.length).toBe(result);
}

describe("ActivitySettings", () => {
    let activityStore;
    let wrapper;

    beforeEach(async () => {
        const pinia = createTestingPinia({ stubActions: false });
        activityStore = useActivityStore();
        activityStore.sync();
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
        const items = wrapper.findAll(".activity-settings-item");
        expect(items.length).toBe(8);

        // replace stored activity with a visible but non-optional test activity
        activityStore.setAll([testActivity("1")]);
        await wrapper.vm.$nextTick();
        const visibleItems = wrapper.findAll(".activity-settings-item");
        expect(visibleItems.length).toBe(1);
        const visibleCheckbox = visibleItems.at(0).find("[data-icon='thumbtack']");
        expect(visibleCheckbox.exists()).toBeTruthy();
        const visibleIcon = wrapper.find("[icon='activity-test-icon'");
        expect(visibleIcon.exists()).toBe(true);

        // replace stored activity with a non-visible but optional test activity
        activityStore.setAll([
            testActivity("1", {
                optional: true,
                visible: false,
            }),
        ]);
        await wrapper.vm.$nextTick();
        const hiddenItems = wrapper.findAll(".activity-settings-item");
        expect(hiddenItems.length).toBe(1);
        const hiddenCheckbox = visibleItems.at(0).find("[data-icon='square']");
        expect(hiddenCheckbox.exists()).toBeTruthy();
    });

    it("filtering", async () => {
        // replace stored activity with a visible but non-optional test activity
        activityStore.setAll([
            testActivity("1"),
            testActivity("2", { title: "something else" }),
            testActivity("3", { title: "SOMETHING different" }),
            testActivity("4", { description: "SOMEthing odd" }),
        ]);
        await wrapper.vm.$nextTick();
        const visibleItems = wrapper.findAll(".activity-settings-item");
        expect(visibleItems.length).toBe(4);
        await testSearch(wrapper, "else", 1);
        await testSearch(wrapper, "someTHING", 3);
        await testSearch(wrapper, "odd", 1);
    });
});
