export const SELECTION_STATES = {
    SELECTED: "selected",
    UNSELECTED: "unselected",
    MIXED: "indeterminate",
} as const;

export type SelectionState = (typeof SELECTION_STATES)[keyof typeof SELECTION_STATES];

export interface SelectionItem {
    id: string;
    label: string;
    details: string;
    isLeaf: boolean;
    url: string;
    entry: Record<string, unknown>;
    selectionState?: SelectionState;
    updateTime?: Date;
    tags?: readonly string[];
    size?: number;
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
