import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, test, vi } from "vitest";
import { nextTick } from "vue";

import { useUserStore } from "@/stores/userStore";

import Tool from "./Tool.vue";

const localVue = getLocalVue();

describe("Tool", () => {
    test("test tool", () => {
        const pinia = createTestingPinia({ createSpy: vi.fn });
        const wrapper = mount(Tool as object, {
            propsData: {
                tool: {
                    id: "test_tool",
                },
            },
            localVue,
            pinia,
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.at(0).text()).toBe("");
        nameElement.trigger("click");
        expect(wrapper.emitted().onClick).toBeDefined();
        const labelsElement = wrapper.find(".labels");
        expect(labelsElement.element.children.length).toBe(0);
    });
    test("test tool hide name, test description", () => {
        const pinia = createTestingPinia({ createSpy: vi.fn });
        const wrapper = mount(Tool as object, {
            propsData: {
                tool: {
                    id: "test_tool",
                    name: "name",
                    description: "description",
                },
                hideName: true,
            },
            localVue,
            pinia,
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.length).toBe(0);
        const descriptionElement = wrapper.find(".description");
        expect(descriptionElement.text()).toBe("description");
    });

    test("favorite button is focusable for keyboard navigation", async () => {
        const pinia = createTestingPinia({ createSpy: vi.fn });
        const wrapper = mount(Tool as object, {
            propsData: {
                tool: {
                    id: "test_tool",
                    name: "name",
                },
            },
            localVue,
            pinia,
            attachTo: document.body,
        });
        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: ["test_tool"] } };
        await nextTick();

        const favoriteButton = wrapper.find('.tool-favorite-button-hover[data-tool-id="test_tool"]');
        expect(favoriteButton.exists()).toBe(true);
        (favoriteButton.element as HTMLElement).focus();
        expect(document.activeElement).toBe(favoriteButton.element);

        wrapper.destroy();
    });
});
