import Workflows from "../Workflow/WorkflowList";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { getLocalVue } from "jest/helpers";
import flushPromises from "flush-promises";
import { parseISO, formatDistanceToNow } from "date-fns";

const localVue = getLocalVue();

jest.mock("app");

const mockWorkflowsData = [
    {
        id: "5f1915bcf9f35612",
        update_time: "2021-01-04T17:40:58.604118",
        create_time: "2021-01-04T17:40:58.407793",
        name: "workflow name",
        tags: ["tagmoo", "tagcow"],
        published: true,
        show_in_tool_panel: true,
        owner: "test",
    },
];

describe("WorkflowList.vue", () => {
    let axiosMock;
    let wrapper;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    describe(" with empty workflow list", () => {
        beforeEach(async () => {
            axiosMock.onAny().reply(200, [], { total_matches: "0" });
            const propsData = {};
            wrapper = mount(Workflows, {
                propsData,
                localVue,
            });
        });

        it("no invocations message should be shown when not loading", async () => {
            expect(wrapper.find("#no-workflows").exists()).toBe(true);
        });
    });

    describe(" with server error", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/workflows", { params: { limit: 50, offset: 0, skip_step_counts: true, search: "" } })
                .reply(403, { err_msg: "this is a problem" });
            const propsData = {};
            wrapper = mount(Workflows, {
                propsData,
                localVue,
            });
            flushPromises();
        });

        it("renders error message", async () => {
            expect(wrapper.find(".index-grid-message").text()).toContain("this is a problem");
        });
    });

    describe(" with single workflow", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/workflows", { params: { limit: 50, offset: 0, skip_step_counts: true, search: "" } })
                .reply(200, mockWorkflowsData, { total_matches: "1" });
            const propsData = {
                inputDebounceDelay: 0,
            };
            wrapper = mount(Workflows, {
                propsData,
                localVue,
            });
            flushPromises();
        });

        it("no workflows message is gone", async () => {
            expect(wrapper.find("#no-workflows").exists()).toBe(false);
        });

        it("renders one row", async () => {
            const rows = wrapper.findAll("tbody > tr").wrappers;
            expect(rows.length).toBe(1);
            const row = rows[0];
            const columns = row.findAll("td");
            expect(columns.at(0).text()).toContain("workflow name");
            expect(columns.at(1).text()).toContain("tagmoo");
            expect(columns.at(1).text()).toContain("tagcow");
            expect(columns.at(2).text()).toBe(
                formatDistanceToNow(parseISO(`${mockWorkflowsData[0].update_time}Z`), { addSuffix: true })
            );
            expect(columns.at(2).text()).toBe(
                formatDistanceToNow(parseISO(`${mockWorkflowsData[0].update_time}Z`), { addSuffix: true })
            );
            expect(row.find(".fa-globe").exists()).toBe(true);
        });

        it("starts with an empty filter", async () => {
            expect(wrapper.find("#workflow-search").element.value).toBe("");
        });

        it("fetched filtered results when search filter is used", async () => {
            axiosMock
                .onGet("/api/workflows", { params: { limit: 50, offset: 0, skip_step_counts: true, search: "mytext" } })
                .reply(200, [], { total_matches: "0" });

            await wrapper.find("#workflow-search").setValue("mytext");
            flushPromises();
            expect(wrapper.find("#workflow-search").element.value).toBe("mytext");
            expect(wrapper.vm.filter).toBe("mytext");
        });

        it("update filter when a tag is clicked", async () => {
            axiosMock
                .onGet("/api/workflows", {
                    params: { limit: 50, offset: 0, skip_step_counts: true, search: "tag:'tagmoo'" },
                })
                .reply(200, mockWorkflowsData, { total_matches: "1" });

            const tags = wrapper.findAll("tbody > tr .tag-name").wrappers;
            expect(tags.length).toBe(2);
            tags[0].trigger("click");
            flushPromises();
            expect(wrapper.vm.filter).toBe("tag:'tagmoo'");
        });

        it("update filter when a tag is clicked only happens on first click", async () => {
            axiosMock
                .onGet("/api/workflows", {
                    params: { limit: 50, offset: 0, skip_step_counts: true, search: "tag:'tagmoo'" },
                })
                .reply(200, mockWorkflowsData, { total_matches: "1" });

            const tags = wrapper.findAll("tbody > tr .tag-name").wrappers;
            expect(tags.length).toBe(2);
            tags[0].trigger("click");
            tags[0].trigger("click");
            tags[0].trigger("click");
            flushPromises();
            expect(wrapper.vm.filter).toBe("tag:'tagmoo'");
        });

        it("update filter when published icon is clicked", async () => {
            axiosMock
                .onGet("/api/workflows", {
                    params: { limit: 50, offset: 0, skip_step_counts: true, search: "is:published" },
                })
                .reply(200, mockWorkflowsData, { total_matches: "1" });
            const rows = wrapper.findAll("tbody > tr").wrappers;
            const row = rows[0];
            row.find(".fa-globe").trigger("click");
            flushPromises();
            expect(wrapper.vm.filter).toBe("is:published");
        });

        it("update filter when shared with me icon is clicked", async () => {
            axiosMock
                .onGet("/api/workflows", {
                    params: { limit: 50, offset: 0, skip_step_counts: true, search: "is:shared_with_me" },
                })
                .reply(200, mockWorkflowsData, { total_matches: "1" });
            const rows = wrapper.findAll("tbody > tr").wrappers;
            const row = rows[0];
            row.find(".fa-share-alt").trigger("click");
            flushPromises();
            expect(wrapper.vm.filter).toBe("is:shared_with_me");
        });
    });
});
