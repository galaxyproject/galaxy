import { createTestingPinia } from "@pinia/testing";
import { PiniaVuePlugin } from "pinia";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { Activities } from "@/stores/activitySetup";
import { useActivityStore } from "@/stores/activityStore";
import mountTarget from "./ActivitySettings.vue";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

const activityItemSelector = ".activity-settings-item";

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
    const filtered = wrapper.findAll(activityItemSelector);
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

    it("availability of built-in activities", async () => {
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(Activities.length);
    });

    it("visible but non-optional activity", async () => {
        activityStore.setAll([testActivity("1")]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(1);
        const pinnedCheckbox = items.at(0).find("[data-icon='thumbtack']");
        expect(pinnedCheckbox.exists()).toBeTruthy();
        const pinnedIcon = wrapper.find("[icon='activity-test-icon'");
        expect(pinnedIcon.exists()).toBeTruthy();
        expect(activityStore.getAll()[0].visible).toBeTruthy();
        pinnedCheckbox.trigger("click");
        await wrapper.vm.$nextTick();
        expect(activityStore.getAll()[0].visible).toBeTruthy();
    });

    it("non-visible but optional activity", async () => {
        activityStore.setAll([
            testActivity("1", {
                optional: true,
                visible: false,
            }),
        ]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(1);
        const hiddenCheckbox = items.at(0).find("[data-icon='square']");
        expect(hiddenCheckbox.exists()).toBeTruthy();
        expect(activityStore.getAll()[0].visible).toBeFalsy();
        hiddenCheckbox.trigger("click");
        await wrapper.vm.$nextTick();
        const visibleCheckbox = items.at(0).find("[data-icon='check-square']");
        expect(visibleCheckbox.exists()).toBeTruthy();
        expect(activityStore.getAll()[0].visible).toBeTruthy();
    });

    it("removable", async () => {
        activityStore.setAll([testActivity("1")]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(1);
        const trash = items.at(0).find("[data-icon='trash']");
        expect(trash.exists()).toBeTruthy();
        expect(activityStore.getAll().length).toBe(1);
        trash.trigger("click");
        await wrapper.vm.$nextTick();
        expect(activityStore.getAll().length).toBe(0);
    });

    it("non-removable", async () => {
        activityStore.setAll([
            testActivity("1", {
                mutable: false,
            }),
        ]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(1);
        const trash = items.at(0).find("[data-icon='trash']");
        expect(trash.exists()).toBeFalsy();
    });

    it("filter activities by title and description", async () => {
        activityStore.setAll([
            testActivity("1"),
            testActivity("2", { title: "something else" }),
            testActivity("3", { title: "SOMETHING different" }),
            testActivity("4", { description: "SOMEthing odd" }),
        ]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(4);
        await testSearch(wrapper, "else", 1);
        await testSearch(wrapper, "someTHING", 3);
        await testSearch(wrapper, "odd", 1);
    });
});
