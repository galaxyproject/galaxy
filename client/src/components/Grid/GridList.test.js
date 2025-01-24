import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { PiniaVuePlugin } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import { setupMockConfig } from "tests/jest/mockConfig";

import Filtering from "@/utils/filtering";

import MountTarget from "./GridList.vue";

jest.useFakeTimers();

setupMockConfig({ disabled: false, enabled: true });

jest.mock("vue-router/composables");

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

const testGrid = {
    actions: [
        {
            title: "test",
            icon: "test-icon",
            handler: jest.fn(),
        },
    ],
    fields: [
        {
            key: "id",
            title: "id",
            type: "text",
        },
        {
            key: "link",
            title: "link",
            type: "link",
        },
        {
            key: "operation",
            title: "operation",
            type: "operations",
            condition: jest.fn(() => true),
            operations: [
                {
                    title: "operation-title-1",
                    icon: "operation-icon-1",
                    condition: (_, config) => config.value.enabled,
                    handler: jest.fn(),
                },
                {
                    title: "operation-title-2",
                    icon: "operation-icon-2",
                    condition: (_, config) => config.value.disabled,
                    handler: jest.fn(),
                },
                {
                    title: "operation-title-3",
                    icon: "operation-icon-3",
                    condition: (_, config) => config.value.enabled,
                    handler: () => ({
                        status: "success",
                        message: "Operation-3 has been executed.",
                    }),
                },
            ],
        },
    ],
    filtering: new Filtering({}, undefined, false, false),
    getData: jest.fn((offset, limit) => {
        const data = [];
        for (let i = offset; i < offset + limit; i++) {
            data.push({
                id: `id-${i + 1}`,
                link: `link-${i + 1}`,
                operation: `operation-${i + 1}`,
            });
        }
        return [data, 100];
    }),
    plural: "Tests",
    sortBy: "id",
    sortDesc: true,
    sortKeys: ["id"],
    title: "Test",
};

function createTarget(propsData) {
    const pinia = createTestingPinia({ stubActions: false });
    return mount(MountTarget, {
        localVue,
        propsData,
        pinia,
        stubs: {
            Icon: true,
        },
    });
}

describe("GridList", () => {
    it("basic rendering", async () => {
        const wrapper = createTarget({
            gridConfig: testGrid,
        });
        const findInput = wrapper.find("[data-description='filter text input']");
        expect(findInput.attributes().placeholder).toBe("search tests");
        expect(wrapper.find(".loading-message").text()).toBe("Loading...");
        const findAction = wrapper.find("[data-description='grid action test']");
        expect(findAction.text()).toBe("test");
        await findAction.trigger("click");
        expect(testGrid.actions[0].handler).toHaveBeenCalledTimes(1);
        expect(testGrid.getData).toHaveBeenCalledTimes(1);
        expect(testGrid.getData.mock.calls[0]).toEqual([0, 25, "", "id", true]);
        expect(findAction.find("[icon='test-icon']").exists()).toBeTruthy();
        await wrapper.vm.$nextTick();
        expect(wrapper.find("[data-description='grid title']").text()).toBe("Test");
        expect(wrapper.find("[data-description='grid cell 0-0']").text()).toBe("id-1");
        expect(wrapper.find("[data-description='grid cell 1-0']").text()).toBe("id-2");
        expect(wrapper.find("[data-description='grid cell 0-1'] > button").text()).toBe("link-1");
        expect(wrapper.find("[data-description='grid cell 1-1'] > button").text()).toBe("link-2");
        const firstHeader = wrapper.find("[data-description='grid header 0']");
        expect(firstHeader.find("button").text()).toBe("id");
        await firstHeader.find("[data-description='grid sort desc']").trigger("click");
        expect(testGrid.getData).toHaveBeenCalledTimes(2);
        expect(testGrid.getData.mock.calls[1]).toEqual([0, 25, "", "id", false]);
        expect(firstHeader.find("[data-description='grid sort desc']").exists()).toBeFalsy();
        expect(firstHeader.find("[data-description='grid sort asc']").exists()).toBeTruthy();
        const secondHeader = wrapper.find("[data-description='grid header 1']");
        expect(secondHeader.find("[data-description='grid sort desc']").exists()).toBeFalsy();
        expect(secondHeader.find("[data-description='grid sort asc']").exists()).toBeFalsy();
    });

    it("header rendering", async () => {
        const wrapper = createTarget({
            gridConfig: testGrid,
        });
        await wrapper.vm.$nextTick();
        for (const [fieldIndex, field] of Object.entries(testGrid.fields)) {
            expect(wrapper.find(`[data-description='grid header ${fieldIndex}']`).text()).toBe(field.title);
        }
    });

    it("operation handling", async () => {
        const wrapper = createTarget({
            gridConfig: testGrid,
        });
        await wrapper.vm.$nextTick();
        const dropdown = wrapper.find("[data-description='grid cell 0-2']");
        const dropdownItems = dropdown.findAll(".dropdown-item");
        expect(dropdownItems.at(0).text()).toBe("operation-title-1");
        expect(dropdownItems.at(1).text()).toBe("operation-title-3");
        await dropdownItems.at(0).trigger("click");
        const clickHandler = testGrid.fields[2].operations[0].handler;
        expect(clickHandler).toHaveBeenCalledTimes(1);
        expect(clickHandler.mock.calls[0]).toEqual([{ id: "id-1", link: "link-1", operation: "operation-1" }]);
        await dropdownItems.at(1).trigger("click");
        await flushPromises();
        const alert = wrapper.find(".alert");
        expect(alert.text()).toBe("Operation-3 has been executed.");
        jest.runAllTimers();
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".alert").exists()).toBeFalsy();
    });

    it("filter handling", async () => {
        const wrapper = createTarget({
            gridConfig: testGrid,
        });
        await wrapper.vm.$nextTick();
        const filterInput = wrapper.find("[data-description='filter text input']");
        await filterInput.setValue("filter query");
        jest.runAllTimers();
        await flushPromises();
        expect(testGrid.getData).toHaveBeenCalledTimes(2);
        expect(testGrid.getData.mock.calls[1]).toEqual([0, 25, "filter query", "id", true]);
    });

    it("pagination", async () => {
        const wrapper = createTarget({
            gridConfig: testGrid,
            limit: 2,
        });
        await wrapper.vm.$nextTick();
        const pageLinks = wrapper.findAll(".page-link");
        await pageLinks.at(4).trigger("click");
        expect(wrapper.find("[data-description='grid cell 0-0']").text()).toBe("id-5");
        expect(wrapper.find("[data-description='grid cell 1-0']").text()).toBe("id-6");
    });
});
