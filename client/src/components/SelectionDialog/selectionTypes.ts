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

/** What a provider is asked for: one page of one level, plus the signal that cancels it. */
export interface SelectItemsQuery {
    /** Opened folders, root first; empty at the root level. */
    path: readonly SelectionItem[];
    page: number;
    perPage: number;
    filter: string;
    sortBy?: string;
    sortDesc?: boolean;
    signal: AbortSignal;
}

export interface SelectItemsPage<Raw> {
    items: Raw[];
    /** Total matches when the source pages and filters server-side; undefined means all items were returned. */
    total?: number;
}

/** Data source of a selection dialog: fetches raw records for a query and maps each one to a SelectionItem. */
export interface SelectItemsProvider<Raw = unknown> {
    load(query: SelectItemsQuery): Promise<SelectItemsPage<Raw>>;
    map(raw: Raw, query: SelectItemsQuery): SelectionItem;
}
