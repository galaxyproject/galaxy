import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useRouter } from "vue-router";

import type { StoredWorkflowDetailed } from "@/api/workflows";
import type * as InvocationFilters from "@/components/Workflow/Invocation/invocationFilters";
import { fetchInvocations } from "@/components/Workflow/Invocation/invocationsIndex";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import InvocationList from "./InvocationList.vue";

vi.useFakeTimers();

vi.mock("vue-router");

vi.mock("@/components/Workflow/Invocation/invocationsIndex", () => ({
    fetchInvocations: vi.fn(),
}));

vi.mock("@/components/Workflow/Invocation/invocationFilters", async (importOriginal) => {
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

type InvocationsPage = Awaited<ReturnType<typeof fetchInvocations>>;

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

function mountTarget(props: Record<string, unknown> = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    useUserStore(pinia).currentUser = USER;
    useWorkflowStore(pinia).workflowsByInstanceId = {
        "instance-1": { id: "stored-1", name: "Name of instance-1" } as StoredWorkflowDetailed,
        "instance-2": { id: "stored-2", name: "Name of instance-2" } as StoredWorkflowDetailed,
    };
    return mount(InvocationList as object, {
        props,
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

const lastQuery = () => vi.mocked(fetchInvocations).mock.calls.at(-1)![0];
const filterInput = (wrapper: ReturnType<typeof mountTarget>) =>
    wrapper.find("[data-description='filter text input']").element as HTMLInputElement;
const rows = (wrapper: ReturnType<typeof mountTarget>) => wrapper.findAll("tbody tr[id^='g-table-row-']");

describe("InvocationList", () => {
    beforeEach(() => {
        vi.mocked(fetchInvocations).mockReset();
        vi.mocked(fetchInvocations).mockResolvedValue([INVOCATIONS, 2] as unknown as InvocationsPage);
    });

    it("lists the user's invocations, newest first", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        expect(lastQuery()).toEqual({
            limit: 25,
            offset: 0,
            sort_by: "create_time",
            sort_desc: true,
            include_nested_invocations: false,
            search: undefined,
            user_id: USER.id,
        });
        expect(rows(wrapper)).toHaveLength(2);
        expect(wrapper.text()).toContain("Name of instance-1");
    });

    it("sends the filter text as the search", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        await wrapper.find("[data-description='filter text input']").setValue("workflow:rna");
        vi.runAllTimers();
        await flushPromises();

        expect(lastQuery().search).toBe("workflow:rna");
    });

    it("sorts by invocation time when the Invoked header is clicked", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        await wrapper.find("th.g-table-sortable").trigger("click");
        await flushPromises();

        expect(lastQuery()).toMatchObject({ sort_by: "create_time", sort_desc: false });
    });

    it("picks workflows from the column filter and removes them with their chips", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        await wrapper.find("[data-description='grid column filter workflow_id'] button").trigger("click");
        await flushPromises();
        await wrapper.find("input[data-description='grid column filter option workflow-2']").setValue(true);
        await flushPromises();

        expect(filterInput(wrapper).value).toBe("workflow_id:workflow-2");
        expect(lastQuery().search).toBe("workflow_id:workflow-2");
        const chips = wrapper.findAll("[data-description='grid active column filter workflow_id']");
        expect(chips.map((chip) => chip.text())).toEqual(["Workflow: Workflow two"]);

        await chips[0]!.trigger("click");
        await flushPromises();
        expect(filterInput(wrapper).value).toBe("");
    });

    it("keeps the column filters available when the filters match nothing", async () => {
        const wrapper = mountTarget();
        await flushPromises();
        vi.mocked(fetchInvocations).mockResolvedValue([[], 0] as InvocationsPage);

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

    describe("admin mode", () => {
        const ADMIN_PROPS = {
            admin: true,
            headerMessage: "Invocations still being scheduled",
            noDataMessage: "Nothing is being scheduled",
        };

        it("lists every user's invocations that are still being scheduled", async () => {
            mountTarget(ADMIN_PROPS);
            await flushPromises();

            expect(lastQuery()).toMatchObject({ include_terminal: false });
            expect(lastQuery().user_id).toBeUndefined();
        });

        it("offers no search or column filters, whose lookups only cover the admin's own items", async () => {
            const wrapper = mountTarget(ADMIN_PROPS);
            await flushPromises();

            expect(rows(wrapper)).toHaveLength(2);
            expect(wrapper.find("[data-description='filter text input']").exists()).toBe(false);
            expect(wrapper.find("[data-description='grid column filter workflow_id']").exists()).toBe(false);
            expect(wrapper.find("[data-description='grid column filter history_id']").exists()).toBe(false);
        });

        it("shows the header message for a while, and its own message when nothing is listed", async () => {
            vi.mocked(fetchInvocations).mockResolvedValue([[], 0] as InvocationsPage);
            const wrapper = mountTarget(ADMIN_PROPS);
            await flushPromises();

            expect(wrapper.text()).toContain("Invocations still being scheduled");
            expect(wrapper.text()).toContain("Nothing is being scheduled");

            // the alert counts down a second at a time
            await vi.runAllTimersAsync();
            expect(wrapper.text()).not.toContain("Invocations still being scheduled");
        });
    });

    describe("scoped to one history or workflow", () => {
        const push = vi.fn();
        const headers = (wrapper: ReturnType<typeof mountTarget>) => wrapper.findAll("thead th").map((th) => th.text());

        beforeEach(() => {
            push.mockReset();
            vi.mocked(useRouter).mockReturnValue({ push } as unknown as ReturnType<typeof useRouter>);
        });

        it("lists the user's invocations in a history, loading only workflow names", async () => {
            const wrapper = mountTarget({ historyId: "history-1" });
            await flushPromises();

            expect(lastQuery()).toMatchObject({
                history_id: "history-1",
                user_id: USER.id,
                include_nested_invocations: false,
            });
            expect(vi.mocked(fetchInvocations).mock.calls.at(-1)![1]).toEqual({ histories: false, workflows: true });
            expect(headers(wrapper)).toEqual(["", "Workflow", "Invoked", "State", "Run"]);
        });

        it("lists the user's invocations of a workflow, loading only history names", async () => {
            const wrapper = mountTarget({ workflowId: "stored-9" });
            await flushPromises();

            expect(lastQuery()).toMatchObject({ workflow_id: "stored-9", user_id: USER.id });
            expect(lastQuery().include_nested_invocations).toBeUndefined();
            expect(vi.mocked(fetchInvocations).mock.calls.at(-1)![1]).toEqual({ histories: true, workflows: false });
            expect(headers(wrapper)).toEqual(["", "View", "History", "Invoked", "State", "Run"]);
        });

        it("offers no heading, search or column filters", async () => {
            const wrapper = mountTarget({ historyId: "history-1" });
            await flushPromises();

            expect(wrapper.find("[data-description='grid action import invocation']").exists()).toBe(false);
            expect(wrapper.find("[data-description='filter text input']").exists()).toBe(false);
            expect(wrapper.find("[data-description='grid column filter workflow_id']").exists()).toBe(false);
            expect(lastQuery().search).toBeUndefined();
        });

        it("runs the invocation's workflow afresh", async () => {
            const historyList = mountTarget({ historyId: "history-1" });
            await flushPromises();
            await historyList.find("tbody tr[id^='g-table-row-'] button[title='Run']").trigger("click");
            expect(push).toHaveBeenLastCalledWith("/workflows/run?id=stored-1");

            const workflowList = mountTarget({ workflowId: "stored-9" });
            await flushPromises();
            await workflowList.find("tbody tr[id^='g-table-row-'] button[title='Run']").trigger("click");
            expect(push).toHaveBeenLastCalledWith("/workflows/run?id=stored-9");
        });
    });

    describe("a batch run's invocations", () => {
        const headers = (wrapper: ReturnType<typeof mountTarget>) => wrapper.findAll("thead th").map((th) => th.text());

        it("lists the given invocations without requesting any", async () => {
            const wrapper = mountTarget({ invocations: INVOCATIONS });
            await flushPromises();

            expect(fetchInvocations).not.toHaveBeenCalled();
            expect(rows(wrapper)).toHaveLength(2);
            expect(headers(wrapper)).toEqual(["", "View", "History", "Invoked", "State"]);
        });

        it("offers no heading, search, sorting or pager", async () => {
            const wrapper = mountTarget({ invocations: INVOCATIONS });
            await flushPromises();

            expect(wrapper.find("[data-description='grid action import invocation']").exists()).toBe(false);
            expect(wrapper.find("[data-description='filter text input']").exists()).toBe(false);
            expect(wrapper.find("th.g-table-sortable").exists()).toBe(false);
            expect(wrapper.find("[data-description='invocation list pager']").exists()).toBe(false);
        });

        it("opens an invocation in a new tab, keeping the run's results page", async () => {
            const open = vi.spyOn(window, "open").mockImplementation(() => null);
            const wrapper = mountTarget({ invocations: INVOCATIONS });
            await flushPromises();

            await wrapper.find("tbody tr[id^='g-table-row-'] button[title='View']").trigger("click");

            expect(open).toHaveBeenCalledWith(expect.stringMatching(/\/workflows\/invocations\/inv-1$/), "_blank");
            open.mockRestore();
        });
    });
});
