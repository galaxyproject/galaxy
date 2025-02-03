export interface CellType {
    name: string;
    content: string;
    configure?: boolean;
    toggle?: boolean;
}

export interface TemplateCategory {
    name: string;
    templates: Array<TemplateEntry>;
}

export interface TemplateEntry {
    title: string;
    description: string;
    cell: CellType;
}
