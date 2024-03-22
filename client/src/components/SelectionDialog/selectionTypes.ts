export const SELECTION_STATES = {
    SELECTED: "success",
    UNSELECTED: "default",
    MIXED: "secondary",
};

export interface SelectionItem {
    id: string;
    label: string;
    details: string;
    isLeaf: boolean;
    url: string;
}
