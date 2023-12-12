interface Workflow {
    id: string;
    name: string;
    owner: string;
    tags: string[];
    deleted: boolean;
    published: boolean;
    description: string;
    create_time: string;
    update_time: string;
    annotations: string[];
    show_in_tool_panel: boolean;
    latest_workflow_uuid: string;
}

export function generateRandomString() {
    return Math.random().toString(36).substring(7) as string;
}

export function generateRandomWorkflow(owner: string): Workflow {
    return {
        id: "workflow-" + Math.floor(Math.random() * 1000000),
        name: generateRandomString(),
        owner: owner,
        tags: Array.from({ length: Math.floor(Math.random() * 10) }, () => generateRandomString()),
        deleted: false,
        published: Math.random() > 0.5,
        description: generateRandomString(),
        create_time: new Date(Date.now() + 1).toISOString(),
        update_time: new Date(Date.now() + 2).toISOString(),
        annotations: Array.from({ length: Math.floor(Math.random() * 2) }, () => generateRandomString()),
        show_in_tool_panel: Math.random() > 0.5,
        latest_workflow_uuid: generateRandomString(),
    };
}

export function generateRandomWorkflowList(owner: string, count: number): Workflow[] {
    return Array.from({ length: count }, () => generateRandomWorkflow(owner));
}
