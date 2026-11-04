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

/**
 * Renders a button next to the cell that sets `key:value` in the grid's filter text
 */
export interface FieldFilter {
    key: string;
    title: string;
    value: (data: RowData) => string | undefined;
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
