import Invocations from "../Workflow/Invocations";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { getLocalVue } from "jest/helpers";
import mockInvocationData from "./test/json/invocation.json";
import moment from "moment";

const localVue = getLocalVue();

describe("Invocations.vue without invocation", () => {
    let axiosMock;
    let wrapper;
    let propsData;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onAny().reply(200, [], { total_matches: "0" });
        propsData = {
            ownerGrid: false,
        };
        wrapper = mount(Invocations, {
            propsData,
            localVue,
        });
    });

    afterEach(() => {
        axiosMock.reset();
    });

    it("title should be shown", async () => {
        expect(wrapper.find("#invocations-title").text()).toBe("Workflow Invocations");
    });

    it("no invocations message should be shown when not loading", async () => {
        expect(wrapper.find("#no-invocations").exists()).toBe(true);
    });
});

describe("Invocations.vue with invocation", () => {
    let wrapper;
    let propsData;
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock
            .onGet("/api/invocations", { params: { limit: 50, offset: 0, include_terminal: false } })
            .reply(200, [mockInvocationData], { total_matches: "1" });
        propsData = {
            ownerGrid: false,
            loading: false,
        };
        wrapper = mount(Invocations, {
            propsData,
            computed: {
                getWorkflowNameByInstanceId: (state) => (id) => "workflow name",
                getWorkflowByInstanceId: (state) => (id) => {
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

    afterEach(() => {
        axiosMock.reset();
    });

    it("renders one row", async () => {
        const rows = wrapper.findAll("tbody > tr").wrappers;
        expect(rows.length).toBe(1);
        const row = rows[0];
        const columns = row.findAll("td");
        expect(columns.at(1).text()).toBe("workflow name");
        expect(columns.at(2).text()).toBe("history name");
        expect(columns.at(3).text()).toBe(moment.utc(mockInvocationData.create_time).fromNow());
        expect(columns.at(4).text()).toBe(moment.utc(mockInvocationData.update_time).fromNow());
        expect(columns.at(5).text()).toBe("scheduled");
        expect(columns.at(6).text()).toBe("");
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

    it("calls switchHistory", async () => {
        const mockMethod = jest.fn();
        wrapper.vm.switchHistory = mockMethod;
        await wrapper.find("#switch-to-history").trigger("click");
        expect(mockMethod).toHaveBeenCalled();
    });

    it("calls executeWorkflow", async () => {
        const mockMethod = jest.fn();
        wrapper.vm.executeWorkflow = mockMethod;
        await wrapper.find("#run-workflow").trigger("click");
        expect(mockMethod).toHaveBeenCalledWith("workflowId");
    });
});
