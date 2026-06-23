export interface MarkdownConfig {
    content?: string;
    errors?: Array<{ error?: string; line?: string }>;
    generate_time?: string;
    generate_version?: string;
    id?: string;
    markdown?: string;
    model_class?: string;
    title?: string;
    update_time?: string;
}
