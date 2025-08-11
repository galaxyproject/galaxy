import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { extractWorkflowFromHistory, submitWorkflowExtraction, type WorkflowExtractionSummary } from "@/api/histories";
import { Toast } from "@/composables/toast";

import GFormInput from "../BaseComponents/Form/GFormInput.vue";
import GButton from "../BaseComponents/GButton.vue";
import RenameModal from "../Common/RenameModal.vue";
import LoadingSpan from "../LoadingSpan.vue";
import WorkflowExtractionCard from "./WorkflowExtraction/WorkflowExtractionCard.vue";
import WorkflowExtractionMessages from "./WorkflowExtraction/WorkflowExtractionMessages.vue";
import WorkflowExtractionForm from "./WorkflowExtractionForm.vue";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("@/api/histories", () => ({
    extractWorkflowFromHistory: vi.fn(),
    submitWorkflowExtraction: vi.fn(),
}));

vi.mock("@/composables/toast", () => {
    const toastInstance = { success: vi.fn(), error: vi.fn() };
    return {
        Toast: toastInstance,
        useToast: () => toastInstance,
    };
});

vi.mock("vue-router", () => ({
    useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => ({
        getHistoryNameById: vi.fn().mockReturnValue("My History"),
        currentHistoryId: "history-1",
    }),
}));

// ── Fixtures ─────────────────────────────────────────────────────────────────

const TOOL_JOB = {
    id: "job-tool-1",
    tool_id: "cat1",
    tool_name: "Concatenate",
    tool_version: "1.0",
    step_type: "tool" as const,
    checked: true,
    tool_version_warning: null,
    outputs: [
        { id: "ds-1", hid: 1, name: "output1", history_content_type: "dataset" as const, state: "ok", deleted: false },
    ],
};

const INPUT_JOB = {
    id: null,
    tool_id: null,
    tool_name: "Input Dataset",
    tool_version: null,
    step_type: "input_dataset" as const,
    checked: true,
    tool_version_warning: null,
    outputs: [
        {
            id: "ds-2",
            hid: 2,
            name: "myfile.txt",
            history_content_type: "dataset" as const,
            state: "ok",
            deleted: false,
        },
    ],
};

const SUMMARY_WITH_JOBS = { jobs: [TOOL_JOB, INPUT_JOB], warnings: [] } as unknown as WorkflowExtractionSummary;
const SUMMARY_EMPTY = { jobs: [], warnings: [] } as unknown as WorkflowExtractionSummary;
const SUMMARY_WITH_WARNINGS = {
    jobs: [TOOL_JOB],
    warnings: ["Tool version mismatch"],
} as unknown as WorkflowExtractionSummary;

// ── Helpers ───────────────────────────────────────────────────────────────────

const localVue = getLocalVue();

async function mountForm(historyId = "history-1") {
    const wrapper = shallowMount(WorkflowExtractionForm as object, {
        propsData: { historyId },
        localVue,
    });
    await flushPromises();
    return wrapper;
}

/** Set the workflow name by simulating GFormInput's `input` event (v-model). */
async function setWorkflowName(wrapper: ReturnType<typeof shallowMount>, name: string) {
    wrapper.findComponent(GFormInput).vm.$emit("input", name);
    await wrapper.vm.$nextTick();
}

/** Click the Create Workflow button. */
async function clickCreateButton(wrapper: ReturnType<typeof shallowMount>) {
    wrapper.findComponent(GButton).vm.$emit("click");
    await flushPromises();
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("WorkflowExtractionForm", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe("loading state", () => {
        it("shows loading spinner while fetching", () => {
            vi.mocked(extractWorkflowFromHistory).mockReturnValue(new Promise(() => {}));
            const wrapper = shallowMount(WorkflowExtractionForm as object, {
                propsData: { historyId: "history-1" },
                localVue,
            });
            expect(wrapper.findComponent(LoadingSpan).exists()).toBe(true);
        });

        it("shows error alert when fetch fails", async () => {
            vi.mocked(extractWorkflowFromHistory).mockRejectedValue(new Error("Network error"));
            const wrapper = await mountForm();
            expect(wrapper.find('[variant="danger"]').exists()).toBe(true);
        });
    });

    describe("empty history", () => {
        beforeEach(() => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_EMPTY);
        });

        it("shows no-workflow message", async () => {
            const wrapper = await mountForm();
            expect(wrapper.find('[data-description="no-workflow-message"]').exists()).toBe(true);
        });

        it("does not show name input or create button", async () => {
            const wrapper = await mountForm();
            expect(wrapper.findComponent(GFormInput).exists()).toBe(false);
            expect(wrapper.findComponent(GButton).exists()).toBe(false);
        });
    });

    describe("with jobs", () => {
        beforeEach(() => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_JOBS);
        });

        it("renders a card per job", async () => {
            const wrapper = await mountForm();
            expect(wrapper.findAllComponents(WorkflowExtractionCard)).toHaveLength(2);
        });

        it("auto-populates newName for input jobs from output name", async () => {
            const wrapper = await mountForm();
            const inputCard = wrapper.findAllComponents(WorkflowExtractionCard).at(1);
            expect(inputCard.props("job").newName).toBe("myfile.txt");
        });

        it("passes warnings to WorkflowExtractionMessages", async () => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_WARNINGS);
            const wrapper = await mountForm();
            expect(wrapper.findComponent(WorkflowExtractionMessages).props("warnings")).toEqual([
                "Tool version mismatch",
            ]);
        });
    });

    describe("submission validation", () => {
        beforeEach(() => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_JOBS);
        });

        it("create button is disabled when workflow name is empty", async () => {
            const wrapper = await mountForm();
            expect(wrapper.findComponent(GButton).props("disabled")).toBe(true);
        });

        it("create button is enabled once a name is entered", async () => {
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "My Workflow");
            expect(wrapper.findComponent(GButton).props("disabled")).toBe(false);
        });

        it("create button is disabled when all cards are unchecked", async () => {
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "My Workflow");
            // uncheck all cards via select events
            wrapper.findAllComponents(WorkflowExtractionCard).wrappers.forEach((card) => {
                card.vm.$emit("select");
            });
            await wrapper.vm.$nextTick();
            expect(wrapper.findComponent(GButton).props("disabled")).toBe(true);
        });
    });

    describe("input renaming", () => {
        beforeEach(() => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_JOBS);
        });

        it("opens RenameModal when rename is emitted from an input card", async () => {
            const wrapper = await mountForm();
            wrapper.findAllComponents(WorkflowExtractionCard).at(1).vm.$emit("rename");
            await flushPromises();
            expect(wrapper.findComponent(RenameModal).exists()).toBe(true);
        });

        it("closes RenameModal when the modal emits close", async () => {
            const wrapper = await mountForm();
            wrapper.findAllComponents(WorkflowExtractionCard).at(1).vm.$emit("rename");
            await flushPromises();
            wrapper.findComponent(RenameModal).vm.$emit("close");
            await flushPromises();
            expect(wrapper.findComponent(RenameModal).exists()).toBe(false);
        });
    });

    describe("workflow submission", () => {
        beforeEach(() => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_JOBS);
            vi.mocked(submitWorkflowExtraction).mockResolvedValue({ id: "new-workflow-id" });
        });

        it("calls submitWorkflowExtraction with correct payload on button click", async () => {
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            await clickCreateButton(wrapper);
            expect(submitWorkflowExtraction).toHaveBeenCalledWith(
                "history-1",
                expect.objectContaining({
                    workflow_name: "Extracted WF",
                    job_ids: ["job-tool-1"],
                }),
            );
        });

        it("shows success toast on successful submission", async () => {
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            await clickCreateButton(wrapper);
            expect(Toast.success).toHaveBeenCalled();
        });

        it("shows error alert when submission fails", async () => {
            vi.mocked(submitWorkflowExtraction).mockRejectedValue(new Error("Submit failed"));
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            await clickCreateButton(wrapper);
            expect(wrapper.find('[variant="danger"]').exists()).toBe(true);
        });

        it("does not submit when button is disabled", async () => {
            const wrapper = await mountForm();
            // no name set — button stays disabled
            await clickCreateButton(wrapper);
            expect(submitWorkflowExtraction).not.toHaveBeenCalled();
        });
    });
});
