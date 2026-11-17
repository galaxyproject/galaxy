import { getLocalVue } from "@tests/vitest/helpers";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getSubworkflowVersions, type SubworkflowVersions } from "@/api/workflows";

import FormSubworkflowVersion from "./FormSubworkflowVersion.vue";

vi.mock("@/api/workflows", () => ({ getSubworkflowVersions: vi.fn() }));

const localVue = getLocalVue();

const STORED_VERSIONS: SubworkflowVersions = {
    workflow_id: "sub1",
    stored_workflow_id: "stored1",
    current_version: 0,
    versions: [
        { version: 0, workflow_id: "sub1", update_time: "2026-09-01T10:00:00", steps: 2 },
        { version: 1, workflow_id: "sub2", update_time: "2026-10-30T10:00:00", steps: 3 },
    ],
};

const TRS_VERSIONS: SubworkflowVersions = {
    ...STORED_VERSIONS,
    versions: [STORED_VERSIONS.versions[0]!],
    trs_tool_id: "#workflow/github.com/iwc-workflows/example/main",
    trs_version_id: "v0.1",
    trs_versions: [
        { trs_version_id: "v0.2", name: "v0.2" },
        { trs_version_id: "v0.1", name: "v0.1" },
    ],
    trs_upgrade_version_id: "v0.2",
};

async function mountWith(versions: SubworkflowVersions): Promise<VueWrapper> {
    vi.mocked(getSubworkflowVersions).mockResolvedValue(versions);
    const wrapper = mount(FormSubworkflowVersion as object, {
        props: { contentId: "sub1", stepId: 3 },
        localVue,
    });
    await flushPromises();
    return wrapper;
}

function optionTexts(wrapper: VueWrapper) {
    return wrapper.findAll("option").map((option) => option.text());
}

function switchButton(wrapper: VueWrapper) {
    return wrapper.findAll("button").find((button) => button.text() === "Switch version")!;
}

describe("FormSubworkflowVersion", () => {
    beforeEach(() => {
        vi.mocked(getSubworkflowVersions).mockReset();
    });

    it("lists the stored versions and marks the current and newest ones", async () => {
        const wrapper = await mountWith(STORED_VERSIONS);
        expect(getSubworkflowVersions).toHaveBeenCalledWith("sub1");
        expect(optionTexts(wrapper)).toEqual([
            "Version 1: Sep 1st 2026, 2 steps (current)",
            "Version 2: Oct 30th 2026, 3 steps (newest)",
        ]);
        expect(switchButton(wrapper).attributes("aria-disabled")).toBe("true");
    });

    it("switches to a stored version, recursively when asked", async () => {
        const wrapper = await mountWith(STORED_VERSIONS);
        expect(wrapper.find("input[type=checkbox]").exists()).toBe(false);
        await wrapper.find("select").setValue("stored:1");
        await wrapper.find("input[type=checkbox]").setValue(true);
        await switchButton(wrapper).trigger("click");
        expect(wrapper.emitted("onAttemptRefactor")).toEqual([
            [[{ action_type: "upgrade_subworkflow", step: { order_index: 3 }, recursive: true, version: 1 }]],
        ]);
    });

    it("offers TRS releases and switches to one", async () => {
        const wrapper = await mountWith(TRS_VERSIONS);
        expect(optionTexts(wrapper)).toEqual([
            "Version 1: Sep 1st 2026, 2 steps (current, newest)",
            "v0.2 (newer)",
            "v0.1 (current)",
        ]);
        await wrapper.find("select").setValue("trs:v0.2");
        await switchButton(wrapper).trigger("click");
        expect(wrapper.emitted("onAttemptRefactor")).toEqual([
            [
                [
                    {
                        action_type: "upgrade_subworkflow",
                        step: { order_index: 3 },
                        recursive: false,
                        trs_version_id: "v0.2",
                    },
                ],
            ],
        ]);
    });

    it("says why TRS releases are missing", async () => {
        const wrapper = await mountWith({
            ...STORED_VERSIONS,
            trs_tool_id: "x",
            trs_error: "TRS server could not be reached.",
        });
        expect(wrapper.text()).toContain("TRS versions are unavailable: TRS server could not be reached.");
    });
});
