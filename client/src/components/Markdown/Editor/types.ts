export interface CellType {
    name: string;
    content: string;
    configure?: boolean;
    toggle?: boolean;
}

export interface DatasetLabel {
    invocation_id: string;
    input?: string;
    output?: string;
}

export interface Invocation {
    history_id: string;
    inputs: Record<string, { label?: string; id?: string }>;
    outputs: Record<string, { id?: string }>;
    steps: { workflow_step_label?: string; job_id?: string; implicit_collection_jobs_id?: string }[];
    workflow_id: string;
}

export interface TemplateEntry {
    title: string;
    description: string;
    icon?: string;
    logo?: string;
    cell: CellType;
}

export interface WorkflowLabel {
    label: string;
    type: "input" | "output" | "step";
}

export type ApiResponse = Array<any> | undefined;

export interface ContentType {
    dataset_id: string;
    dataset_name?: string;
}

export interface OptionType {
    id: string;
    name: string;
    value?: any;
}
