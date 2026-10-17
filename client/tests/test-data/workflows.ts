import type { WorkflowSummary } from "@/api/workflows";

export function getFakeWorkflowSummary(overrides: Partial<WorkflowSummary> = {}): WorkflowSummary {
    const id = overrides.id ?? "workflow-id";
    return {
        model_class: "StoredWorkflow",
        id,
        latest_workflow_id: `${id}-latest`,
        name: "Test Workflow",
        create_time: "2026-08-30T10:00:00",
        update_time: "2026-08-31T10:00:00",
        published: false,
        importable: false,
        deleted: false,
        hidden: false,
        tags: [],
        latest_workflow_uuid: `${id}-uuid`,
        creator_deleted: false,
        annotations: [],
        url: `/api/workflows/${id}`,
        owner: "me",
        source_metadata: {},
        show_in_tool_panel: false,
        ...overrides,
    };
}
