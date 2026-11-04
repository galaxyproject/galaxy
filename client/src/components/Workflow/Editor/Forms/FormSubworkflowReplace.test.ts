import { getLocalVue } from "@tests/vitest/helpers";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadWorkflows, type WorkflowSummary } from "@/api/workflows";
import { getVersions } from "@/components/Workflow/Editor/modules/services";

import FormSubworkflowReplace from "./FormSubworkflowReplace.vue";

vi.mock("@/api/workflows", () => ({ loadWorkflows: vi.fn() }));
vi.mock("@/components/Workflow/Editor/modules/services", () => ({ getVersions: vi.fn() }));

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

    it("searches own, shared and published workflows except the one being edited", async () => {
        const wrapper = await mountForm();
        expect(loadWorkflows).toHaveBeenCalledWith(
            expect.objectContaining({ filterText: "", showPublished: true, showShared: true }),
        );
        const options = wrapper.find("select").findAll("option");
        expect(options.map((option) => option.text())).toEqual([
            "Select a workflow",
            "My QC (me)",
            "Published QC (someone)",
        ]);
        expect(replaceButton(wrapper).attributes("aria-disabled")).toBe("true");
    });

    it("replaces the step with the newest version of the chosen workflow by default", async () => {
        const wrapper = await mountForm();
        await wrapper.find("select").setValue("published");
        await flushPromises();
        expect(getVersions).toHaveBeenCalledWith("published");
        const versionSelect = wrapper.findAll("select")[1]!;
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
                        stored_workflow_id: "published",
                        version: 1,
                        recursive: false,
                    },
                ],
            ],
            [
                [
                    {
                        action_type: "upgrade_subworkflow",
                        step: { order_index: 2 },
                        stored_workflow_id: "published",
                        version: 0,
                        recursive: false,
                    },
                ],
            ],
        ]);
    });
});
