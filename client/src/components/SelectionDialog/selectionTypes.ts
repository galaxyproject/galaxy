export const SELECTION_STATES = {
    SELECTED: "success",
    UNSELECTED: "default",
    MIXED: "secondary",
} as const;

export type SelectionState = (typeof SELECTION_STATES)[keyof typeof SELECTION_STATES];

export interface SelectionItem {
    id: string;
    label: string;
    time?: Date | string;
    update_time: Date | string;
    details?: string;
    isLeaf: boolean;
    url: string;
    size?: number;
    variant?: SelectionState;
    tags?: string[];
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
