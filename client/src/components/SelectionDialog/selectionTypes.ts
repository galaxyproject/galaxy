import type { TableClassValue } from "@/components/Common/GTable.types";

export const SELECTION_STATES = {
    SELECTED: "success",
    UNSELECTED: "default",
    MIXED: "secondary",
} as const;

export type SelectionState = (typeof SELECTION_STATES)[keyof typeof SELECTION_STATES];

export interface SelectionItem {
    class?: TableClassValue;
    cellClass?: Record<string, TableClassValue>;
    id: string;
    label: string;
    details: string;
    isLeaf: boolean;
    url: string;
    entry: Record<string, unknown>;
    selectionState?: SelectionState;
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
