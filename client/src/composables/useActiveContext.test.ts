import { describe, expect, it, vi } from "vitest";
import { type Ref, ref } from "vue";

import type { ActiveContext } from "./useActiveContext";

// Mock route as a reactive ref so tests can mutate it
const mockRoute: Ref<{ path: string; query: Record<string, string>; params: Record<string, string> }> = ref({
    path: "/",
    query: {},
    params: {},
});

vi.mock("vue-router/composables", () => ({
    useRoute: () => mockRoute.value,
}));

const mockToolNames: Record<string, string> = {};

// In a real Pinia store, computed properties are auto-unwrapped,
// so toolStore.getToolNameById is accessed as a plain function.
vi.mock("@/stores/toolStore", () => ({
    useToolStore: () => ({
        getToolNameById: (id: string) => mockToolNames[id] ?? "...",
    }),
}));

// Import after mocks are in place
const { useActiveContext } = await import("./useActiveContext");

function withRoute(path: string, query: Record<string, string> = {}, params: Record<string, string> = {}) {
    mockRoute.value = { path, query, params };
    return useActiveContext();
}

describe("useActiveContext", () => {
    describe("activeContext", () => {
        it("returns null for unrecognized routes", () => {
            const { activeContext } = withRoute("/some/random/page");
            expect(activeContext.value).toBeNull();
        });

        it("returns null for the root route with no relevant query params", () => {
            const { activeContext } = withRoute("/");
            expect(activeContext.value).toBeNull();
        });

        it("detects tool context from root route with tool_id", () => {
            const { activeContext } = withRoute("/", { tool_id: "bwa_mem" });
            expect(activeContext.value).toEqual({
                contextType: "tool",
                toolId: "bwa_mem",
                toolName: undefined,
                toolVersion: undefined,
            });
        });

        it("excludes upload1 from tool context", () => {
            const { activeContext } = withRoute("/", { tool_id: "upload1" });
            expect(activeContext.value).toBeNull();
        });

        it("includes tool name when the tool store has it", () => {
            mockToolNames["bowtie2"] = "Bowtie2";
            try {
                const { activeContext } = withRoute("/", { tool_id: "bowtie2" });
                expect((activeContext.value as ActiveContext & { contextType: "tool" }).toolName).toBe("Bowtie2");
            } finally {
                delete mockToolNames["bowtie2"];
            }
        });

        it("omits tool name when store returns placeholder", () => {
            const { activeContext } = withRoute("/", { tool_id: "unknown_tool" });
            expect((activeContext.value as ActiveContext & { contextType: "tool" }).toolName).toBeUndefined();
        });

        it("includes version when present in query", () => {
            const { activeContext } = withRoute("/", { tool_id: "bwa_mem", version: "0.7.17" });
            expect((activeContext.value as ActiveContext & { contextType: "tool" }).toolVersion).toBe("0.7.17");
        });

        it("detects dataset context", () => {
            const { activeContext } = withRoute("/datasets/abc123", {}, { datasetId: "abc123" });
            expect(activeContext.value).toEqual({
                contextType: "dataset",
                datasetId: "abc123",
            });
        });

        it("detects workflow editor context", () => {
            const { activeContext } = withRoute("/workflows/edit", { id: "wf-42" });
            expect(activeContext.value).toEqual({
                contextType: "workflow_editor",
                workflowId: "wf-42",
            });
        });

        it("detects workflow run from /workflows/run", () => {
            const { activeContext } = withRoute("/workflows/run", { id: "wf-99" });
            expect(activeContext.value).toEqual({
                contextType: "workflow_run",
                workflowId: "wf-99",
            });
        });

        it("detects workflow run from root route with workflow_id", () => {
            const { activeContext } = withRoute("/", { workflow_id: "wf-55" });
            expect(activeContext.value).toEqual({
                contextType: "workflow_run",
                workflowId: "wf-55",
            });
        });

        it("detects job context", () => {
            const { activeContext } = withRoute("/jobs/job-7", {}, { jobId: "job-7" });
            expect(activeContext.value).toEqual({
                contextType: "job",
                jobId: "job-7",
            });
        });
    });

    describe("contextLabel", () => {
        it("returns null when no context", () => {
            const { contextLabel } = withRoute("/some/other/page");
            expect(contextLabel.value).toBeNull();
        });

        it("labels tool context with name", () => {
            mockToolNames["samtools_sort"] = "Samtools Sort";
            try {
                const { contextLabel } = withRoute("/", { tool_id: "samtools_sort" });
                expect(contextLabel.value).toBe("Tool: Samtools Sort");
            } finally {
                delete mockToolNames["samtools_sort"];
            }
        });

        it("labels tool context with ID when name unavailable", () => {
            const { contextLabel } = withRoute("/", { tool_id: "mystery_tool" });
            expect(contextLabel.value).toBe("Tool: mystery_tool");
        });

        it("labels dataset context", () => {
            const { contextLabel } = withRoute("/datasets/ds-1", {}, { datasetId: "ds-1" });
            expect(contextLabel.value).toBe("Dataset: ds-1");
        });

        it("labels workflow editor context", () => {
            const { contextLabel } = withRoute("/workflows/edit", { id: "wf-10" });
            expect(contextLabel.value).toBe("Editing workflow: wf-10");
        });

        it("labels workflow run context", () => {
            const { contextLabel } = withRoute("/workflows/run", { id: "wf-20" });
            expect(contextLabel.value).toBe("Running workflow: wf-20");
        });

        it("labels job context", () => {
            const { contextLabel } = withRoute("/jobs/j-5", {}, { jobId: "j-5" });
            expect(contextLabel.value).toBe("Job: j-5");
        });
    });
});
