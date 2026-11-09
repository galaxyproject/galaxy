import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";

import type { GalaxyConfiguration } from "@/stores/configurationStore";
import type Filtering from "@/utils/filtering";

export interface Action {
    title: string;
    icon?: IconDefinition;
    handler: () => void;
}

export type ActionArray = Array<Action>;

export interface GridConfig {
    id: string;
    actions?: ActionArray;
    fields: FieldArray;
    filtering?: Filtering<any>;
    /** Number of items that can be picked across the column filters */
    maxColumnFilterPicks?: number;
    getData: (
        offset: number,
        limit: number,
        search: string,
        sort_by: string,
        sort_desc: boolean,
        extraProps?: Record<string, unknown>,
    ) => Promise<any>;
    batch?: BatchOperationArray;
    plural: string;
    sortBy: string;
    sortKeys: Array<string>;
    sortDesc: boolean;
    title: string;
}

export type FieldArray = Array<FieldEntry>;

export interface FieldEntry {
    key: string;
    title?: string | null;
    condition?: (data: RowData) => boolean;
    disabled?: boolean;
    type: validTypes;
    operations?: Array<Operation>;
    icon?: IconDefinition;
    handler?: FieldHandler;
    converter?: (data: RowData) => string;
    filter?: FieldFilter;
    width?: number;
}

/** An item offered by a column's filter dropdown */
export interface FilterOption {
    id: string;
    name: string;
    /** Shown as elapsed time */
    updateTime?: string;
    /** Secondary text such as a run or item count, read reactively */
    detail?: () => string | undefined;
}

/**
 * Adds a filter dropdown to the column header. Picking items sets repeated `key:<id>` terms in the
 * grid's filter text and removes the `clears` keys from it. `key` must be a `MultiTags` filter.
 */
export interface FieldFilter {
    key: string;
    clears?: string[];
    /** Name of the items, used in the dropdown's labels (e.g. "workflows") */
    plural: string;
    /** Items matching the search text; an empty query lists the most recent items */
    search: (query: string) => Promise<FilterOption[]>;
}

export type FieldHandler = (data: RowData) => void;

export interface BatchOperation {
    title: string;
    icon: IconDefinition;
    condition?: (data: Array<RowData>) => boolean;
    handler: (data: Array<RowData>) => OperationHandlerReturn;
}

export type BatchOperationArray = Array<BatchOperation>;

export interface Operation {
    title: string;
    icon: IconDefinition;
    condition?: (data: RowData, config: GalaxyConfiguration) => boolean;
    handler: (data: RowData) => OperationHandlerReturn;
    loading?: (data: RowData, config: GalaxyConfiguration) => boolean;
}

interface OperationHandlerMessage {
    message: string;
    status: string;
}

type OperationHandlerReturn = Promise<OperationHandlerMessage | undefined> | void;

export type RowData = Record<string, unknown>;

type validTypes =
    | "boolean"
    | "date"
    | "datasets"
    | "link"
    | "button"
    | "operations"
    | "sharing"
    | "tags"
    | "text"
    | "expand"
    | "history"
    | "helptext";
