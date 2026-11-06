import { faCog, faCopy, faFilter, faFolder } from "@fortawesome/free-solid-svg-icons";
import { createTestingPinia } from "@pinia/testing";
import { deferred } from "@tests/vitest/deferred";
import { getLocalVue, nth } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import type { GalaxyConfiguration } from "@/stores/configurationStore";
import Filtering, { equals } from "@/utils/filtering";

import type { GridConfig, RowData } from "./configs/types";

import MountTarget from "./GridList.vue";

vi.useFakeTimers();

setupMockConfig({ disabled: false, enabled: true });

vi.mock("vue-router");

const localVue = getLocalVue();

function createTestGrid(): GridConfig {
    return {
        id: "test-grid",
        actions: [
            {
                title: "test",
                icon: faCopy as any,
                handler: vi.fn(),
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
                condition: vi.fn(() => true),
                operations: [
                    {
                        title: "operation-title-1",
                        icon: faCog as any,
                        condition: (_: RowData, config: GalaxyConfiguration) => config.value.enabled,
                        handler: vi.fn(),
                    },
                    {
                        title: "operation-title-2",
                        icon: faFilter as any,
                        condition: (_: RowData, config: GalaxyConfiguration) => config.value.disabled,
                        handler: vi.fn(),
                    },
                    {
                        title: "operation-title-3",
                        icon: faFolder as any,
                        condition: (_: RowData, config: GalaxyConfiguration) => config.value.enabled,
                        handler: async () => ({
                            status: "success",
                            message: "Operation-3 has been executed.",
                        }),
                    },
                ],
            },
        ],
        filtering: new Filtering({}, undefined, false),
        getData: vi.fn(async (offset: number, limit: number): Promise<[RowData[], number]> => {
            const data: RowData[] = [];
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
}

interface TargetProps {
    gridConfig: GridConfig;
    limit?: number;
}

function createTarget(propsData: TargetProps) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    return mount(MountTarget as object, {
        global: localVue,
        propsData,
        pinia,
    });
}

describe("GridList", () => {
    it("basic rendering", async () => {
        const testGrid = createTestGrid();
        const wrapper = createTarget({
            gridConfig: testGrid,
        });
        const findInput = wrapper.find("[data-description='filter text input']");
        expect(findInput.attributes().placeholder).toBe("search tests");
        expect(wrapper.find("[data-description='grid initial loading']").exists()).toBeTruthy();
        const findAction = wrapper.find("[data-description='grid action test']");
        expect(findAction.text()).toBe("test");
        await findAction.trigger("click");
        expect(testGrid.actions![0]!.handler).toHaveBeenCalledTimes(1);
        expect(testGrid.getData).toHaveBeenCalledTimes(1);
        expect(vi.mocked(testGrid.getData).mock.calls[0]!.slice(0, 5)).toEqual([0, 25, "", "id", true]);
        expect(findAction.find("svg").exists()).toBeTruthy();
        await wrapper.vm.$nextTick();
        expect(wrapper.find("[data-description='grid title']").text()).toBe("Test");
        expect(wrapper.find("[data-description='grid cell 0-0']").text()).toBe("id-1");
        expect(wrapper.find("[data-description='grid cell 1-0']").text()).toBe("id-2");
        expect(wrapper.find("[data-description='grid cell 0-1'] > button").text()).toBe("link-1");
        expect(wrapper.find("[data-description='grid cell 1-1'] > button").text()).toBe("link-2");
        const firstHeader = wrapper.find("[data-description='grid header 0']");
        expect(firstHeader.find("button").text()).toBe("id");
        await firstHeader.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        await flushPromises();
        expect(testGrid.getData).toHaveBeenCalledTimes(2);
        expect(vi.mocked(testGrid.getData).mock.calls[1]!.slice(0, 5)).toEqual([0, 25, "", "id", false]);
        expect(firstHeader.find("[data-description='grid sort desc']").exists()).toBeFalsy();
        expect(firstHeader.find("[data-description='grid sort asc']").exists()).toBeTruthy();
        const secondHeader = wrapper.find("[data-description='grid header 1']");
        expect(secondHeader.find("[data-description='grid sort desc']").exists()).toBeFalsy();
        expect(secondHeader.find("[data-description='grid sort asc']").exists()).toBeFalsy();
    });

    it("header rendering", async () => {
        const testGrid = createTestGrid();
        const wrapper = createTarget({
            gridConfig: testGrid,
        });
        await flushPromises();
        for (const [fieldIndex, field] of Object.entries(testGrid.fields)) {
            expect(wrapper.find(`[data-description='grid header ${fieldIndex}']`).text()).toBe(field.title);
        }
    });

    it("operation handling", async () => {
        const testGrid = createTestGrid();
        const wrapper = createTarget({
            gridConfig: testGrid,
        });
        await flushPromises();
        const dropdown = wrapper.find("[data-description='grid cell 0-2']");
        const dropdownItems = dropdown.findAll(".dropdown-item");
        expect(nth(dropdownItems, 0).text()).toBe("operation-title-1");
        expect(nth(dropdownItems, 1).text()).toBe("operation-title-3");
        await nth(dropdownItems, 0).trigger("click");
        const clickHandler = testGrid.fields[2]!.operations![0]!.handler;
        expect(clickHandler).toHaveBeenCalledTimes(1);
        expect(vi.mocked(clickHandler).mock.calls[0]!.slice(0, 1)).toEqual([
            { id: "id-1", link: "link-1", operation: "operation-1" },
        ]);
        await nth(dropdownItems, 1).trigger("click");
        await flushPromises();
        const alert = wrapper.find(".alert");
        expect(alert.text()).toBe("Operation-3 has been executed.");
        await vi.runAllTimersAsync();
        await flushPromises();
        expect(wrapper.find(".alert").exists()).toBeFalsy();
    });

    it("filter handling", async () => {
        const testGrid = createTestGrid();
        const wrapper = createTarget({
            gridConfig: testGrid,
        });
        await wrapper.vm.$nextTick();
        const filterInput = wrapper.find("[data-description='filter text input']");
        await filterInput.setValue("filter query");
        vi.runAllTimers();
        await flushPromises();
        expect(vi.mocked(testGrid.getData)).toHaveBeenCalledTimes(2);
        expect(vi.mocked(testGrid.getData).mock.calls[1]!.slice(0, 5)).toEqual([0, 25, "filter query", "id", true]);
    });

    it("column filter handling", async () => {
        const testGrid = createTestGrid();
        testGrid.filtering = new Filtering({
            link: { type: "MultiTags", handler: equals("link", "link"), menuItem: false },
            name: { handler: equals("name", "name"), menuItem: false },
        });
        const search = vi.fn(async () => [
            { id: "link-1", name: "Link one" },
            { id: "link-2", name: "Link two" },
        ]);
        testGrid.fields[1]!.filter = { key: "link", clears: ["name"], plural: "links", search };
        const wrapper = createTarget({
            gridConfig: testGrid,
        });
        await flushPromises();
        const filterInput = () => wrapper.find("[data-description='filter text input']").element as HTMLInputElement;
        await wrapper.find("[data-description='filter text input']").setValue("name:foo");
        vi.runAllTimers();
        await flushPromises();
        await wrapper.find("[data-description='grid column filter link'] button").trigger("click");
        await flushPromises();
        expect(search).toHaveBeenCalledWith("");
        await wrapper.find("input[data-description='grid column filter option link-2']").setValue(true);
        await flushPromises();
        expect(filterInput().value).toBe("link:link-2");
        expect(vi.mocked(testGrid.getData).mock.calls.at(-1)!.slice(0, 5)).toEqual([0, 25, "link:link-2", "id", true]);
        await wrapper.find("input[data-description='grid column filter option link-1']").setValue(true);
        await flushPromises();
        expect(filterInput().value).toBe("link:link-2 link:link-1");
        const chips = wrapper.findAll("[data-description='grid active column filter link']");
        expect(chips.map((chip) => chip.text())).toEqual(["link: Link two", "link: Link one"]);
        await chips[0]!.trigger("click");
        await flushPromises();
        expect(filterInput().value).toBe("link:link-1");
        expect(wrapper.find("[data-description='grid column filter count']").text()).toBe("1");
    });

    it("keeps column filters available when a pick matches nothing", async () => {
        const testGrid = createTestGrid();
        testGrid.filtering = new Filtering({
            link: { type: "MultiTags", handler: equals("link", "link"), menuItem: false },
        });
        const search = vi.fn(async () => [{ id: "link-1", name: "Link one" }]);
        testGrid.fields[1]!.filter = { key: "link", plural: "links", search };
        const wrapper = createTarget({ gridConfig: testGrid });
        await flushPromises();
        await wrapper.find("[data-description='grid column filter link'] button").trigger("click");
        await flushPromises();
        vi.mocked(testGrid.getData).mockResolvedValue([[], 0]);
        await wrapper.find("input[data-description='grid column filter option link-1']").setValue(true);
        await flushPromises();

        expect(wrapper.text()).toContain("Nothing found with:");
        expect(wrapper.findAll("[data-description='grid item']")).toHaveLength(0);
        expect(wrapper.find("[data-description='grid column filter link']").exists()).toBe(true);
        expect(wrapper.find("[data-description='grid column filter search']").exists()).toBe(true);
    });

    it("hides the table when there is no data and no filter", async () => {
        const testGrid = createTestGrid();
        testGrid.filtering = new Filtering({
            link: { type: "MultiTags", handler: equals("link", "link"), menuItem: false },
        });
        testGrid.fields[1]!.filter = { key: "link", plural: "links", search: vi.fn(async () => []) };
        vi.mocked(testGrid.getData).mockResolvedValue([[], 0]);
        const wrapper = createTarget({ gridConfig: testGrid });
        await flushPromises();

        expect(wrapper.find(".grid-table").exists()).toBe(false);
        expect(wrapper.text()).toContain("No data available.");
    });

    it("ignores a response that arrives after a newer one", async () => {
        const testGrid = createTestGrid();
        testGrid.filtering = new Filtering({
            link: { type: "MultiTags", handler: equals("link", "link"), menuItem: false },
        });
        const wrapper = createTarget({ gridConfig: testGrid });
        await flushPromises();
        const slow = deferred<[RowData[], number]>();
        const fast = deferred<[RowData[], number]>();
        vi.mocked(testGrid.getData).mockReturnValueOnce(slow.promise).mockReturnValueOnce(fast.promise);
        await wrapper.find("[data-description='filter text input']").setValue("link:slow");
        vi.runAllTimers();
        await flushPromises();
        await wrapper.find("[data-description='filter text input']").setValue("link:fast");
        vi.runAllTimers();
        await flushPromises();

        fast.resolve([[{ id: "fast-row" }], 1]);
        await flushPromises();
        slow.resolve([[{ id: "slow-row" }], 1]);
        await flushPromises();

        expect(wrapper.find("[data-description='grid cell 0-0']").text()).toBe("fast-row");
    });

    it("pagination", async () => {
        const testGrid = createTestGrid();
        const wrapper = createTarget({
            gridConfig: testGrid,
            limit: 2,
        });
        await flushPromises();

        const pageLinks = wrapper.findAll(".page-link");
        await pageLinks[4]!.trigger("click");
        await flushPromises();
        expect(wrapper.find("[data-description='grid cell 0-0']").text()).toBe("id-5");
        expect(wrapper.find("[data-description='grid cell 1-0']").text()).toBe("id-6");
    });
});
