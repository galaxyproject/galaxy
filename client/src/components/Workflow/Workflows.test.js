import Workflows from "../Workflow/WorkflowList";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { getLocalVue } from "jest/helpers";
import flushPromises from "flush-promises";
import { parseISO, formatDistanceToNow } from "date-fns";

const localVue = getLocalVue();

const mockWorkflowsData = [
    {
        id: "5f1915bcf9f35612",
        update_time: "2021-01-04T17:40:58.604118",
        create_time: "2021-01-04T17:40:58.407793",
        name: "workflow name",
        tags: ["tagmoo", "tagcow"],
        published: true,
        shared: true,
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

    describe(" with single workflow", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/workflows", { params: { limit: 50, offset: 0, skip_step_counts: true, search: "" } })
                .reply(200, mockWorkflowsData, { total_matches: "1" });
            const propsData = {};
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

            wrapper.find("#workflow-search").setValue("mytext");
            flushPromises();
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
    });
});
