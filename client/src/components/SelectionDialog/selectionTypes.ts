export const SELECTION_STATES = {
    SELECTED: "success" as const,
    UNSELECTED: "default" as const,
    MIXED: "secondary" as const,
};

export type SelectionState = (typeof SELECTION_STATES)[keyof typeof SELECTION_STATES];

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
    _rowVariant?: SelectionState;
}

export interface ItemsProviderContext {
    apiUrl?: string;
    currentPage: number;
    perPage: number;
    filter?: string;
    sortBy?: string;
    sortDesc?: boolean;
}

export type ItemsProvider = (ctx: ItemsProviderContext) => Promise<SelectionItem[]>;
