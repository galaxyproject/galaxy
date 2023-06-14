import Workflows from "../Workflow/WorkflowList";
import { mount } from "@vue/test-utils";
import { useUserTags } from "composables/user";
import { computed } from "vue";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { getLocalVue } from "tests/jest/helpers";
import flushPromises from "flush-promises";
import { parseISO, formatDistanceToNow } from "date-fns";
import { PiniaVuePlugin } from "pinia";
import { createTestingPinia } from "@pinia/testing";
import Tag from "../TagsMultiselect/Tag";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

const autocompleteTags = ["#named_user_tags", "abc", "my_tag"];
jest.mock("composables/user");
useUserTags.mockReturnValue({
    userTags: computed(() => autocompleteTags),
    addLocalTag: jest.fn(),
});

jest.mock("app");

const sampleLongAnnotation =
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor\
    incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis\
    eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident,\
    sunt in culpa qui officia deserunt mollit anim id est laborum.";

const mockWorkflowsData = [
    {
        id: "5f1915bcf9f35612",
        update_time: "2021-01-04T17:40:58.604118",
        create_time: "2021-01-04T17:40:58.407793",
        name: "workflow name",
        tags: ["tagmoo", "tagcow"],
        annotations: [sampleLongAnnotation],
        published: true,
        show_in_tool_panel: true,
        owner: "test",
    },
];

const defaultApiParams = {
    limit: 20,
    offset: 0,
    skip_step_counts: true,
    sort_by: "update_time",
    sort_desc: true,
};

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
                pinia: createTestingPinia(),
            });
        });

        it("no invocations message should be shown when not loading", async () => {
            expect(wrapper.find("#no-workflows").exists()).toBe(true);
        });
    });

    describe(" with server error", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/workflows", { params: { search: "", ...defaultApiParams } })
                .reply(403, { err_msg: "this is a problem" });
            const propsData = {};
            wrapper = mount(Workflows, {
                propsData,
                localVue,
                pinia: createTestingPinia(),
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
                .onGet("/api/workflows", { params: { search: "", ...defaultApiParams } })
                .reply(200, mockWorkflowsData, { total_matches: "1" });
            const propsData = {
                inputDebounceDelay: 0,
            };
            wrapper = mount(Workflows, {
                propsData,
                localVue,
                pinia: createTestingPinia(),
            });
            flushPromises();
        });

        it("no workflows message is gone", async () => {
            expect(wrapper.find("#no-workflows").exists()).toBe(false);
        });

        it("renders one row", async () => {
            let rows = wrapper.findAll("tbody > tr").wrappers;
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
            expect(row.find(".sharing-indicator-published").exists()).toBe(true);

            // test expand summary button for longer annotations
            const annotationHead = sampleLongAnnotation.substr(0, 75);
            const annotationTail = sampleLongAnnotation.substr(sampleLongAnnotation.length - 50);
            expect(columns.at(0).text()).toContain(annotationHead);
            expect(columns.at(0).text()).not.toContain(annotationTail);
            expect(columns.at(0).find("a > .fa-chevron-down").exists()).toBe(true);
            // click Down Arrow: full annotation should be visible in a b-card
            await columns.at(0).find("a.text-summary-expand").trigger("click");
            expect(columns.at(0).find("a > .fa-chevron-down").exists()).toBe(false);
            rows = wrapper.findAll("tbody > tr").wrappers;
            expect(rows.length).toBe(3);
            const descriptionCard = rows[2].find("td");
            expect(descriptionCard.text()).toContain(annotationTail);
            expect(columns.at(0).find("a > .fa-chevron-up").exists()).toBe(true);
        });

        it("starts with an empty filter", async () => {
            expect(wrapper.find("#workflow-search").element.value).toBe("");
        });

        it("fetched filtered results when search filter is used", async () => {
            await wrapper.find("#workflow-search").setValue("mytext");
            flushPromises();
            expect(wrapper.find("#workflow-search").element.value).toBe("mytext");
            expect(wrapper.vm.filter).toBe("mytext");
        });

        it("update filter when a tag is clicked", async () => {
            const tags = wrapper.findAllComponents(Tag).wrappers;
            expect(tags.length).toBe(2);
            tags[0].trigger("click");
            flushPromises();
            expect(wrapper.vm.filter).toBe("tag:'tagmoo'");
        });

        it("update filter when a tag is clicked only happens on first click", async () => {
            const tags = wrapper.findAllComponents(Tag).wrappers;
            expect(tags.length).toBe(2);
            tags[0].trigger("click");
            tags[0].trigger("click");
            tags[0].trigger("click");
            flushPromises();
            expect(wrapper.vm.filter).toBe("tag:'tagmoo'");
        });

        it("update filter when published icon is clicked", async () => {
            const rows = wrapper.findAll("tbody > tr").wrappers;
            const row = rows[0];
            row.find(".sharing-indicator-published").trigger("click");
            flushPromises();
            expect(wrapper.vm.filter).toBe("is:published");
        });

        it("update filter when shared with me icon is clicked", async () => {
            const rows = wrapper.findAll("tbody > tr").wrappers;
            const row = rows[0];
            row.find(".fa-share-alt").trigger("click");
            flushPromises();
            expect(wrapper.vm.filter).toBe("is:shared_with_me");
        });
    });

    describe("published grid", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/workflows", {
                    params: {
                        search: "is:published",
                        show_published: true,
                        show_shared: false,
                        ...defaultApiParams,
                    },
                })
                .reply(200, mockWorkflowsData, { total_matches: "1" });
            const propsData = {
                inputDebounceDelay: 0,
                published: true,
            };
            wrapper = mount(Workflows, {
                propsData,
                localVue,
                pinia: createTestingPinia(),
            });
            flushPromises();
        });

        it("should be error free", async () => {
            const errorDiv = wrapper.find(".index-grid-message");
            expect(errorDiv.text()).toBeFalsy();
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
        });
    });
});
