import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { createTestRouter, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AnyHistory } from "@/api";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import type * as InvocationFilters from "@/components/Workflow/Invocation/invocationFilters";
import { fetchInvocations } from "@/components/Workflow/Invocation/invocationsIndex";
import { useHistoryStore } from "@/stores/historyStore";
import { useInvocationStore } from "@/stores/invocationStore";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import InvocationList from "./InvocationList.vue";

vi.useFakeTimers();

// the list's links and navigation go through a real test router
const router = createTestRouter();
const push = vi.spyOn(router, "push").mockResolvedValue(undefined);

const { confirm } = vi.hoisted(() => ({ confirm: vi.fn() }));
vi.mock("@/composables/confirmDialog", () => ({ useConfirmDialog: () => ({ confirm }) }));

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
    // the user's own history, which a rerun switches to
    useHistoryStore(pinia).storedHistories = {
        "history-1": { id: "history-1", name: "History one", user_id: USER.id } as AnyHistory,
    };
    useWorkflowStore(pinia).workflowsByInstanceId = {
        "instance-1": { id: "stored-1", name: "Name of instance-1", version: 2 } as StoredWorkflowDetailed,
        "instance-2": { id: "stored-2", name: "Name of instance-2" } as StoredWorkflowDetailed,
    };
    return mount(InvocationList as object, {
        props,
        global: {
            ...getLocalVue(),
            plugins: [pinia, router],
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

/** Picks an action from the first row's options menu */
async function clickRowAction(wrapper: ReturnType<typeof mountTarget>, actionId: string) {
    const cell = wrapper.find("tbody .g-table-actions-column");
    await cell.find("button").trigger("click");
    await cell.find(`#${actionId}`).trigger("click");
}

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

    it("links each workflow name to its invocation, with the workflow version numbered from 1", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        const [first, second] = wrapper.findAll(".invocation-workflow");
        expect(first!.find("a").attributes("href")).toBe("/workflows/invocations/inv-1");
        expect(first!.find(".invocation-workflow-version").text()).toBe("v3");
        // a workflow whose version isn't known yet shows no tag
        expect(second!.find(".invocation-workflow-version").exists()).toBe(false);
    });

    it("sends the filter text as the search", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        await wrapper.find("[data-description='filter text input']").setValue("workflow:rna");
        vi.runAllTimers();
        await flushPromises();

        expect(lastQuery().search).toBe("workflow:rna");
    });

    it("sends the state, status and invoked time filters as their own parameters", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        await wrapper
            .find("[data-description='filter text input']")
            .setValue("rna status:problem create_time_gt:2026-11-01 create_time_lt:2026-11-02");
        vi.runAllTimers();
        await flushPromises();

        expect(lastQuery()).toMatchObject({
            search: "workflow:rna",
            state: ["failed"],
            date_range_min: "2026-11-01",
            date_range_max: "2026-11-02",
        });
    });

    it("sets and clears a status group with the status buttons", async () => {
        const wrapper = mountTarget();
        await flushPromises();

        await wrapper.find("[data-status-group='problem']").trigger("click");
        vi.runAllTimers();
        await flushPromises();
        expect(lastQuery().state).toEqual(["failed"]);
        expect(wrapper.find("[data-status-group='problem']").attributes("aria-pressed")).toBe("true");

        // clicking the active group again turns it off
        await wrapper.find("[data-status-group='problem']").trigger("click");
        vi.runAllTimers();
        await flushPromises();
        expect(lastQuery().state).toBeUndefined();
    });

    it("removes a typed state when a status group is picked", async () => {
        const wrapper = mountTarget();
        await flushPromises();
        const input = wrapper.find("[data-description='filter text input']");
        await input.setValue("rna state:completed");
        vi.runAllTimers();
        await flushPromises();

        await wrapper.find("[data-status-group='active']").trigger("click");
        vi.runAllTimers();
        await flushPromises();

        expect((input.element as HTMLInputElement).value).toBe("rna status:active");
        expect(lastQuery().state).toEqual(["new", "requires_materialization", "ready", "scheduled"]);
    });

    it("sets and clears a time range pick as the Invoked time's lower bound", async () => {
        vi.setSystemTime(new Date("2026-11-11T12:00:00.000Z"));
        const wrapper = mountTarget();
        await flushPromises();
        const select = wrapper.find("select[aria-label='Filter invocations by time range']");

        await select.setValue("7d");
        vi.runAllTimers();
        await flushPromises();
        expect(lastQuery().date_range_min).toBe("2026-11-04T12:00:00.000Z");
        expect((select.element as HTMLSelectElement).value).toBe("7d");

        // "Anytime" has no value, so pick it by position
        (select.element as HTMLSelectElement).selectedIndex = 0;
        await select.trigger("change");
        vi.runAllTimers();
        await flushPromises();
        expect(lastQuery().date_range_min).toBeUndefined();
    });

    it("shows a typed Invoked time range as a custom range", async () => {
        const wrapper = mountTarget();
        await flushPromises();
        await wrapper.find("[data-description='filter text input']").setValue("create_time>2026-01-01");
        vi.runAllTimers();
        await flushPromises();

        const options = wrapper.findAll("select[aria-label='Filter invocations by time range'] option");
        expect(options[0]!.text()).toBe("Custom range");
        expect((options[0]!.element as HTMLOptionElement).selected).toBe(true);
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

    it("cancels the selected invocations that are still active, after confirming", async () => {
        const wrapper = mountTarget();
        await flushPromises();
        const cancel = vi.spyOn(useInvocationStore(), "cancelWorkflowScheduling").mockResolvedValue(undefined as never);
        confirm.mockResolvedValue(true);

        await wrapper.find("thead input[type='checkbox']").setValue(true);
        const bulkCancel = wrapper.find("#invocation-list-footer-bulk-cancel-button");
        // only inv-1 is still active
        expect(bulkCancel.text()).toContain("Cancel Selected (1)");

        await bulkCancel.trigger("click");
        await flushPromises();
        expect(confirm).toHaveBeenCalledOnce();
        expect(cancel.mock.calls.map(([id]) => id)).toEqual(["inv-1"]);
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
        const headers = (wrapper: ReturnType<typeof mountTarget>) => wrapper.findAll("thead th").map((th) => th.text());

        beforeEach(() => {
            push.mockClear();
        });

        it("lists the user's invocations in a history", async () => {
            const wrapper = mountTarget({ historyId: "history-1" });
            await flushPromises();

            expect(lastQuery()).toMatchObject({
                history_id: "history-1",
                user_id: USER.id,
                include_nested_invocations: false,
            });
            expect(headers(wrapper)).toEqual(["", "", "Workflow", "Invoked", "State", "Actions"]);
        });

        it("lists the user's invocations of a workflow", async () => {
            const wrapper = mountTarget({ workflowId: "stored-9" });
            await flushPromises();

            expect(lastQuery()).toMatchObject({ workflow_id: "stored-9", user_id: USER.id });
            expect(lastQuery().include_nested_invocations).toBeUndefined();
            expect(headers(wrapper)).toEqual(["", "", "View", "History", "Invoked", "State", "Actions"]);
        });

        it("offers no heading, search or column filters", async () => {
            const wrapper = mountTarget({ historyId: "history-1" });
            await flushPromises();

            expect(wrapper.find("[data-description='grid action import invocation']").exists()).toBe(false);
            expect(wrapper.find("[data-description='filter text input']").exists()).toBe(false);
            expect(wrapper.find("[data-description='grid column filter workflow_id']").exists()).toBe(false);
            expect(lastQuery().search).toBeUndefined();
        });

        it("reruns an invocation with its inputs, as the other lists do", async () => {
            const historyList = mountTarget({ historyId: "history-1" });
            await flushPromises();
            await clickRowAction(historyList, "rerun-invocation");
            expect(push).toHaveBeenLastCalledWith("/workflows/rerun?invocation_id=inv-1");

            const workflowList = mountTarget({ workflowId: "stored-9" });
            await flushPromises();
            await clickRowAction(workflowList, "rerun-invocation");
            expect(push).toHaveBeenLastCalledWith("/workflows/rerun?invocation_id=inv-1");
        });
    });

    describe("a batch run's invocations", () => {
        const headers = (wrapper: ReturnType<typeof mountTarget>) => wrapper.findAll("thead th").map((th) => th.text());

        it("lists the given invocations without requesting any", async () => {
            const wrapper = mountTarget({ invocations: INVOCATIONS });
            await flushPromises();

            expect(fetchInvocations).not.toHaveBeenCalled();
            expect(rows(wrapper)).toHaveLength(2);
            expect(headers(wrapper)).toEqual(["", "", "View", "History", "Invoked", "State", "Actions"]);
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
