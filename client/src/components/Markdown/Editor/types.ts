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

/** Shared shape of a `visualization` embed block, read by the renderer and
 * written by the configure dialog. The index signature carries plugin-specific
 * config through unchanged. */
export interface VisualizationEmbedConfig {
    visualization_name?: string;
    visualization_title?: string;
    dataset_id?: string;
    dataset_url?: string;
    dataset_label?: DatasetLabel;
    dataset_name?: string;
    settings?: Record<string, unknown>;
    tracks?: unknown[];
    height?: number;
    [key: string]: unknown;
}

export interface Invocation {
    history_id: string;
    inputs: Record<string, { label?: string; id?: string; src?: string }>;
    outputs: Record<string, { id?: string }>;
    output_collections: Record<string, { id?: string }>;
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
