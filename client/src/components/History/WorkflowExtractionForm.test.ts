import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
    extractWorkflowByIds,
    extractWorkflowFromHistory,
    type WorkflowExtractionJob,
    type WorkflowExtractionSummary,
} from "@/api/histories";
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
    extractWorkflowByIds: vi.fn(),
}));

vi.mock("@/composables/toast", () => {
    const toastInstance = { success: vi.fn(), error: vi.fn() };
    return {
        Toast: toastInstance,
        useToast: () => toastInstance,
    };
});

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => ({
        getHistoryNameById: vi.fn().mockReturnValue("My History"),
        currentHistoryId: "history-1",
    }),
}));

// ── Fixtures ─────────────────────────────────────────────────────────────────

const TOOL_OUTPUT = {
    id: "ds-1",
    hid: 1,
    name: "output1",
    history_content_type: "dataset",
    state: "ok",
    deleted: false,
    exposed: false,
    output_name: "out_file1",
} as NonNullable<WorkflowExtractionJob["outputs"]>[number];

const TOOL_JOB: WorkflowExtractionJob = {
    id: "job-tool-1",
    tool_id: "cat1",
    tool_name: "Concatenate",
    tool_version: "1.0",
    step_type: "tool",
    checked: true,
    tool_version_warning: null,
    outputs: [TOOL_OUTPUT],
};

const MAPPED_TOOL_JOB: WorkflowExtractionJob = {
    ...TOOL_JOB,
    id: "job-tool-2",
    implicit_collection_jobs_id: "icj-1",
    implicit_collection_jobs_size: 4,
};

const MAPPED_TOOL_JOB_2: WorkflowExtractionJob = {
    ...MAPPED_TOOL_JOB,
    id: "job-tool-3",
};

const TOOL_JOB_WITH_NON_WORKFLOW_OUTPUT: WorkflowExtractionJob = {
    ...TOOL_JOB,
    outputs: [{ ...TOOL_OUTPUT, output_name: undefined } as NonNullable<WorkflowExtractionJob["outputs"]>[number]],
};

const INPUT_JOB: WorkflowExtractionJob = {
    id: null,
    tool_id: null,
    tool_name: "Input Dataset",
    tool_version: null,
    step_type: "input_dataset",
    checked: true,
    tool_version_warning: null,
    outputs: [
        {
            id: "ds-2",
            hid: 2,
            name: "myfile.txt",
            history_content_type: "dataset",
            state: "ok",
            deleted: false,
            exposed: false,
        },
    ],
};

function summary(jobs: WorkflowExtractionJob[], warnings: string[] = []): WorkflowExtractionSummary {
    return { history_id: "history-1", jobs, warnings };
}

/** Second input sharing INPUT_JOB's output name ("myfile.txt") → colliding newName. */
const INPUT_JOB_DUP: WorkflowExtractionJob = {
    ...INPUT_JOB,
    outputs: [{ ...INPUT_JOB.outputs![0], id: "ds-3" } as NonNullable<WorkflowExtractionJob["outputs"]>[number]],
};

/** Two tool jobs whose exposed outputs default to the same label ("shared"). */
const TOOL_JOB_OUT_A: WorkflowExtractionJob = {
    ...TOOL_JOB,
    id: "job-out-a",
    outputs: [{ ...TOOL_OUTPUT, id: "out-a", name: "shared" }],
};
const TOOL_JOB_OUT_B: WorkflowExtractionJob = {
    ...TOOL_JOB,
    id: "job-out-b",
    outputs: [{ ...TOOL_OUTPUT, id: "out-b", name: "shared" }],
};

const SUMMARY_WITH_JOBS = summary([TOOL_JOB, INPUT_JOB]);
const SUMMARY_WITH_DUPLICATE_INPUT_NAMES = summary([INPUT_JOB, INPUT_JOB_DUP]);
const SUMMARY_WITH_DUPLICATE_OUTPUT_NAMES = summary([TOOL_JOB_OUT_A, TOOL_JOB_OUT_B]);
const SUMMARY_WITH_MAPPED_JOB = summary([MAPPED_TOOL_JOB]);
const SUMMARY_WITH_DUPLICATE_MAPPED_JOBS = summary([MAPPED_TOOL_JOB, MAPPED_TOOL_JOB_2]);
const SUMMARY_WITH_PLAIN_AND_MAPPED_JOBS = summary([TOOL_JOB, MAPPED_TOOL_JOB]);
const SUMMARY_EMPTY = summary([]);
const SUMMARY_WITH_WARNINGS = summary([TOOL_JOB], ["Tool version mismatch"]);

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
            vi.mocked(extractWorkflowByIds).mockResolvedValue({ id: "new-workflow-id" });
        });

        it("calls extractWorkflowByIds with encoded-id payload on button click", async () => {
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            await clickCreateButton(wrapper);
            const payload = vi.mocked(extractWorkflowByIds).mock.calls[0]?.[0] as Record<string, unknown>;
            expect(payload).toEqual(
                expect.objectContaining({
                    workflow_name: "Extracted WF",
                    job_ids: ["job-tool-1"],
                    implicit_collection_jobs_ids: [],
                    hda_ids: ["ds-2"],
                    hdca_ids: [],
                    dataset_names: ["myfile.txt"],
                    dataset_collection_names: [],
                }),
            );
            expect(payload).not.toHaveProperty("output_labels");
        });

        it("submits output_labels only after an output is starred", async () => {
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            wrapper.findAllComponents(WorkflowExtractionCard).at(0).vm.$emit("toggle-output", 0);
            await wrapper.vm.$nextTick();
            await clickCreateButton(wrapper);
            expect(extractWorkflowByIds).toHaveBeenCalledWith(
                expect.objectContaining({
                    output_labels: [{ id: "ds-1", kind: "hda", label: "output1" }],
                }),
            );
        });

        it("does not submit starred outputs from unchecked tool rows", async () => {
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            const toolCard = wrapper.findAllComponents(WorkflowExtractionCard).at(0);
            toolCard.vm.$emit("toggle-output", 0);
            toolCard.vm.$emit("select");
            await wrapper.vm.$nextTick();
            await clickCreateButton(wrapper);
            const payload = vi.mocked(extractWorkflowByIds).mock.calls[0]?.[0] as Record<string, unknown>;
            expect(payload).not.toHaveProperty("output_labels");
            expect(payload).toEqual(expect.objectContaining({ job_ids: [] }));
        });

        it("does not submit output labels for outputs without a workflow-visible output name", async () => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(summary([TOOL_JOB_WITH_NON_WORKFLOW_OUTPUT]));
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            wrapper.findAllComponents(WorkflowExtractionCard).at(0).vm.$emit("toggle-output", 0);
            await wrapper.vm.$nextTick();
            await clickCreateButton(wrapper);
            const payload = vi.mocked(extractWorkflowByIds).mock.calls[0]?.[0] as Record<string, unknown>;
            expect(payload).not.toHaveProperty("output_labels");
        });

        it("does not submit a starred output with an empty label", async () => {
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            const toolCard = wrapper.findAllComponents(WorkflowExtractionCard).at(0);
            toolCard.vm.$emit("toggle-output", 0);
            toolCard.vm.$emit("rename-output", 0);
            await flushPromises();
            const renameAction = wrapper.findComponent(RenameModal).props("renameAction") as (name: string) => void;
            renameAction("");
            await wrapper.vm.$nextTick();
            await clickCreateButton(wrapper);
            expect(extractWorkflowByIds).not.toHaveBeenCalled();
        });

        it("submits mapped tool job via implicit_collection_jobs_ids", async () => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_MAPPED_JOB);
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            await clickCreateButton(wrapper);
            expect(extractWorkflowByIds).toHaveBeenCalledWith(
                expect.objectContaining({
                    job_ids: [],
                    implicit_collection_jobs_ids: ["icj-1"],
                }),
            );
        });

        it("dedupes ICJ ids when two cards share an ICJ", async () => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_DUPLICATE_MAPPED_JOBS);
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            await clickCreateButton(wrapper);
            expect(extractWorkflowByIds).toHaveBeenCalledWith(
                expect.objectContaining({
                    job_ids: [],
                    implicit_collection_jobs_ids: ["icj-1"],
                }),
            );
        });

        it("mixes plain and mapped job buckets correctly", async () => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_PLAIN_AND_MAPPED_JOBS);
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            await clickCreateButton(wrapper);
            expect(extractWorkflowByIds).toHaveBeenCalledWith(
                expect.objectContaining({
                    job_ids: ["job-tool-1"],
                    implicit_collection_jobs_ids: ["icj-1"],
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
            vi.mocked(extractWorkflowByIds).mockRejectedValue(new Error("Submit failed"));
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            await clickCreateButton(wrapper);
            expect(wrapper.find('[variant="danger"]').exists()).toBe(true);
        });

        it("submission error keeps job list visible", async () => {
            vi.mocked(extractWorkflowByIds).mockRejectedValue(new Error("Submit failed"));
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            await clickCreateButton(wrapper);
            expect(wrapper.find('[variant="danger"]').exists()).toBe(true);
            expect(wrapper.findAllComponents(WorkflowExtractionCard)).toHaveLength(2);
        });

        it("submit shows submitting state without hiding list", async () => {
            let resolveSubmission: (value: { id: string }) => void = () => {};
            vi.mocked(extractWorkflowByIds).mockReturnValue(
                new Promise((resolve) => {
                    resolveSubmission = resolve;
                }),
            );
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            wrapper.findComponent(GButton).vm.$emit("click");
            await wrapper.vm.$nextTick();
            expect(wrapper.findComponent(GButton).props("disabled")).toBe(true);
            expect(wrapper.text()).toContain("Creating...");
            expect(wrapper.findComponent(LoadingSpan).exists()).toBe(false);
            expect(wrapper.findAllComponents(WorkflowExtractionCard)).toHaveLength(2);
            resolveSubmission({ id: "new-workflow-id" });
            await flushPromises();
        });

        it("does not submit when button is disabled", async () => {
            const wrapper = await mountForm();
            // no name set — button stays disabled
            await clickCreateButton(wrapper);
            expect(extractWorkflowByIds).not.toHaveBeenCalled();
        });
    });

    describe("uniqueness validation", () => {
        function disabledReason(wrapper: ReturnType<typeof shallowMount>): string {
            return wrapper.findComponent(GButton).props("disabledTitle") as string;
        }

        function card(wrapper: ReturnType<typeof shallowMount>, index: number) {
            return wrapper.findAllComponents(WorkflowExtractionCard).at(index);
        }

        it("de-duplicates colliding input names so the UI reflects what will be created", async () => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_DUPLICATE_INPUT_NAMES);
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");

            const names = [card(wrapper, 0).props("job").newName, card(wrapper, 1).props("job").newName];
            expect(new Set(names)).toEqual(new Set(["myfile.txt", "myfile.txt (2)"]));
            // Names are unique, so the backend won't reject — submit is enabled.
            expect(wrapper.findComponent(GButton).props("disabled")).toBe(false);
        });

        it("re-uniquifies when an input is renamed into a collision", async () => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_DUPLICATE_INPUT_NAMES);
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");

            // Cards start as ["myfile.txt", "myfile.txt (2)"]; rename the 2nd back onto the 1st.
            card(wrapper, 1).vm.$emit("rename");
            await flushPromises();
            (wrapper.findComponent(RenameModal).props("renameAction") as (name: string) => void)("myfile.txt");
            await wrapper.vm.$nextTick();

            expect(card(wrapper, 1).props("job").newName).toBe("myfile.txt (2)");
            expect(wrapper.findComponent(GButton).props("disabled")).toBe(false);
        });

        async function renameOutputVia(wrapper: ReturnType<typeof shallowMount>, index: number, label: string) {
            card(wrapper, index).vm.$emit("rename-output", 0);
            await flushPromises();
            (wrapper.findComponent(RenameModal).props("renameAction") as (name: string) => void)(label);
            await wrapper.vm.$nextTick();
        }

        it("disables submit when two exposed outputs share a label, re-enables after relabel", async () => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_DUPLICATE_OUTPUT_NAMES);
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            card(wrapper, 0).vm.$emit("toggle-output", 0);
            card(wrapper, 1).vm.$emit("toggle-output", 0);
            await wrapper.vm.$nextTick();

            expect(wrapper.findComponent(GButton).props("disabled")).toBe(true);
            expect(disabledReason(wrapper)).toBe("Exposed output labels must be unique");

            await renameOutputVia(wrapper, 1, "distinct");

            expect(wrapper.findComponent(GButton).props("disabled")).toBe(false);
        });

        it("treats internal-whitespace variants as duplicate output labels (backend parity)", async () => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_DUPLICATE_OUTPUT_NAMES);
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            card(wrapper, 0).vm.$emit("toggle-output", 0);
            card(wrapper, 1).vm.$emit("toggle-output", 0);
            await wrapper.vm.$nextTick();

            // Relabel both so they differ only by internal whitespace; the backend
            // collapses "a  b" and "a b" to the same string and 400s the second.
            await renameOutputVia(wrapper, 0, "a  b");
            await renameOutputVia(wrapper, 1, "a b");

            expect(wrapper.findComponent(GButton).props("disabled")).toBe(true);
            expect(disabledReason(wrapper)).toBe("Exposed output labels must be unique");
        });

        it("treats labels colliding only after 255-char truncation as duplicates (backend parity)", async () => {
            vi.mocked(extractWorkflowFromHistory).mockResolvedValue(SUMMARY_WITH_DUPLICATE_OUTPUT_NAMES);
            const wrapper = await mountForm();
            await setWorkflowName(wrapper, "Extracted WF");
            card(wrapper, 0).vm.$emit("toggle-output", 0);
            card(wrapper, 1).vm.$emit("toggle-output", 0);
            await wrapper.vm.$nextTick();

            // Identical for 255 chars, differ only after — the backend truncates both
            // to the same string and 400s the second; the frontend must predict that.
            await renameOutputVia(wrapper, 0, "x".repeat(255) + "A");
            await renameOutputVia(wrapper, 1, "x".repeat(255) + "B");

            expect(wrapper.findComponent(GButton).props("disabled")).toBe(true);
            expect(disabledReason(wrapper)).toBe("Exposed output labels must be unique");
        });
    });
});
