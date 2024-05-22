export const SELECTION_STATES = {
    SELECTED: "success",
    UNSELECTED: "default",
    MIXED: "secondary",
};

export interface FieldEntry {
    key: string;
    label?: string;
    sortable?: boolean;
}

export interface SelectionItem {
    id: string;
    label: string;
    details: string;
    isLeaf: boolean;
    url: string;
}
