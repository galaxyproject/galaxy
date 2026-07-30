import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";

import SubworkflowPanel from "./SubworkflowPanel.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

vi.mock("@/components/Workflow/workflows.services", () => ({
    getWorkflowFull: vi.fn(),
}));

const localVue = getLocalVue();
const CONTENT_ID = "c0ffee";

const SUBWORKFLOW = {
    name: "Demo B middle",
    steps: {
        0: {
            id: 0,
            type: "data_input",
            label: "b_input",
            name: "Input dataset",
            input_connections: {},
            inputs: [],
            outputs: [{ name: "output", extensions: ["input"], optional: false }],
            tool_state: {},
        },
        1: {
            id: 1,
            type: "subworkflow",
            label: "b_inner",
            name: "Demo C inner",
            content_id: "deadbeef",
            input_connections: {},
            inputs: [],
            outputs: [],
            tool_state: {},
        },
    },
    comments: [],
    report: {},
};

function mountPanel(): Wrapper<Vue> {
    return shallowMount(SubworkflowPanel as object, {
        propsData: {
            contentId: CONTENT_ID,
            trailNames: ["Demo A parent"],
            datatypes: [],
            datatypesMapper: testDatatypesMapper,
        },
        localVue,
    });
}

/** The footer actions, addressed as components since shallowMount renders them as stubs. */
function buttonWith(wrapper: Wrapper<Vue>, text: string) {
    const found = wrapper.findAllComponents(GButton).filter((button) => button.text().includes(text));
    if (found.length === 0) {
        throw new Error(`no button reading "${text}" in: ${wrapper.text()}`);
    }
    return found.at(0);
}

function graphOf(wrapper: Wrapper<Vue>) {
    return wrapper.findComponent(WorkflowGraph);
}

describe("SubworkflowPanel", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        setActivePinia(createTestingPinia({ createSpy: vi.fn, stubActions: false }));
        vi.mocked(getWorkflowFull).mockResolvedValue(structuredClone(SUBWORKFLOW));
    });

    it("loads the subworkflow as a revision, not as a stored workflow", async () => {
        mountPanel();
        await flushPromises();
        // a step's content_id is a workflow revision; without the instance flag the id is looked
        // up as a stored workflow and the request 404s, which read as "it doesn't know the workflow"
        expect(vi.mocked(getWorkflowFull)).toHaveBeenCalledWith(CONTENT_ID, undefined, true);
    });

    it("names the way in, ending with the subworkflow being shown", async () => {
        const wrapper = mountPanel();
        await flushPromises();
        expect(wrapper.text()).toContain("Demo A parent");
        expect(wrapper.text()).toContain("Demo B middle");
    });

    it("reports a load failure instead of showing an empty panel", async () => {
        vi.mocked(getWorkflowFull).mockRejectedValue(new Error("No such workflow found"));
        const wrapper = mountPanel();
        await flushPromises();
        expect(wrapper.text()).toContain("No such workflow found");
    });

    it("opens a nested subworkflow when a node inside asks to be edited", async () => {
        const wrapper = mountPanel();
        await flushPromises();

        // the graph forwards a node's Edit; the caller needs the step index to know
        // what to save the nested edit back into
        graphOf(wrapper).vm.$emit("editSubworkflow", "deadbeef", 1);
        expect(wrapper.emitted("openNested")![0]).toEqual(["deadbeef", "b_inner", 1]);
    });

    it("passes a node's upgrade on, saying whether there are unsaved edits", async () => {
        const wrapper = mountPanel();
        await flushPromises();
        graphOf(wrapper).vm.$emit("upgradeSubworkflow", 1);
        expect(wrapper.emitted("upgradeStep")![0]).toEqual([CONTENT_ID, 1, false]);

        graphOf(wrapper).vm.$emit("onChange");
        await wrapper.vm.$nextTick();
        graphOf(wrapper).vm.$emit("upgradeSubworkflow", 1);
        expect(wrapper.emitted("upgradeStep")![1]).toEqual([CONTENT_ID, 1, true]);
    });

    it("cannot be applied until something is changed", async () => {
        const wrapper = mountPanel();
        await flushPromises();
        expect(buttonWith(wrapper, "Apply changes").props("disabled")).toBe(true);

        graphOf(wrapper).vm.$emit("onChange");
        await wrapper.vm.$nextTick();
        expect(buttonWith(wrapper, "Apply changes").props("disabled")).toBe(false);
    });

    it("hands the caller the steps it is showing when applied", async () => {
        const wrapper = mountPanel();
        await flushPromises();

        graphOf(wrapper).vm.$emit("onChange");
        await wrapper.vm.$nextTick();
        buttonWith(wrapper, "Apply changes").vm.$emit("click");
        await wrapper.vm.$nextTick();

        const applied = wrapper.emitted("apply")![0] as [string, Record<string, any>];
        expect(applied[0]).toBe(CONTENT_ID);
        expect(applied[1].name).toBe("Demo B middle");
        expect(Object.keys(applied[1].steps)).toHaveLength(2);
    });

    it("closes without applying when cancelled", async () => {
        const wrapper = mountPanel();
        await flushPromises();
        buttonWith(wrapper, "Cancel").vm.$emit("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted("close")).toHaveLength(1);
        expect(wrapper.emitted("apply")).toBeUndefined();
    });
});
