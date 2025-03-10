export interface CellType {
    name: string;
    content: string;
    configure?: boolean;
    toggle?: boolean;
}

export interface TemplateEntry {
    title: string;
    description: string;
    cell: CellType;
}
