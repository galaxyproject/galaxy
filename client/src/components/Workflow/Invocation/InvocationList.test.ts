import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StoredWorkflowDetailed } from "@/api/workflows";
import type * as InvocationFilters from "@/components/Grid/configs/invocationFilters";
import { getData } from "@/components/Grid/configs/invocations";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import InvocationList from "./InvocationList.vue";

vi.useFakeTimers();

vi.mock("vue-router");

vi.mock("@/components/Grid/configs/invocations", () => ({
    getData: vi.fn(),
}));

vi.mock("@/components/Grid/configs/invocationFilters", async (importOriginal) => {
    const original = await importOriginal<typeof InvocationFilters>();
    const search = async () => [
        { id: "workflow-1", name: "Workflow one" },
        { id: "workflow-2", name: "Workflow two" },
    ];
    return {
        ...original,
        workflowColumnFilter: { ...original.workflowColumnFilter, search },
        historyColumnFilter: { ...original.historyColumnFilter, search: async () => [] },
    };
});

const USER = getFakeRegisteredUser();

type InvocationsPage = Awaited<ReturnType<typeof getData>>;

const INVOCATIONS = [
    {
        id: "inv-1",
        workflow_id: "instance-1",
        history_id: "history-1",
        state: "scheduled",
        create_time: "",
        update_time: "",
    },
    {
        id: "inv-2",
        workflow_id: "instance-2",
        history_id: "history-1",
        state: "completed",
        create_time: "",
        update_time: "",
    },
];

function mountTarget() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    useUserStore(pinia).currentUser = USER;
    useWorkflowStore(pinia).workflowsByInstanceId = {
        "instance-1": { name: "Name of instance-1" } as StoredWorkflowDetailed,
        "instance-2": { name: "Name of instance-2" } as StoredWorkflowDetailed,
    };
    return mount(InvocationList as object, {
        global: {
            ...getLocalVue(),
            plugins: [pinia],
            stubs: {
                WorkflowInvocationState: { template: "<div data-description='invocation state stub' />" },
                SwitchToHistoryLink: true,
                HelpText: true,
                UtcDate: true,
            },
        },
    });
}

const lastQuery = () => vi.mocked(getData).mock.calls.at(-1)!.slice(0, 6);
const filterInput = (wrapper: ReturnType<typeof mountTarget>) =>
    wrapper.find("[data-description='filter text input']").element as HTMLInputElement;
const rows = (wrapper: ReturnType<typeof mountTarget>) => wrapper.findAll("tbody tr[id^='g-table-row-']");

describe("InvocationList", () => {
    beforeEach(() => {
        vi.mocked(getData).mockReset();
        vi.mocked(getData).mockResolvedValue([INVOCATIONS, 2] as unknown as InvocationsPage);
    });

    it("lists the user's invocations, newest first", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        expect(lastQuery()).toEqual([0, 25, "", "create_time", true, { user_id: USER.id }]);
        expect(rows(wrapper)).toHaveLength(2);
        expect(wrapper.text()).toContain("Name of instance-1");
    });

    it("sends the filter text as the search", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        await wrapper.find("[data-description='filter text input']").setValue("workflow:rna");
        vi.runAllTimers();
        await flushPromises();

        expect(lastQuery()[2]).toBe("workflow:rna");
    });

    it("sorts by invocation time when the Invoked header is clicked", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        await wrapper.find("th.g-table-sortable").trigger("click");
        await flushPromises();

        expect(lastQuery().slice(3, 5)).toEqual(["create_time", false]);
    });

    it("picks workflows from the column filter and removes them with their chips", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        await wrapper.find("[data-description='grid column filter workflow_id'] button").trigger("click");
        await flushPromises();
        await wrapper.find("input[data-description='grid column filter option workflow-2']").setValue(true);
        await flushPromises();

        expect(filterInput(wrapper).value).toBe("workflow_id:workflow-2");
        expect(lastQuery()[2]).toBe("workflow_id:workflow-2");
        const chips = wrapper.findAll("[data-description='grid active column filter workflow_id']");
        expect(chips.map((chip) => chip.text())).toEqual(["Workflow: Workflow two"]);

        await chips[0]!.trigger("click");
        await flushPromises();
        expect(filterInput(wrapper).value).toBe("");
    });

    it("keeps the column filters available when the filters match nothing", async () => {
        const wrapper = mountTarget();
        await flushPromises();
        vi.mocked(getData).mockResolvedValue([[], 0] as InvocationsPage);

        await wrapper.find("[data-description='filter text input']").setValue("workflow:no-such-workflow");
        vi.runAllTimers();
        await flushPromises();

        expect(wrapper.text()).toContain("Nothing found with:");
        expect(rows(wrapper)).toHaveLength(0);
        expect(wrapper.find("[data-description='grid column filter workflow_id']").exists()).toBe(true);
        expect(wrapper.find("[data-description='grid column filter history_id']").exists()).toBe(true);
    });

    it("shows the invocation's state when a row is expanded", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        await wrapper.findAll("[data-description='toggle row details']")[1]!.trigger("click");
        await flushPromises();

        const details = wrapper.find("[data-description='grid expanded row']");
        expect(details.find("[data-invocation-id='inv-2']").exists()).toBe(true);
        expect(details.find("[data-description='invocation state stub']").exists()).toBe(true);
    });

    it("collapses expanded rows when new rows load", async () => {
        const wrapper = mountTarget();
        await flushPromises();
        await wrapper.findAll("[data-description='toggle row details']")[0]!.trigger("click");
        await flushPromises();
        expect(wrapper.find("[data-description='grid expanded row']").exists()).toBe(true);

        await wrapper.find("[data-description='filter text input']").setValue("workflow:rna");
        vi.runAllTimers();
        await flushPromises();

        expect(wrapper.find("[data-description='grid expanded row']").exists()).toBe(false);
    });
});
