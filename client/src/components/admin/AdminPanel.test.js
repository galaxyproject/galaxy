import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import MountTarget from "./AdminPanel.vue";

const localVue = getLocalVue(true);

function createTarget(propsData = {}) {
    return mount(MountTarget, {
        localVue,
        propsData,
        stubs: {
            routerLink: true,
        },
    });
}

describe("AdminPanel", () => {
    it("ensure reactivity to prop changes", async () => {
        const wrapper = createTarget();
        const sections = {
            isToolshedInstalled: "#admin-link-toolshed",
            enableQuotas: "#admin-link-quotas",
        };
        for (const elementId of Object.values(sections)) {
            expect(wrapper.find(elementId).exists()).toBe(false);
        }
        for (const available of [true, false]) {
            for (const [propId, elementId] of Object.entries(sections)) {
                const props = {};
                props[propId] = available;
                await wrapper.setProps(props);
                expect(wrapper.find(elementId).exists()).toBe(available);
            }
        }
    });
});
