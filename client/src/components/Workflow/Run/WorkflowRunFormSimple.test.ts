import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, suppressDebugConsole } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { h, ref } from "vue";

import { invokeWorkflow } from "./services";

import WorkflowRunFormSimple from "./WorkflowRunFormSimple.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

vi.mock("./services", () => ({
    invokeWorkflow: vi.fn(),
    searchHistoryContents: vi.fn(),
}));
vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config: ref({}), isConfigLoaded: ref(true) }),
}));
vi.mock("@/composables/fileSources", () => ({
    useFileSources: () => ({ hasWritable: ref(false) }),
}));
vi.mock("@/composables/useWorkflowInstance", () => ({
    useWorkflowInstance: () => ({ workflow: ref(null), loading: ref(false) }),
}));

function stub(name: string, props: string[] = []) {
    return { default: { name, props, render: () => h("div") } };
}

vi.mock("@/components/Form/FormDisplay.vue", () => stub("FormDisplay", ["inputs"]));
vi.mock("../WorkflowNavigationTitle.vue", () => ({
    default: {
        name: "WorkflowNavigationTitle",
        setup(_props: unknown, { slots }: { slots: Record<string, (() => unknown) | undefined> }) {
            return () => h("div", slots["workflow-title-actions"]?.() as any);
        },
    },
}));
vi.mock("../WorkflowAnnotation.vue", () => stub("WorkflowAnnotation"));
vi.mock("./WorkflowRunGraph.vue", () => stub("WorkflowRunGraph", ["stepValidation"]));
vi.mock("./WorkflowHelpDisplay.vue", () => stub("WorkflowHelpDisplay"));
vi.mock("./WorkflowStorageConfiguration.vue", () => stub("WorkflowStorageConfiguration"));
vi.mock("./ExportOnCompleteWizard.vue", () => stub("ExportOnCompleteWizard"));
vi.mock("@/components/Workflow/Run/WorkflowCredentials.vue", () => stub("WorkflowCredentials"));

const globalConfig = getLocalVue();

function inputStep(index: number, label: string, input: Record<string, unknown>, section?: string) {
    return {
        step_index: index,
        step_label: label,
        step_type: input.type === "data" ? "data_input" : "parameter_input",
        inputs: [{ name: "input", label, ...input }],
        output_connections: [],
        ...(section ? { section } : {}),
    };
}

function runData(inputSections: Record<string, unknown>[] | undefined, steps: Record<string, unknown>[]) {
    return {
        id: "stored_id",
        workflow_id: "workflow_id",
        name: "Sectioned workflow",
        history_id: "history_id",
        version: 1,
        steps,
        ...(inputSections ? { input_sections: inputSections } : {}),
    };
}

const SECTIONED_STEPS = [
    inputStep(0, "reads", { type: "data", optional: false }),
    inputStep(1, "min_quality", { type: "integer", optional: false, value: 20 }, "advanced"),
    inputStep(2, "adapter", { type: "text", optional: true, value: "" }, "advanced"),
    inputStep(3, "threads", { type: "integer", optional: false, value: 4 }),
    inputStep(4, "reference", { type: "data", optional: false }, "references"),
];

function mountForm(data: Record<string, unknown>) {
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        initialState: {
            userStore: { currentUser: { id: "user_id" } },
            historyStore: {
                storedHistories: { current_history_id: { id: "current_history_id", name: "Current" } },
            },
        },
    });
    setActivePinia(pinia);
    return mount(WorkflowRunFormSimple as object, {
        props: {
            model: {
                workflowId: "stored_id",
                name: data.name,
                historyId: "history_id",
                runData: data,
                steps: data.steps,
                wpInputs: {},
            },
            canMutateCurrentHistory: true,
        },
        global: {
            ...globalConfig,
            plugins: [...(globalConfig.plugins ?? []), pinia],
        },
    });
}

function formDisplay(wrapper: VueWrapper) {
    return wrapper.findComponent({ name: "FormDisplay" });
}

function displayedLayout(wrapper: VueWrapper) {
    return formDisplay(wrapper)
        .props("inputs")
        .map((input: any) =>
            input.type === "section"
                ? {
                      section: input.name,
                      title: input.title,
                      expanded: input.expanded,
                      help: input.help,
                      inputs: input.inputs.map((i: any) => String(i.name)),
                  }
                : String(input.name),
        );
}

describe("WorkflowRunFormSimple input sections", () => {
    beforeEach(() => {
        suppressDebugConsole();
        vi.mocked(invokeWorkflow).mockReset();
        vi.mocked(invokeWorkflow).mockResolvedValue([{ id: "invocation_id" }]);
    });

    it("renders a flat list when the workflow has no sections", () => {
        const wrapper = mountForm(
            runData(undefined, [
                inputStep(0, "reads", { type: "data" }),
                inputStep(1, "n", { type: "integer", value: 1 }),
            ]),
        );
        expect(displayedLayout(wrapper)).toEqual(["0", "1"]);
    });

    it("groups inputs into sections placed at their first member", () => {
        const wrapper = mountForm(
            runData(
                [{ name: "advanced", label: "Advanced options", expanded: false, help: "Rarely changed." }],
                SECTIONED_STEPS,
            ),
        );
        expect(displayedLayout(wrapper)).toEqual([
            "0",
            {
                section: "advanced",
                title: "Advanced options",
                expanded: false,
                help: "Rarely changed.",
                inputs: ["1", "2"],
            },
            "3",
            // No definition: labelled by name, opened because its required input has no value.
            { section: "references", title: "references", expanded: true, help: undefined, inputs: ["4"] },
        ]);
    });

    it("submits section inputs keyed by step index", async () => {
        const wrapper = mountForm(runData([{ name: "advanced", label: "Advanced options" }], SECTIONED_STEPS));
        formDisplay(wrapper).vm.$emit("onChange", {
            0: { values: [{ id: "d1", src: "hda" }] },
            "advanced|1": 30,
            "advanced|2": "AGATCGGAAGAGC",
            3: 8,
            "references|4": { values: [{ id: "d2", src: "hda" }] },
        });
        await wrapper.vm.$nextTick();
        wrapper.findComponent({ name: "WorkflowNavigationTitle" }).vm.$emit("on-execute");
        await flushPromises();
        expect(vi.mocked(invokeWorkflow).mock.calls[0]![1].inputs).toEqual({
            0: { values: [{ id: "d1", src: "hda" }] },
            1: 30,
            2: "AGATCGGAAGAGC",
            3: 8,
            4: { values: [{ id: "d2", src: "hda" }] },
        });
    });

    it("passes validation for section inputs to the graph by step index", async () => {
        const wrapper = mountForm(runData([{ name: "advanced" }], SECTIONED_STEPS));
        formDisplay(wrapper).vm.$emit("onValidation", ["advanced|1", "Please provide a value for this option."]);
        const graphButton = wrapper
            .findAllComponents(GButton)
            .find((button) => button.props("title") === "Show workflow graph");
        await graphButton!.trigger("click");
        expect(wrapper.findComponent({ name: "WorkflowRunGraph" }).props("stepValidation")).toEqual([
            "1",
            "Please provide a value for this option.",
        ]);
    });
});
