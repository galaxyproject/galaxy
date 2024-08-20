import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { PiniaVuePlugin } from "pinia";
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
        optional: true,
        title: "activity-test-title",
        to: null,
        tooltip: "activity-test-tooltip",
        visible: true,
    };
    return { ...defaultOptions, ...newOptions };
}

async function testSearch(wrapper, query, result) {
    await wrapper.setProps({ query });
    const filtered = wrapper.findAll(activityItemSelector);
    expect(filtered.length).toBe(result);
}

describe("ActivitySettings", () => {
    let activityStore;
    let wrapper;

    beforeEach(async () => {
        const pinia = createTestingPinia({ stubActions: false });
        activityStore = useActivityStore("default");
        activityStore.sync();
        wrapper = mount(mountTarget, {
            localVue,
            pinia,
            props: {
                query: "",
                activityBarScope: "default",
            },
            stubs: {
                icon: { template: "<div></div>" },
            },
        });
    });

    it("availability of built-in activities", async () => {
        const items = wrapper.findAll(activityItemSelector);
        const nOptional = Activities.filter((x) => x.optional).length;
        expect(items.length).toBe(nOptional);
    });

    it("visible and optional activity", async () => {
        activityStore.setAll([testActivity("1")]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(1);
        const checkbox = items.at(0).find("[title='Hide in Activity Bar']");
        expect(checkbox.exists()).toBeTruthy();
        const icon = wrapper.find("[icon='activity-test-icon'");
        expect(icon.exists()).toBeTruthy();
        expect(activityStore.getAll()[0].visible).toBeTruthy();
        checkbox.trigger("click");
        await wrapper.vm.$nextTick();
        expect(activityStore.getAll()[0].visible).toBeFalsy();
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
        const checkbox = items.at(0).find("[title='Show in Activity Bar']");
        expect(checkbox.exists()).toBeTruthy();
        expect(activityStore.getAll()[0].visible).toBeFalsy();
        checkbox.trigger("click");
        await wrapper.vm.$nextTick();
        const visibleCheckbox = items.at(0).find("[title='Hide in Activity Bar']");
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
