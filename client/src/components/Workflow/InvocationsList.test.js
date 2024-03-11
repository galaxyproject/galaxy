import "jest-location-mock";

import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { formatDistanceToNow, parseISO } from "date-fns";
import { getLocalVue } from "tests/jest/helpers";

import InvocationsList from "./InvocationsList";
import mockInvocationData from "./test/json/invocation.json";

const localVue = getLocalVue();

const pinia = createTestingPinia();
describe("InvocationsList.vue", () => {
    let axiosMock;
    let wrapper;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(`api/invocations/${mockInvocationData.id}`).reply(200, mockInvocationData);
        axiosMock.onGet(`api/invocations/${mockInvocationData.id}/jobs_summary`).reply(200, {});
    });

    afterEach(() => {
        axiosMock.restore();
    });

    describe(" with empty invocation list", () => {
        beforeEach(async () => {
            axiosMock.onAny().reply(200, [], { total_matches: "0" });
            const propsData = {
                ownerGrid: false,
            };
            wrapper = mount(InvocationsList, {
                propsData,
                localVue,
            });
        });

        it("title should be shown", async () => {
            expect(wrapper.find("#invocations-title").text()).toBe("Workflow Invocations");
        });

        it("no invocations message should be shown when not loading", async () => {
            expect(wrapper.find("#no-invocations").exists()).toBe(true);
        });
    });

    describe("with server error", () => {
        beforeEach(async () => {
            axiosMock.onAny().reply(403, { err_msg: "this is a problem" });
            const propsData = {
                ownerGrid: false,
            };
            wrapper = mount(InvocationsList, {
                propsData,
                localVue,
                pinia,
            });
        });

        it("renders error message", async () => {
            expect(wrapper.find(".index-grid-message").text()).toContain("this is a problem");
        });
    });

    describe("for a workflow with an empty invocation list", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/invocations", {
                    params: { limit: 50, offset: 0, include_terminal: false, workflow_id: "abcde145678" },
                })
                .reply(200, [], { total_matches: "0" });
            const propsData = {
                ownerGrid: false,
                storedWorkflowName: "My Workflow",
                storedWorkflowId: "abcde145678",
            };
            wrapper = mount(InvocationsList, {
                propsData,
                localVue,
                pinia,
            });
        });

        it("title should be shown", async () => {
            expect(wrapper.find("#invocations-title").text()).toBe('Workflow Invocations for workflow "My Workflow"');
        });

        it("no invocations message should be shown when not loading", async () => {
            expect(wrapper.find("#no-invocations").exists()).toBe(true);
        });

        it("should not render pager", async () => {
            expect(wrapper.find(".gx-invocations-grid-pager").exists()).toBeFalsy();
        });
    });

    describe("for a history with an empty invocation list", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/invocations", {
                    params: { limit: 50, offset: 0, include_terminal: false, history_id: "abcde145678" },
                })
                .reply(200, [], { total_matches: "0" });
            const propsData = {
                ownerGrid: false,
                historyName: "My History",
                historyId: "abcde145678",
            };
            wrapper = mount(InvocationsList, {
                propsData,
                localVue,
            });
        });

        it("title should be shown", async () => {
            expect(wrapper.find("#invocations-title").text()).toBe('Workflow Invocations for history "My History"');
        });

        it("no invocations message should be shown when not loading", async () => {
            expect(wrapper.find("#no-invocations").exists()).toBe(true);
        });

        it("should not render pager", async () => {
            expect(wrapper.find(".gx-invocations-grid-pager").exists()).toBeFalsy();
        });
    });

    describe("with invocation", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/invocations", { params: { limit: 50, offset: 0, include_terminal: false } })
                .reply(200, [mockInvocationData], { total_matches: "1" });
            const propsData = {
                ownerGrid: false,
                loading: false,
            };
            wrapper = mount(InvocationsList, {
                propsData,
                computed: {
                    getStoredWorkflowNameByInstanceId: (state) => (id) => "workflow name",
                    getStoredWorkflowIdByInstanceId: (state) => (id) => {
                        return "workflowId";
                    },
                    getStoredWorkflowByInstanceId: (state) => (id) => {
                        return { id: "workflowId" };
                    },
                    getHistoryById: (state) => (id) => {
                        return { id: "historyId" };
                    },
                    getHistoryNameById: () => () => "history name",
                },
                stubs: {
                    "workflow-invocation-state": {
                        template: "<span/>",
                    },
                },
                localVue,
                pinia,
            });
        });

        it("renders one row", async () => {
            const rows = wrapper.findAll("tbody > tr").wrappers;
            expect(rows.length).toBe(1);
            const row = rows[0];
            const columns = row.findAll("td");
            expect(columns.at(1).text()).toBe("workflow name");
            expect(columns.at(2).text()).toBe("Loading..."); // Checking the actual name will be tested in its own component
            expect(columns.at(3).text()).toBe(
                formatDistanceToNow(parseISO(`${mockInvocationData.create_time}Z`), { addSuffix: true })
            );
            expect(columns.at(4).text()).toBe("scheduled");
            expect(columns.at(5).text()).toBe("");
        });

        it("toggles detail rendering", async () => {
            let rows = wrapper.findAll("tbody > tr").wrappers;
            expect(rows.length).toBe(1);
            await wrapper.find(".toggle-invocation-details").trigger("click");
            rows = wrapper.findAll("tbody > tr").wrappers;
            expect(rows.length).toBe(3);
            await wrapper.find(".toggle-invocation-details").trigger("click");
            rows = wrapper.findAll("tbody > tr").wrappers;
            expect(rows.length).toBe(1);
        });

        it("check run button", async () => {
            const runButton = await wrapper.find('[data-workflow-run="workflowId"');

            expect(runButton.attributes("href")).toBe("/workflows/run?id=workflowId");
        });

        it("should not render pager", async () => {
            expect(wrapper.find(".gx-invocations-grid-pager").exists()).toBeFalsy();
        });
    });

    describe("paginations", () => {
        beforeEach(async () => {
            axiosMock
                .onGet("/api/invocations", { params: { limit: 1, offset: 0, include_terminal: false } })
                .reply(200, [mockInvocationData], { total_matches: "3" });
            const propsData = {
                ownerGrid: false,
                loading: false,
                defaultPerPage: 1,
            };
            wrapper = mount(InvocationsList, {
                propsData,
                computed: {
                    getStoredWorkflowNameByInstanceId: (state) => (id) => "workflow name",
                    getStoredWorkflowByInstanceId: (state) => (id) => {
                        return { id: "workflowId" };
                    },
                    getHistoryById: (state) => (id) => {
                        return { id: "historyId" };
                    },
                    getHistoryNameById: () => () => "history name",
                },
                stubs: {
                    "workflow-invocation-state": {
                        template: "<span/>",
                    },
                },
                localVue,
            });
        });

        it("title should render pager", async () => {
            expect(wrapper.find(".gx-invocations-grid-pager").exists()).toBeTruthy();
        });
    });
});
