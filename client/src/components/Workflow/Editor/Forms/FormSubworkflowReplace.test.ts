import { getLocalVue } from "@tests/vitest/helpers";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { loadWorkflows, type WorkflowSummary } from "@/api/workflows";
import { getVersions } from "@/components/Workflow/Editor/modules/services";

import FormSubworkflowReplace from "./FormSubworkflowReplace.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";

const { getTrsServers, getTrsTool } = vi.hoisted(() => ({ getTrsServers: vi.fn(), getTrsTool: vi.fn() }));

vi.mock("@/api/workflows", () => ({ loadWorkflows: vi.fn() }));
vi.mock("@/components/Workflow/Editor/modules/services", () => ({ getVersions: vi.fn() }));
vi.mock("@/components/Workflow/services", () => ({
    Services: class {
        getTrsServers = getTrsServers;
        getTrsTool = getTrsTool;
    },
}));

const localVue = getLocalVue();

const WORKFLOWS = [
    { id: "edited", name: "Edited workflow", owner: "me" },
    { id: "mine", name: "My QC", owner: "me" },
    { id: "published", name: "Published QC", owner: "someone" },
] as WorkflowSummary[];

async function mountForm(): Promise<VueWrapper> {
    const wrapper = mount(FormSubworkflowReplace as object, {
        props: { stepId: 2, workflowId: "edited" },
        localVue,
    });
    await flushPromises();
    expect(loadWorkflows).not.toHaveBeenCalled();
    await wrapper.find("button").trigger("click");
    await flushPromises();
    return wrapper;
}

function selectLabelled(wrapper: VueWrapper, label: string) {
    return wrapper.find(`select[aria-label="${label}"]`);
}

function workflowCombobox(wrapper: VueWrapper) {
    return wrapper.find(".multiselect");
}

function listedWorkflows(wrapper: VueWrapper) {
    return workflowCombobox(wrapper)
        .findAll(".multiselect__element")
        .filter((element) => element.isVisible())
        .map((element) => element.text());
}

async function chooseWorkflow(wrapper: VueWrapper, text: string) {
    await workflowCombobox(wrapper).trigger("focus");
    const option = workflowCombobox(wrapper)
        .findAll(".multiselect__element")
        .find((element) => element.text() === text)!;
    await option.find(".multiselect__option").trigger("click");
    await flushPromises();
}

function replaceButton(wrapper: VueWrapper) {
    return wrapper.findAll("button").find((button) => button.text() === "Replace")!;
}

describe("FormSubworkflowReplace", () => {
    beforeEach(() => {
        vi.mocked(loadWorkflows).mockReset().mockResolvedValue({ data: WORKFLOWS, totalMatches: 3 });
        vi.mocked(getVersions)
            .mockReset()
            .mockResolvedValue([
                { version: 0, update_time: "2026-09-01T10:00:00", steps: 2 },
                { version: 1, update_time: "2026-10-30T10:00:00", steps: 3 },
            ]);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("searches own, shared and published workflows except the one being edited", async () => {
        const wrapper = await mountForm();
        expect(loadWorkflows).toHaveBeenCalledWith(
            expect.objectContaining({ filterText: "", showPublished: true, showShared: true }),
        );
        await workflowCombobox(wrapper).trigger("focus");
        expect(listedWorkflows(wrapper)).toEqual(["My QC (me)", "Published QC (someone)"]);
        expect(replaceButton(wrapper).attributes("aria-disabled")).toBe("true");
    });

    it("keeps the list open while search results arrive and keeps the chosen workflow", async () => {
        const wrapper = await mountForm();
        await chooseWorkflow(wrapper, "Published QC (someone)");

        vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
        let deliverResults: (results: { data: WorkflowSummary[]; totalMatches: number }) => void = () => {};
        vi.mocked(loadWorkflows).mockReturnValueOnce(new Promise((resolve) => (deliverResults = resolve)));
        await workflowCombobox(wrapper).trigger("focus");
        await wrapper.find("input.multiselect__input").setValue("other");
        await vi.advanceTimersByTimeAsync(400);
        expect(loadWorkflows).toHaveBeenLastCalledWith(expect.objectContaining({ filterText: "other" }));
        expect(workflowCombobox(wrapper).classes()).toContain("multiselect--active");

        deliverResults({ data: [{ id: "other", name: "Other QC", owner: "me" } as WorkflowSummary], totalMatches: 1 });
        await flushPromises();
        expect(workflowCombobox(wrapper).classes()).toContain("multiselect--active");
        expect(listedWorkflows(wrapper)).toEqual(["Other QC (me)"]);

        await replaceButton(wrapper).trigger("click");
        expect(wrapper.emitted("onAttemptRefactor")?.[0]?.[0]).toEqual([
            expect.objectContaining({ stored_workflow_id: "published", version: 1 }),
        ]);
    });

    it("replaces the step with the newest version of the chosen workflow by default", async () => {
        const wrapper = await mountForm();
        await chooseWorkflow(wrapper, "Published QC (someone)");
        expect(getVersions).toHaveBeenCalledWith("published");
        const versionSelect = selectLabelled(wrapper, "Version of the replacement workflow");
        expect(versionSelect.findAll("option").map((option) => option.text())).toEqual([
            "Version 1: Sep 1st 2026, 2 steps",
            "Version 2: Oct 30th 2026, 3 steps (newest)",
        ]);
        await replaceButton(wrapper).trigger("click");
        await versionSelect.setValue("0");
        await replaceButton(wrapper).trigger("click");
        expect(wrapper.emitted("onAttemptRefactor")).toEqual([
            [
                [
                    {
                        action_type: "upgrade_subworkflow",
                        step: { order_index: 2 },
                        recursive: false,
                        stored_workflow_id: "published",
                        version: 1,
                    },
                ],
            ],
            [
                [
                    {
                        action_type: "upgrade_subworkflow",
                        step: { order_index: 2 },
                        recursive: false,
                        stored_workflow_id: "published",
                        version: 0,
                    },
                ],
            ],
        ]);
    });

    it("replaces the step with the newest version of a workflow on a TRS server", async () => {
        const tool = "#workflow/github.com/org/repo/main";
        getTrsServers.mockResolvedValue([{ id: "dockstore", label: "Dockstore" }]);
        getTrsTool.mockResolvedValue({
            id: tool,
            versions: [
                { id: `${tool}:main`, name: "main" },
                { id: `${tool}:v0.1`, name: "v0.1" },
                { id: `${tool}:v0.2`, name: "v0.2" },
            ],
        });
        const wrapper = await mountForm();
        await selectLabelled(wrapper, "Replacement source").setValue("trs");
        await flushPromises();
        expect(replaceButton(wrapper).attributes("aria-disabled")).toBe("true");
        wrapper.findComponent(DelayedInput as object).vm.$emit("input", ` ${tool} `);
        await flushPromises();
        expect(getTrsTool).toHaveBeenCalledWith("dockstore", tool);
        const versionSelect = selectLabelled(wrapper, "TRS version of the replacement workflow");
        expect(versionSelect.findAll("option").map((option) => option.text())).toEqual(["v0.2", "v0.1", "main"]);
        await replaceButton(wrapper).trigger("click");
        expect(wrapper.emitted("onAttemptRefactor")).toEqual([
            [
                [
                    {
                        action_type: "upgrade_subworkflow",
                        step: { order_index: 2 },
                        recursive: false,
                        trs_server: "dockstore",
                        trs_tool_id: tool,
                        trs_version_id: "v0.2",
                    },
                ],
            ],
        ]);
    });

    it("replaces the step with the workflow at a URL", async () => {
        const wrapper = await mountForm();
        await selectLabelled(wrapper, "Replacement source").setValue("url");
        await flushPromises();
        expect(replaceButton(wrapper).attributes("aria-disabled")).toBe("true");
        const url = "https://github.com/org/repo/blob/main/workflow.ga";
        await wrapper.find('input[type="url"]').setValue(` ${url} `);
        await replaceButton(wrapper).trigger("click");
        expect(wrapper.emitted("onAttemptRefactor")).toEqual([
            [[{ action_type: "upgrade_subworkflow", step: { order_index: 2 }, recursive: false, url }]],
        ]);
    });
});
