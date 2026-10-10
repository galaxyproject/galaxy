import { faCog, faCopy, faFilter, faFolder } from "@fortawesome/free-solid-svg-icons";
import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { GalaxyConfiguration } from "@/stores/configurationStore";
import Filtering from "@/utils/filtering";

import type { GridConfig, RowData } from "./configs/types";

import GridList from "./GridList.vue";

vi.useFakeTimers();

setupMockConfig({ disabled: false, enabled: true });

const SELECTORS = {
    FILTER_INPUT: "[data-description='filter text input']",
    INITIAL_LOADING: "[data-description='grid initial loading']",
    TEST_ACTION: "[data-description='grid action test']",
    TITLE: "[data-description='grid title']",
    SORT_DESC: "[data-description='grid sort desc']",
    SORT_ASC: "[data-description='grid sort asc']",
    DROPDOWN_ITEM: ".dropdown-item",
    ALERT: ".alert",
    PAGE_LINK: ".page-link",
};

const FIRST_PAGE_REQUEST = { offset: 0, limit: 25, search: "", sortBy: "id", sortDesc: true };

function createTestGrid(): GridConfig {
    return {
        id: "test-grid",
        actions: [
            {
                title: "test",
                icon: faCopy,
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
                        icon: faCog,
                        condition: (_: RowData, config: GalaxyConfiguration) => config.value.enabled,
                        handler: vi.fn(),
                    },
                    {
                        title: "operation-title-2",
                        icon: faFilter,
                        condition: (_: RowData, config: GalaxyConfiguration) => config.value.disabled,
                        handler: vi.fn(),
                    },
                    {
                        title: "operation-title-3",
                        icon: faFolder,
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

function mountGridList(gridConfig: GridConfig, limit?: number) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    return mount(GridList as object, {
        global: withPlugins(getLocalVue(), pinia),
        props: { gridConfig, limit },
    });
}

async function mountLoadedGridList(gridConfig: GridConfig, limit?: number) {
    const wrapper = mountGridList(gridConfig, limit);
    await flushPromises();
    return wrapper;
}

/** Each `getData` request so far, without the trailing `extraProps` */
function dataRequests(gridConfig: GridConfig) {
    return vi.mocked(gridConfig.getData).mock.calls.map(([offset, limit, search, sortBy, sortDesc]) => ({
        offset,
        limit,
        search,
        sortBy,
        sortDesc,
    }));
}

function cell(wrapper: VueWrapper, row: number, column: number) {
    return wrapper.find(`[data-description='grid cell ${row}-${column}']`);
}

function header(wrapper: VueWrapper, column: number) {
    return wrapper.find(`[data-description='grid header ${column}']`);
}

enableAutoUnmount(afterEach);

describe("GridList", () => {
    it("shows the initial loading state while the first page is requested", async () => {
        const testGrid = createTestGrid();
        const wrapper = mountGridList(testGrid);

        expect(wrapper.find(SELECTORS.INITIAL_LOADING).exists()).toBe(true);
        expect(dataRequests(testGrid)).toEqual([FIRST_PAGE_REQUEST]);

        await flushPromises();

        expect(wrapper.find(SELECTORS.INITIAL_LOADING).exists()).toBe(false);
    });

    it("renders the title, the filter placeholder and a working action", async () => {
        const testGrid = createTestGrid();
        const wrapper = await mountLoadedGridList(testGrid);

        expect(wrapper.find(SELECTORS.TITLE).text()).toBe("Test");
        expect(wrapper.find(SELECTORS.FILTER_INPUT).attributes("placeholder")).toBe("search tests");

        const action = wrapper.find(SELECTORS.TEST_ACTION);
        expect(action.text()).toBe("test");
        expect(action.find("svg").exists()).toBe(true);
        await action.trigger("click");
        expect(testGrid.actions![0]!.handler).toHaveBeenCalledTimes(1);
        expect(dataRequests(testGrid)).toEqual([FIRST_PAGE_REQUEST]);
    });

    it("renders the text and link cells of the first page", async () => {
        const wrapper = await mountLoadedGridList(createTestGrid());

        expect(cell(wrapper, 0, 0).text()).toBe("id-1");
        expect(cell(wrapper, 1, 0).text()).toBe("id-2");
        expect(cell(wrapper, 0, 1).find("button").text()).toBe("link-1");
        expect(cell(wrapper, 1, 1).find("button").text()).toBe("link-2");
    });

    it("titles each column header after its field", async () => {
        const testGrid = createTestGrid();
        const wrapper = await mountLoadedGridList(testGrid);

        testGrid.fields.forEach((field, column) => {
            expect(header(wrapper, column).text()).toBe(field.title);
        });
    });

    it("reverses the sort order when the sorted column's header is clicked", async () => {
        const testGrid = createTestGrid();
        const wrapper = await mountLoadedGridList(testGrid);
        const sortedHeader = header(wrapper, 0);
        expect(sortedHeader.find("button").text()).toBe("id");
        expect(sortedHeader.find(SELECTORS.SORT_DESC).exists()).toBe(true);

        await sortedHeader.find("button").trigger("click");
        await flushPromises();

        expect(dataRequests(testGrid)).toEqual([FIRST_PAGE_REQUEST, { ...FIRST_PAGE_REQUEST, sortDesc: false }]);
        expect(sortedHeader.find(SELECTORS.SORT_DESC).exists()).toBe(false);
        expect(sortedHeader.find(SELECTORS.SORT_ASC).exists()).toBe(true);
        expect(header(wrapper, 1).find(SELECTORS.SORT_DESC).exists()).toBe(false);
        expect(header(wrapper, 1).find(SELECTORS.SORT_ASC).exists()).toBe(false);
    });

    it("lists only the operations whose condition holds for the configuration", async () => {
        const wrapper = await mountLoadedGridList(createTestGrid());

        const operations = cell(wrapper, 0, 2).findAll(SELECTORS.DROPDOWN_ITEM);
        expect(operations.map((operation) => operation.text())).toEqual(["operation-title-1", "operation-title-3"]);
    });

    it("runs an operation's handler with its row", async () => {
        const testGrid = createTestGrid();
        const wrapper = await mountLoadedGridList(testGrid);

        await cell(wrapper, 0, 2).findAll(SELECTORS.DROPDOWN_ITEM)[0]!.trigger("click");

        const handler = testGrid.fields[2]!.operations![0]!.handler;
        expect(handler).toHaveBeenCalledExactlyOnceWith({ id: "id-1", link: "link-1", operation: "operation-1" });
    });

    it("shows an operation's result message until it times out", async () => {
        const wrapper = await mountLoadedGridList(createTestGrid());

        await cell(wrapper, 0, 2).findAll(SELECTORS.DROPDOWN_ITEM)[1]!.trigger("click");
        await flushPromises();
        expect(wrapper.find(SELECTORS.ALERT).text()).toBe("Operation-3 has been executed.");

        await vi.runAllTimersAsync();
        await flushPromises();
        expect(wrapper.find(SELECTORS.ALERT).exists()).toBe(false);
    });

    it("requests matching rows once the filter text settles", async () => {
        const testGrid = createTestGrid();
        const wrapper = await mountLoadedGridList(testGrid);

        await wrapper.find(SELECTORS.FILTER_INPUT).setValue("filter query");
        vi.runAllTimers();
        await flushPromises();

        expect(dataRequests(testGrid)).toEqual([FIRST_PAGE_REQUEST, { ...FIRST_PAGE_REQUEST, search: "filter query" }]);
    });

    it("shows the rows of the page picked in the pager", async () => {
        const testGrid = createTestGrid();
        const wrapper = await mountLoadedGridList(testGrid, 2);

        const thirdPage = wrapper.findAll(SELECTORS.PAGE_LINK).find((link) => link.text() === "3");
        await thirdPage!.trigger("click");
        await flushPromises();

        expect(dataRequests(testGrid).at(-1)).toEqual({ ...FIRST_PAGE_REQUEST, offset: 4, limit: 2 });
        expect(cell(wrapper, 0, 0).text()).toBe("id-5");
        expect(cell(wrapper, 1, 0).text()).toBe("id-6");
    });
});
