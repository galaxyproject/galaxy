import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { formatDistanceToNow, parseISO } from "date-fns";
import flushPromises from "flush-promises";
import { PiniaVuePlugin } from "pinia";
import { useUserStore } from "stores/userStore";
import { getLocalVue, wait } from "tests/jest/helpers";

import PageList from "./PageList.vue";

jest.mock("app");

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

const debounceDelay = 500; // in ms - see FilterMenu.props.debounceDelay

describe("PgeList.vue", () => {
    let axiosMock;
    let wrapper;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    const personalGridApiParams = {
        limit: 20,
        offset: 0,
        sort_by: "update_time",
        sort_desc: true,
        show_published: false,
        show_shared: true,
    };
    const publishedGridApiParams = {
        ...personalGridApiParams,
        show_published: true,
        search: "is:published",
        show_shared: false,
    };
    const publishedGridApiParamsSortTitleAsc = {
        sort_by: "title",
        limit: 20,
        offset: 0,
        search: "is:published",
        show_published: true,
        show_shared: false,
    };
    const publishedGridApiParamsSortTitleDesc = {
        ...publishedGridApiParamsSortTitleAsc,
        sort_desc: true,
    };

    const propsDataPersonalGrid = {
        inputDebounceDelay: 0,
        published: false,
    };
    const propsDataPublishedGrid = {
        ...propsDataPersonalGrid,
        published: true,
    };

    const privatePage = {
        id: "5f1915bcf9f3561a",
        update_time: "2023-05-23T17:51:51.069761",
        create_time: "2023-01-04T17:40:58.407793",
        deleted: false,
        importable: false,
        published: false,
        slug: "raynor-here",
        tags: ["tagThis", "tagIs", "tagJimmy"],
        title: "jimmy's page",
        username: "jimmyPage",
    };
    const publishedPage = {
        ...privatePage,
        id: "5f1915bcf9f3561b",
        published: true,
        importable: true,
        update_time: "2023-05-25T17:51:51.069761",
    };
    const pageA = {
        id: "5f1915bcf9f3561c",
        update_time: "2023-05-21T17:51:51.069761",
        create_time: "2023-01-04T17:40:58.407793",
        deleted: false,
        importable: true,
        published: true,
        slug: "a-page",
        title: "a page title",
        username: "APageUser",
    };
    const mockPrivatePageData = [privatePage];
    const mockPublishedPageData = [publishedPage];
    const mockTwoPageData = [privatePage, pageA];

    function mountGrid(propsData) {
        const pinia = createTestingPinia();
        const userStore = useUserStore();
        userStore.currentUser = { username: "jimmyPage", tags_used: [] };

        wrapper = mount(PageList, {
            propsData,
            localVue,
            pinia,
            stubs: {
                icon: { template: "<div></div>" },
            },
        });
    }

    function mountPersonalGrid() {
        mountGrid(propsDataPersonalGrid);
    }

    function mountPublishedGrid() {
        mountGrid(propsDataPublishedGrid);
    }

    describe(" with empty page list", () => {
        beforeEach(async () => {
            axiosMock.onAny().reply(200, [], { total_matches: "0" });
            mountPersonalGrid();
        });

        it("title should be shown", async () => {
            expect(wrapper.find("#pages-title").text()).toBe("Pages");
        });

        it("no invocations message should be shown when not loading", async () => {
            expect(wrapper.find("#no-pages").exists()).toBe(true);
        });
    });
    describe("with server error", () => {
        beforeEach(async () => {
            axiosMock.onAny().reply(403, { err_msg: "this is a problem" });
            mountPersonalGrid();
        });

        it("renders error message", async () => {
            expect(wrapper.find(".index-grid-message").text()).toContain("this is a problem");
        });
    });

    describe("with single private page", () => {
        function findSearchBar(wrapper) {
            return wrapper.find("[data-description='filter text input']");
        }

        beforeEach(async () => {
            axiosMock
                .onGet("/api/pages", { params: { search: "", ...personalGridApiParams } })
                .reply(200, mockPrivatePageData, { total_matches: "1" });
            jest.spyOn(PageList.methods, "decorateData").mockImplementation((page) => {
                page.shared = false;
            });
            mountPersonalGrid();
            await flushPromises();
        });

        it("'no pages' message is gone", async () => {
            expect(wrapper.find("#no-pages").exists()).toBe(false);
        });

        it("renders one row with correct sharing options", async () => {
            const rows = wrapper.findAll("tbody > tr").wrappers;
            expect(rows.length).toBe(1);
            const row = rows[0];
            const columns = row.findAll("td");
            expect(columns.at(0).text()).toContain("jimmy's page");
            expect(columns.at(1).text()).toContain("tagThis");
            expect(columns.at(1).text()).toContain("tagIs");
            expect(columns.at(1).text()).toContain("tagJimmy");
            expect(columns.at(3).text()).toBe(
                formatDistanceToNow(parseISO(`${mockPrivatePageData[0].update_time}Z`), { addSuffix: true })
            );
            expect(row.find(".share-this-page").exists()).toBe(true);
            expect(row.find(".sharing-indicator-published").exists()).toBe(false);
            expect(row.find(".sharing-indicator-importable").exists()).toBe(false);
            expect(row.find(".sharing-indicator-shared").exists()).toBe(false);
        });

        it("starts with an empty filter", async () => {
            expect(findSearchBar(wrapper).element.value).toBe("");
        });

        it("fetches filtered results when search filter is used", async () => {
            await findSearchBar(wrapper).setValue("mytext");
            expect(findSearchBar(wrapper).element.value).toBe("mytext");
            await wait(debounceDelay);
            expect(wrapper.vm.filterText).toBe("mytext");
        });

        it("updates filter when a tag is clicked", async () => {
            const tags = wrapper.findAll("tbody > tr .tag").wrappers;
            expect(tags.length).toBe(3);
            tags[0].trigger("click");
            await flushPromises();
            expect(wrapper.vm.filterText).toBe("tag:'tagThis'");
        });

        it("updates filter when a tag is clicked only on the first click", async () => {
            const tags = wrapper.findAll("tbody > tr .tag").wrappers;
            expect(tags.length).toBe(3);
            tags[0].trigger("click");
            tags[0].trigger("click");
            tags[0].trigger("click");
            await flushPromises();
            expect(wrapper.vm.filterText).toBe("tag:'tagThis'");
        });
    });
    describe("with single published and importable page on personal grid", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/pages", { params: { search: "", ...personalGridApiParams } })
                .reply(200, mockPublishedPageData, { total_matches: "1" });
            jest.spyOn(PageList.methods, "decorateData").mockImplementation((page) => {
                page.shared = true;
            });
            mountPersonalGrid();
            await flushPromises();
        });
        it("updates filter when published icon is clicked", async () => {
            const rows = wrapper.findAll("tbody > tr").wrappers;
            const row = rows[0];
            row.find(".sharing-indicator-published").trigger("click");
            await flushPromises();
            expect(wrapper.vm.filterText).toBe("is:published");
        });

        it("updates filter when shared with me icon is clicked", async () => {
            const rows = wrapper.findAll("tbody > tr").wrappers;
            const row = rows[0];
            row.find(".sharing-indicator-shared").trigger("click");
            await flushPromises();
            expect(wrapper.vm.filterText).toBe("is:shared_with_me");
        });

        it("updates filter when importable icon is clicked", async () => {
            const rows = wrapper.findAll("tbody > tr").wrappers;
            const row = rows[0];
            row.find(".sharing-indicator-importable").trigger("click");
            await flushPromises();
            expect(wrapper.vm.filterText).toBe("is:importable");
        });
    });
    describe("with single page on published grid", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/pages", { params: publishedGridApiParams })
                .reply(200, mockPublishedPageData, { total_matches: "1" });
            jest.spyOn(PageList.methods, "decorateData").mockImplementation((page) => {
                page.shared = false;
            });
            mountPublishedGrid();
            await flushPromises();
        });

        it("renders one row with correct sharing options", async () => {
            const rows = wrapper.findAll("tbody > tr").wrappers;
            expect(rows.length).toBe(1);
            const row = rows[0];
            const columns = row.findAll("td");
            expect(columns.at(0).text()).toContain("jimmy's page");
            expect(columns.at(1).text()).toContain("tagThis");
            expect(columns.at(1).text()).toContain("tagIs");
            expect(columns.at(1).text()).toContain("tagJimmy");
            expect(columns.at(2).text()).toBe("jimmyPage");
            expect(columns.at(3).text()).toBe(
                formatDistanceToNow(parseISO(`${mockPublishedPageData[0].update_time}Z`), { addSuffix: true })
            );
            expect(row.find(".share-this-page").exists()).toBe(false);
            expect(row.find(".sharing-indicator-published").exists()).toBe(false);
            expect(row.find(".sharing-indicator-importable").exists()).toBe(false);
            expect(row.find(".sharing-indicator-shared").exists()).toBe(false);
        });
    });
    describe("with two pages on published grid", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/pages", { params: publishedGridApiParams })
                .reply(200, mockTwoPageData, { total_matches: "2" });
            axiosMock
                .onGet("/api/pages", { params: publishedGridApiParamsSortTitleAsc })
                .reply(200, [pageA, privatePage], { total_matches: "2" });
            axiosMock
                .onGet("/api/pages", { params: publishedGridApiParamsSortTitleDesc })
                .reply(200, mockTwoPageData, { total_matches: "2" });
            jest.spyOn(PageList.methods, "decorateData").mockImplementation((page) => {
                page.shared = false;
            });
            mountPublishedGrid();
            await flushPromises();
        });

        it("should render both rows", async () => {
            const rows = wrapper.findAll("tbody > tr").wrappers;
            expect(rows.length).toBe(2);
        });

        it("should sort asc/desc when title column is clicked", async () => {
            let firstRowColumns = wrapper.findAll("tbody > tr").wrappers[0].findAll("td");
            expect(firstRowColumns.at(0).text()).toContain("jimmy's page");
            const titleColumn = wrapper.findAll("th").wrappers[0];
            // default sort is by update_time
            expect(titleColumn.attributes("aria-sort")).toBe("none");
            await titleColumn.trigger("click");
            await flushPromises();
            expect(titleColumn.attributes("aria-sort")).toBe("ascending");
            firstRowColumns = wrapper.findAll("tbody > tr").wrappers[0].findAll("td");
            expect(firstRowColumns.at(0).text()).toContain("a page title");
            await titleColumn.trigger("click");
            await flushPromises();
            expect(titleColumn.attributes("aria-sort")).toBe("descending");
            firstRowColumns = wrapper.findAll("tbody > tr").wrappers[0].findAll("td");
            expect(firstRowColumns.at(0).text()).toContain("jimmy's page");
        });
    });
});
